"""
Blueprint do Mural de Relatos de Perda
Permite aos estudantes registrar relatos públicos de pertences perdidos.
"""
import json
from datetime import datetime
from flask import Blueprint, request, jsonify
from psycopg2.extras import RealDictCursor

from database import get_db_connection
from utils.privacy import item_publico, relato_publico
from utils.security import consulta_publica, token_required, secretaria_required, identidade_aluno
from utils.helpers import extrair_termos

mural_bp = Blueprint('mural', __name__)

@mural_bp.route('/api/mural', methods=['OPTIONS', 'GET', 'POST'])
@consulta_publica
def mural():
    """Lista todos os relatos ou cadastra um novo relato de perda com busca imediata de matches."""
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200
        
    if request.method == 'GET':
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM mural_perdidos ORDER BY id DESC;")
        res = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(res if request.user.get('role') == 'secretaria' else [relato_publico(it) for it in res])
        
    else:
        aluno = identidade_aluno()
        if not aluno:
            return jsonify({'success': False, 'message': 'Somente alunos com RM informado podem publicar relatos de perda.'}), 403
        data = request.json or {}
        if request.headers.get('Idempotency-Key'):
            from services.cadastro_offline import enviar
            return enviar(get_db_connection,'mural',data)
        nome, rm, email_aluno = aluno['nome'], aluno['rm'], aluno['email']
        from utils.validacao_item import texto,validar_categoria
        try:
            categoria=texto(data.get('categoria'),'Categoria',50).upper()
            descricao=texto(data.get('descricao'),'Descrição',2000,linhas=True)
            validar_categoria(get_db_connection,categoria)
        except ValueError as error:return jsonify(success=False,message=str(error)),400
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            INSERT INTO mural_perdidos (nome_aluno, rm_aluno, email_aluno, categoria, descricao, data_registro, status) 
            VALUES (%s, %s, %s, %s, %s, %s, 'PROCURANDO') 
            RETURNING id;
        """, (nome, rm, email_aluno, categoria, descricao, datetime.now().strftime("%d/%m/%Y %H:%M")))
        
        matches = []
        try:
            termos_relato = extrair_termos(descricao or "")
            cursor.execute("""
                SELECT id, nome_item as nome, descricao as txt_descricao, categoria, foto, fotos_json 
                FROM itens 
                WHERE aprovado = TRUE AND status = 'DISPONÍVEL' AND categoria = %s;
            """, (categoria,))
            for item in cursor.fetchall():
                try:
                    item['fotos'] = json.loads(item['fotos_json']) if item.get('fotos_json') else ([] if not item.get('foto') else [item['foto']])
                except Exception:
                    item['fotos'] = []
                termos_item = extrair_termos((item.get('nome') or "") + " " + (item.get('txt_descricao') or ""))
                if len(termos_relato.intersection(termos_item)) >= 1:
                    matches.append(item)
        except Exception as e:
            print("[Mural] Erro ao checar matches imediatos:", e)
            
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "matches_encontrados": matches})

@mural_bp.route('/api/mural/aluno/<string:rm>', methods=['OPTIONS', 'GET'])
@token_required
def mural_aluno(rm):
    """Retorna os relatos cadastrados pelo estudante filtrados por seu RM."""
    if request.user.get("role") != "secretaria" and rm != str(request.user.get("rm") or ""):
        return jsonify({"success": False, "message": "Acesso negado."}), 403
    filtro, valor = ("rm_aluno", rm) if request.user.get("role") == "secretaria" else ("email_aluno", request.user.get("email"))
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(f"""
            SELECT id, categoria, descricao, data_registro as data, status 
            FROM mural_perdidos 
            WHERE {filtro} = %s
            ORDER BY id DESC;
        """, (valor,))
        res = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(res)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@mural_bp.route('/api/mural/<int:id>', methods=['OPTIONS', 'DELETE'])
@secretaria_required
def deletar_mural(id):
    """Exclui um relato do mural de perdidos."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM mural_perdidos WHERE id = %s;", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"success": True})

