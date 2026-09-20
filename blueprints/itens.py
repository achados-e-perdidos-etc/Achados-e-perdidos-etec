"""
Blueprint de Gestão do Catálogo de Itens e Categorias
Rotas para listagem, cadastro (secretaria e aluno), moderação, atualização e descarte/doação.
"""
import json
from datetime import datetime
from flask import Blueprint, request, jsonify
from psycopg2.extras import RealDictCursor

from database import get_db_connection, verificar_e_atualizar_itens_doacao
from utils.security import token_required
from utils.helpers import extrair_termos
from services.cloudinary_service import processar_fotos
from services.email_service import disparar_email

itens_bp = Blueprint('itens', __name__)

# ==============================================================================
# CATEGORIAS
# ==============================================================================

@itens_bp.route('/api/categorias/<string:nome>', methods=['OPTIONS', 'DELETE'])
@itens_bp.route('/api/categorias', methods=['OPTIONS', 'GET', 'POST', 'DELETE'])
def categorias(nome=None):
    """Gerencia listagem, criação e exclusão de categorias de itens."""
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200
        
    if request.method == 'GET':
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM categorias ORDER BY id ASC;")
        res = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(res)
        
    elif request.method == 'POST':
        nome_cat = (request.json.get('nome') or '').strip().upper()
        if not nome_cat:
            return jsonify({"success": False, "message": "Nome da categoria é obrigatório."}), 400
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO categorias (nome) VALUES (%s) ON CONFLICT DO NOTHING;", (nome_cat,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True})
        
    elif request.method == 'DELETE':
        cat_nome = nome
        if not cat_nome and request.is_json and request.json:
            cat_nome = request.json.get('nome')
        if not cat_nome:
            cat_nome = request.args.get('nome')
        cat_nome = (cat_nome or '').strip().upper()
        if not cat_nome:
            return jsonify({"success": False, "message": "Nome da categoria não informado."}), 400
            
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM categorias WHERE UPPER(nome) = %s;", (cat_nome,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": f"Categoria '{cat_nome}' removida com sucesso."})

# ==============================================================================
# CATÁLOGO PÚBLICO & PENDÊNCIAS
# ==============================================================================

@itens_bp.route('/api/itens', methods=['OPTIONS', 'GET'])
def get_itens():
    """Retorna a lista de todos os itens aprovados e disponíveis para o catálogo público."""
    conn = None
    try:
        verificar_e_atualizar_itens_doacao()
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute("""
                SELECT id, 
                       COALESCE(nome_item, descricao) as nome, 
                       descricao as txt_descricao, 
                       categoria, 
                       data_encontrado as txt_data, 
                       local_encontrado as txt_local, 
                       foto, fotos_json, status, solicitado_por, rm_aluno, 
                       COALESCE(aprovado, TRUE) as aprovado, 
                       COALESCE(cadastrado_por_aluno, FALSE) as cadastrado_por_aluno 
                FROM itens 
                WHERE (aprovado IS NULL OR aprovado = TRUE)
                ORDER BY id DESC;
            """)
            itens = cursor.fetchall()
        except Exception:
            conn.rollback()
            cursor.execute("""
                SELECT id, 
                       COALESCE(nome_item, descricao) as nome, 
                       descricao as txt_descricao, 
                       categoria, 
                       data_encontrado as txt_data, 
                       local_encontrado as txt_local, 
                       foto, status, solicitado_por, rm_aluno 
                FROM itens 
                ORDER BY id DESC;
            """)
            itens = cursor.fetchall()

        for item in itens:
            try:
                item['fotos'] = json.loads(item['fotos_json']) if item.get('fotos_json') else ([] if not item.get('foto') else [item['foto']])
            except Exception:
                item['fotos'] = [item['foto']] if item.get('foto') else []
            if 'aprovado' not in item:
                item['aprovado'] = True
            if 'cadastrado_por_aluno' not in item:
                item['cadastrado_por_aluno'] = False
                
        cursor.close()
        conn.close()
        return jsonify(itens)
    except Exception as e:
        if conn:
            conn.close()
        return jsonify({"success": False, "error": str(e)}), 500

@itens_bp.route('/api/itens/pendentes', methods=['OPTIONS', 'GET'])
@token_required
def get_itens_pendentes():
    """Lista itens cadastrados por alunos aguardando aprovação da secretaria."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT id, nome_item as nome, descricao as txt_descricao, categoria, 
                   data_encontrado as txt_data, local_encontrado as txt_local, 
                   foto, fotos_json, status, rm_aluno 
            FROM itens 
            WHERE aprovado = FALSE 
            ORDER BY id DESC;
        """)
        itens = cursor.fetchall()
        for item in itens:
            try:
                item['fotos'] = json.loads(item['fotos_json']) if item.get('fotos_json') else ([] if not item.get('foto') else [item['foto']])
            except Exception:
                item['fotos'] = []
        cursor.close()
        conn.close()
        return jsonify(itens)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@itens_bp.route('/api/itens/cadastrar-aluno', methods=['OPTIONS', 'POST'])
def cadastrar_item_aluno():
    """Permite que um estudante cadastre um objeto encontrado para análise da secretaria."""
    data = request.json or {}
    nome = (data.get('nome') or '').strip()
    descricao = (data.get('descricao') or '').strip()
    categoria = (data.get('categoria') or 'OUTROS').strip()
    data_enc = (data.get('data') or datetime.now().strftime("%d/%m/%Y")).strip()
    local = (data.get('local') or 'Não informado').strip()
    rm = (data.get('rm') or '').strip()
    
    lista_entrada = data.get('fotos', [])
    if not lista_entrada and data.get('foto'):
        lista_entrada = [data.get('foto')]

    urls_nuvem = processar_fotos(lista_entrada)
    foto_capa = urls_nuvem[0] if urls_nuvem else ''
    fotos_json_str = json.dumps(urls_nuvem)

    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('''
            INSERT INTO itens (
                nome_item, descricao, categoria, data_encontrado, 
                local_encontrado, foto, fotos_json, status, aprovado, 
                cadastrado_por_aluno, rm_aluno
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'DISPONÍVEL', FALSE, TRUE, %s) 
            RETURNING id;
        ''', (nome, descricao, categoria, data_enc, local, foto_capa, fotos_json_str, rm))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "Item enviado para moderação!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@itens_bp.route('/api/itens/<int:item_id>/aprovar', methods=['OPTIONS', 'PUT'])
@token_required
def aprovar_item(item_id):
    """Aprova um item pendente, tornando-o visível no catálogo público."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE itens SET aprovado = TRUE WHERE id = %s;", (item_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "Item aprovado com sucesso!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@itens_bp.route('/api/itens', methods=['OPTIONS', 'POST'])
@token_required
def cadastrar_item():
    """Cadastra um novo pertence achado diretamente pela secretaria escolar com auto-notificação de matches."""
    data = request.json or {}
    nome = (data.get('nome') or '').strip()
    descricao = (data.get('descricao') or '').strip()
    categoria = (data.get('categoria') or 'OUTROS').strip()
    data_enc = (data.get('data') or datetime.now().strftime("%d/%m/%Y")).strip()
    local = (data.get('local') or 'Não informado').strip()
    status = (data.get('status') or 'DISPONÍVEL').strip()

    if not descricao:
        return jsonify({"success": False, "error": "A descrição é obrigatória."}), 400

    lista_entrada = data.get('fotos', [])
    if not lista_entrada and data.get('foto'):
        lista_entrada = [data.get('foto')]

    urls_nuvem = processar_fotos(lista_entrada)
    foto_capa = urls_nuvem[0] if urls_nuvem else ''
    fotos_json_str = json.dumps(urls_nuvem)

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('''
            INSERT INTO itens (
                nome_item, descricao, categoria, data_encontrado, 
                local_encontrado, foto, fotos_json, status, aprovado
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE) 
            RETURNING id;
        ''', (nome, descricao, categoria, data_enc, local, foto_capa, fotos_json_str, status))
        
        row = cursor.fetchone()
        novo_id = row['id'] if isinstance(row, dict) else row[0]
        conn.commit()

        # Verifica correspondências com o mural de perdidos dos alunos
        try:
            termos_novo = extrair_termos(f"{nome} {descricao}")
            cursor.execute("SELECT * FROM mural_perdidos WHERE status = 'PROCURANDO' AND categoria = %s;", (categoria,))
            for mural in cursor.fetchall():
                termos_mural = extrair_termos(mural.get('descricao', ''))
                if len(termos_novo.intersection(termos_mural)) >= 1:
                    msg_match = f"A secretaria registrou um objeto parecido: '{nome or descricao}'. Veja o catálogo!"
                    cursor.execute(
                        "INSERT INTO mensagens_chat (rm_aluno, nome_aluno, remetente, mensagem, data_envio) VALUES (%s, %s, %s, %s, %s);", 
                        (mural['rm_aluno'], mural['nome_aluno'], 'SECRETARIA', msg_match, datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
                    )
                    if mural.get('email_aluno'):
                        disparar_email(
                            mural['email_aluno'], 
                            "Item Encontrado! ETEC Achados", 
                            f"<div style='font-family:Arial;'><h2 style='color:#dc2626;'>Possível Match!</h2><p>Olá {mural['nome_aluno']}, a secretaria registrou um item parecido: <strong>{nome or descricao}</strong>.</p></div>"
                        )
            conn.commit()
        except Exception:
            if conn:
                conn.rollback()

        cursor.close()
        conn.close()
        return jsonify({"success": True, "id": novo_id, "message": "Item salvo com sucesso!"})
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return jsonify({"success": False, "error": str(e)}), 500

@itens_bp.route('/api/itens/<int:item_id>', methods=['OPTIONS', 'PUT', 'POST', 'DELETE'])
@token_required
def gerenciar_item(item_id):
    """Atualiza ou exclui um item catalogado, incluindo registro formal de entrega se status for 'ENTREGUE'."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        if request.method == 'DELETE' or (request.is_json and request.json and request.json.get('_method') == 'DELETE'):
            cursor.execute("DELETE FROM entregues WHERE item_id = %s;", (item_id,))
            cursor.execute("DELETE FROM itens WHERE id = %s;", (item_id,))
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({"success": True, "message": "Item excluído com sucesso."})
        else:
            data = request.json or {}
            cursor.execute("SELECT * FROM itens WHERE id = %s;", (item_id,))
            item_atual = cursor.fetchone()
            if not item_atual:
                cursor.close()
                conn.close()
                return jsonify({"success": False, "message": "Item não encontrado."}), 404

            nome = data.get('nome') if ('nome' in data and data.get('nome') is not None) else item_atual.get('nome_item', '')
            descricao = data.get('descricao') if ('descricao' in data and data.get('descricao') is not None) else item_atual.get('descricao', '')
            categoria = data.get('categoria') if ('categoria' in data and data.get('categoria') is not None) else item_atual.get('categoria', 'OUTROS')
            data_enc = data.get('data') if ('data' in data and data.get('data') is not None) else item_atual.get('data_encontrado', '')
            local = data.get('local') if ('local' in data and data.get('local') is not None) else item_atual.get('local_encontrado', '')
            status = data.get('status') if ('status' in data and data.get('status') is not None) else item_atual.get('status', 'DISPONÍVEL')

            nome = (str(nome) or '').strip()
            descricao = (str(descricao) or '').strip()
            categoria = (str(categoria) or 'OUTROS').strip()
            data_enc = (str(data_enc) or '').strip()
            local = (str(local) or '').strip()
            status = (str(status) or 'DISPONÍVEL').strip()

            if not descricao:
                descricao = nome or 'Objeto'

            if 'fotos' in data and data.get('fotos') is not None:
                fotos_rec = data.get('fotos') or []
                urls = processar_fotos(fotos_rec)
                foto_capa = urls[0] if urls else (item_atual.get('foto') or '')
                fotos_json_str = json.dumps(urls) if urls else (item_atual.get('fotos_json') or '[]')
                cursor.execute("""
                    UPDATE itens 
                    SET nome_item=%s, descricao=%s, categoria=%s, data_encontrado=%s, 
                        local_encontrado=%s, foto=%s, fotos_json=%s, status=%s, aprovado=TRUE 
                    WHERE id=%s;
                """, (nome, descricao, categoria, data_enc, local, foto_capa, fotos_json_str, status, item_id))
            else:
                cursor.execute("""
                    UPDATE itens 
                    SET nome_item=%s, descricao=%s, categoria=%s, data_encontrado=%s, 
                        local_encontrado=%s, status=%s, aprovado=TRUE 
                    WHERE id=%s;
                """, (nome, descricao, categoria, data_enc, local, status, item_id))

            if status.upper() == 'ENTREGUE':
                cursor.execute("DELETE FROM entregues WHERE item_id = %s;", (item_id,))
                cursor.execute("""
                    INSERT INTO entregues (
                        item_id, nome_item, retirado_por, rm_retirante, turma_curso, 
                        data_entrega, funcionario_responsavel
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s);
                """, (
                    item_id, nome or descricao, 
                    data.get('retirado_por', item_atual.get('solicitado_por', '')), 
                    data.get('rm_retirante', item_atual.get('rm_aluno', '')), 
                    data.get('turma_curso', '-'), 
                    data.get('data_entrega', datetime.now().strftime("%d/%m/%Y %H:%M")), 
                    data.get('funcionario_responsavel', 'Secretaria')
                ))

            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({"success": True, "message": "Item atualizado com sucesso!"})
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return jsonify({"success": False, "error": str(e), "message": f"Erro interno ao atualizar item: {str(e)}"}), 500

@itens_bp.route('/api/itens/<int:item_id>/recusar', methods=['OPTIONS', 'PUT', 'DELETE', 'POST'])
@token_required
def recusar_solicitacao(item_id):
    """
    Recusa solicitação ou cadastro:
    - Se pendente de aprovação: exclui definitivamente o item rejeitado.
    - Se solicitação de retirada: cancela a reserva e reverte o item para DISPONÍVEL.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT aprovado, cadastrado_por_aluno FROM itens WHERE id = %s;", (item_id,))
        item = cursor.fetchone()
        
        if item and item.get('aprovado') is False:
            cursor.execute("DELETE FROM itens WHERE id = %s;", (item_id,))
            msg = "Item pendente recusado e excluído do sistema."
        else:
            cursor.execute("""
                UPDATE itens 
                SET status = 'DISPONÍVEL', solicitado_por = NULL, rm_aluno = NULL, email_solicitante = NULL 
                WHERE id = %s;
            """, (item_id,))
            msg = "Solicitação cancelada. Item retornado para DISPONÍVEL."
            
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": msg})
    except Exception as e:
        if conn:
            conn.close()
        return jsonify({"success": False, "error": str(e)}), 500

@itens_bp.route('/api/itens/doacoes/concluir', methods=['OPTIONS', 'DELETE'])
@token_required
def concluir_doacoes():
    """Remove do catálogo itens cujo processo de doação já foi concluído e registrado."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM itens WHERE UPPER(status) = 'DOAÇÃO FEITA' OR UPPER(status) = 'DOACAO FEITA';")
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"success": True})

@itens_bp.route('/api/solicitar', methods=['OPTIONS', 'POST'])
def solicitar_item():
    """Permite ao estudante solicitar a retirada de um item disponível."""
    data = request.json or {}
    item_id = data.get('id')
    nome = data.get('nome')
    rm = data.get('rm')
    email_aluno = data.get('email')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE itens 
        SET status = 'SOLICITADO', solicitado_por = %s, rm_aluno = %s, email_solicitante = %s 
        WHERE id = %s AND status = 'DISPONÍVEL';
    """, (nome, rm, email_aluno, item_id))
    afetados = cursor.rowcount
    conn.commit()
    cursor.close()
    conn.close()
    if afetados > 0:
        return jsonify({"success": True, "message": "Solicitação enviada com sucesso!"})
    return jsonify({"success": False, "message": "Este item não está mais disponível."}), 400
