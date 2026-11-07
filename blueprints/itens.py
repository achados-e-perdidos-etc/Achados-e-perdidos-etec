from utils.validacao_item import validar_item, validar_categoria
from utils.entregas import cancelar_entregas, registrar_entrega
"""
Blueprint de Gestão do Catálogo de Itens e Categorias
Rotas para listagem, cadastro (secretaria e aluno), moderação, atualização e descarte/doação.
"""
import json
from datetime import datetime
from flask import Blueprint, request, jsonify
from psycopg2.extras import RealDictCursor

from database import get_db_connection, verificar_e_atualizar_itens_doacao
from utils.doacoes import DOACOES_PENDENTES_SQL
from utils.privacy import item_publico, relato_publico
from utils.security import consulta_publica, token_required, secretaria_required, categorias_required, identidade_aluno, identidade_portal
from utils.helpers import extrair_termos
from services.cloudinary_service import processar_fotos, FalhaUploadFotos
from services.email_service import disparar_email
from services import push_delivery

itens_bp = Blueprint('itens', __name__)

# ==============================================================================
# CATEGORIAS
# ==============================================================================

@itens_bp.errorhandler(FalhaUploadFotos)
def falha_upload_fotos(error):
    return jsonify({'success': False, 'message': str(error)}), error.status_code

@itens_bp.route('/api/categorias/<string:nome>', methods=['OPTIONS', 'DELETE'])
@itens_bp.route('/api/categorias', methods=['OPTIONS', 'GET', 'POST', 'DELETE'])
@categorias_required
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
@consulta_publica
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
                WHERE (aprovado IS NULL OR aprovado = TRUE)
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
        return jsonify(itens if request.user.get('role') == 'secretaria' else [item_publico(it) for it in itens])
    except Exception as e:
        if conn:
            conn.close()
        return jsonify({"success": False, "error": str(e)}), 500

@itens_bp.route('/api/itens/pendentes', methods=['OPTIONS', 'GET'])
@secretaria_required
def get_itens_pendentes():
    from blueprints.moderacao import listar
    return listar(get_db_connection)

@itens_bp.route('/api/itens/cadastrar-aluno', methods=['OPTIONS', 'POST'])
@token_required
def cadastrar_item_aluno():
    """Permite que um estudante cadastre um objeto encontrado para análise da secretaria."""
    autor = identidade_portal()
    if not autor:
        return jsonify({'success': False, 'message': 'Entre com sua conta institucional para cadastrar objetos.'}), 403
    data = request.json or {}
    if request.headers.get('Idempotency-Key'):
        from services.cadastro_offline import enviar
        return enviar(get_db_connection,'encontrado',data)
    try:
        v = validar_item(data); validar_categoria(get_db_connection,v['categoria'])
    except ValueError as error: return jsonify(success=False,message=str(error)),400
    nome,descricao,categoria,data_enc,local,status = (v[k] for k in ['nome','descricao','categoria','data','local','status'])
    rm = autor['rm']
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
                cadastrado_por_aluno, rm_aluno, email_cadastrador
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'DISPONÍVEL', FALSE, TRUE, %s, %s)
            RETURNING id;
        ''', (nome, descricao, categoria, data_enc, local, foto_capa, fotos_json_str, rm, autor['email']))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "Item enviado para moderação!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@itens_bp.route('/api/itens/<int:item_id>/aprovar', methods=['OPTIONS', 'PUT'])
@secretaria_required
def aprovar_item(item_id):
    """Aprova um item pendente, tornando-o visível no catálogo público."""
    from services.moderacao_service import aprovar
    return aprovar(get_db_connection,item_id)

@itens_bp.route('/api/itens', methods=['OPTIONS', 'POST'])
@secretaria_required
def cadastrar_item():
    destinatarios_push = set()
    """Cadastra um novo pertence achado diretamente pela secretaria escolar com auto-notificação de matches."""
    data = request.json or {}
    try:
        v = validar_item(data); validar_categoria(get_db_connection,v['categoria'])
    except ValueError as error: return jsonify(success=False,message=str(error)),400
    nome,descricao,categoria,data_enc,local,status = (v[k] for k in ['nome','descricao','categoria','data','local','status'])
    from services.moderacao_service import publicar_conferido,registrar_revisao
    aviso=publicar_conferido(get_db_connection,{**data,**v})
    if aviso:return aviso
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
        registrar_revisao(cursor,novo_id,data)
        conn.commit()

        cursor.close()
        conn.close()
        return jsonify({"success": True, "id": novo_id, "message": "Item salvo com sucesso!"})
    except Exception as e:
        if conn:
            conn.rollback()
            destinatarios_push.clear()
            conn.close()
        return jsonify({"success": False, "error": str(e)}), 500

@itens_bp.route('/api/itens/<int:item_id>', methods=['OPTIONS', 'PUT', 'POST', 'DELETE'])
@secretaria_required
def gerenciar_item(item_id):
    """Atualiza ou exclui um item catalogado, incluindo registro formal de entrega se status for 'ENTREGUE'."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        if request.method == 'DELETE' or (request.is_json and request.json and request.json.get('_method') == 'DELETE'):
            cursor.execute("DELETE FROM itens WHERE id = %s;", (item_id,))
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({"success": True, "message": "Item excluído com sucesso."})
        else:
            data = request.json or {}
            cursor.execute("SELECT * FROM itens WHERE id = %s FOR UPDATE;", (item_id,))
            item_atual = cursor.fetchone()
            if not item_atual:
                cursor.close()
                conn.close()
                return jsonify({"success": False, "message": "Item não encontrado."}), 404

            try:
                v = validar_item(data,item_atual); validar_categoria(get_db_connection,v['categoria'])
            except ValueError as error:
                conn.rollback();conn.close();return jsonify(success=False,message=str(error)),400
            nome,descricao,categoria,data_enc,local,status = (v[k] for k in ['nome','descricao','categoria','data','local','status'])
            from services.moderacao_service import conferir_versao,aviso_duplicado,registrar_revisao
            if item_atual.get('aprovado') is False:
                try:conferir_versao(data,item_atual)
                except ValueError as error:return jsonify(success=False,message=str(error)),409
            if item_atual.get('aprovado') is False or any(v[k]!=item_atual.get(col) for k,col in [('nome','nome_item'),('categoria','categoria'),('data','data_encontrado')]):
                aviso=aviso_duplicado(cursor,{**data,**v},item_id)
                if aviso:return aviso

            if 'fotos' in data and data.get('fotos') is not None:
                fotos_rec = data.get('fotos') or []
                urls = processar_fotos(fotos_rec, existentes=item_publico(item_atual)['fotos'])
                foto_capa = urls[0] if urls else ''
                fotos_json_str = json.dumps(urls)
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

            if item_atual.get('aprovado') is False:
                cursor.execute('UPDATE itens SET motivo_recusa=NULL,recusado_em=NULL WHERE id=%s',(item_id,))
            registrar_revisao(cursor,item_id,data)
            if status == 'ENTREGUE':
                registrar_entrega(cursor,item_id,nome,data,item_atual,request.user['email'])
            else:
                cancelar_entregas(cursor,item_id,request.user['email'])

            conn.commit()
            cursor.close()
            conn.close()
            if status != item_atual.get('status'):
                push_delivery.notificar(item_atual.get('email_solicitante'), 'item')
            return jsonify({"success": True, "message": "Item atualizado com sucesso!"})
    except FalhaUploadFotos as error:
        if conn: conn.rollback(); conn.close()
        return jsonify({'success': False, 'message': str(error)}), error.status_code
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return jsonify(success=False,message="Não foi possível atualizar o item. Atualize e tente novamente."), 503
    finally:
        if conn: conn.close()

@itens_bp.route('/api/itens/<int:item_id>/recusar', methods=['OPTIONS', 'PUT', 'DELETE', 'POST'])
@secretaria_required
def recusar_solicitacao(item_id):
    from services.entrega_service import reverter
    return reverter(get_db_connection,item_id)

@itens_bp.route('/api/itens/doacoes/concluir', methods=['OPTIONS', 'DELETE'])
@secretaria_required
def concluir_doacoes():
    """Arquiva as doações pendentes, preservando o histórico dos itens."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"UPDATE itens SET status = 'DOAÇÃO FEITA' WHERE {DOACOES_PENDENTES_SQL} AND aprovado = TRUE;")
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"success": True})

@itens_bp.route('/api/solicitar', methods=['OPTIONS', 'POST'])
@token_required
def solicitar_item():
    """Permite ao estudante solicitar a retirada de um item disponível."""
    aluno = identidade_aluno()
    if not aluno:
        return jsonify({'success': False, 'message': 'Somente alunos com RM informado podem solicitar a retirada de itens.'}), 403
    data = request.json or {}
    item_id = data.get('id')
    nome, rm, email_aluno = aluno['nome'], aluno['rm'], aluno['email']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE itens 
        SET status = 'SOLICITADO', solicitado_por = %s, rm_aluno = %s, email_solicitante = %s 
        WHERE id = %s AND status = 'DISPONÍVEL' AND (aprovado IS NULL OR aprovado = TRUE);
    """, (nome, rm, email_aluno, item_id))
    afetados = cursor.rowcount
    conn.commit()
    cursor.close()
    conn.close()
    if afetados > 0:
        return jsonify({"success": True, "message": "Solicitação enviada com sucesso!"})
    return jsonify({"success": False, "message": "Este item não está mais disponível."}), 400



@itens_bp.route('/api/itens/meus', methods=['OPTIONS', 'GET'])
@token_required
def meus_itens():
    email = request.user.get('email')
    if not email:
        return jsonify({'success': False, 'message': 'Sessão sem identidade.'}), 403
    conn = get_db_connection()
    try:
        c = conn.cursor(cursor_factory=RealDictCursor)
        c.execute("""SELECT id, COALESCE(nome_item, descricao) as nome, descricao as txt_descricao,
                     categoria, data_encontrado as txt_data, local_encontrado as txt_local,
                     foto, fotos_json, status FROM itens
                     WHERE email_solicitante = %s AND (aprovado IS NULL OR aprovado = TRUE)
                     ORDER BY id DESC;""", (email,))
        rows = c.fetchall()
        c.close()
        return jsonify([item_publico(item) for item in rows])
    finally:
        conn.close()
