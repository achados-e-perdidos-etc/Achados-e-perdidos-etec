"""
Blueprint do Mural de Relatos de Perda
Permite aos estudantes registrar relatos públicos de pertences perdidos.
"""
import json
from datetime import datetime
from flask import Blueprint, request, jsonify
from psycopg2.extras import RealDictCursor

from database import get_db_connection
from utils.security import token_required
from utils.helpers import extrair_termos

mural_bp = Blueprint('mural', __name__)

@mural_bp.route('/api/mural', methods=['OPTIONS', 'GET', 'POST'])
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
        return jsonify(res)
        
    else:
        data = request.json or {}
        nome = data.get('nome')
        rm = data.get('rm')
        email_aluno = data.get('email')
        categoria = data.get('categoria')
        descricao = data.get('descricao')
        
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
def mural_aluno(rm):
    """Retorna os relatos cadastrados pelo estudante filtrados por seu RM."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT id, categoria, descricao, data_registro as data, status 
            FROM mural_perdidos 
            WHERE rm_aluno = %s 
            ORDER BY id DESC;
        """, (rm,))
        res = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(res)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@mural_bp.route('/api/mural/<int:id>', methods=['OPTIONS', 'DELETE'])
@token_required
def deletar_mural(id):
    """Exclui um relato do mural de perdidos."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM mural_perdidos WHERE id = %s;", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"success": True})
