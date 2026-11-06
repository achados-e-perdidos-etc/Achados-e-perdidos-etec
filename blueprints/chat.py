"""
Blueprint do Chat de Atendimento Multi-Aluno
Comunicação direta em tempo real (polling) entre alunos e secretaria escolar.
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from psycopg2.extras import RealDictCursor

from database import get_db_connection
from services import push_delivery
from utils.security import token_required, secretaria_required, pode_acessar_chat

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/api/chat/enviar', methods=['OPTIONS', 'POST'])
@token_required
def enviar_chat():
    """Envia uma mensagem no chat (origem: ALUNO ou SECRETARIA)."""
    data = request.json or {}
    user = request.user
    rm = str(data.get('rm') or user.get('rm') or '').strip()
    if not pode_acessar_chat(rm):
        return jsonify({'success': False, 'message': 'Acesso negado a esta conversa.'}), 403
    remetente = 'SECRETARIA' if user.get('role') == 'secretaria' else 'ALUNO'
    nome = 'Secretaria' if remetente == 'SECRETARIA' else user.get('nome', 'Aluno')
    mensagem = str(data.get('mensagem') or '').strip()[:4000]
    
    if not rm or not mensagem:
        return jsonify({"success": False, "message": "RM e mensagem são obrigatórios."}), 400
        
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO mensagens_chat (rm_aluno, nome_aluno, remetente, mensagem, data_envio, email_aluno)
        VALUES (%s, %s, %s, %s, %s, %s);
    """, (rm, nome, remetente, mensagem, datetime.now().strftime("%d/%m/%Y %H:%M:%S"), user.get('email') if remetente == 'ALUNO' else None))
    conn.commit()
    cursor.close()
    conn.close()
    if remetente == 'SECRETARIA': push_delivery.notificar_resposta(rm)
    return jsonify({"success": True})

@chat_bp.route('/api/chat/mensagens/<string:rm>', methods=['OPTIONS', 'GET'])
@token_required
def buscar_mensagens(rm):
    """Retorna somente conversas autorizadas pela sessão."""
    if not pode_acessar_chat(rm):
        return jsonify({"success": False, "message": "Acesso negado a esta conversa."}), 403
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM mensagens_chat WHERE rm_aluno = %s ORDER BY id ASC;", (rm,))
    msgs = cursor.fetchall()
    
    # Marca como lida se solicitado pelo leitor
    if request.args.get('marcar_lida', 'false').lower() == 'true' and msgs:
        outro = 'ALUNO' if request.user.get('role') == 'secretaria' else 'SECRETARIA'
        cursor.execute("UPDATE mensagens_chat SET lida = TRUE WHERE rm_aluno = %s AND remetente = %s AND lida = FALSE;", (rm, outro))
        conn.commit()
        
    cursor.close()
    conn.close()
    return jsonify(msgs)

@chat_bp.route('/api/chat/conversas', methods=['OPTIONS', 'GET'])
@secretaria_required
def listar_conversas():
    """
    Lista todos os atendimentos agrupados por aluno para o painel da Secretaria.
    Retorna nome, última mensagem, data/hora e contador de mensagens não lidas.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT m.rm_aluno,
                   COALESCE(
                       (SELECT nome FROM alunos WHERE rm = m.rm_aluno LIMIT 1),
                       (SELECT nome_aluno FROM mensagens_chat WHERE rm_aluno = m.rm_aluno AND remetente = 'ALUNO' ORDER BY id DESC LIMIT 1),
                       'Aluno RM ' || m.rm_aluno
                   ) as nome_aluno,
                   (SELECT mensagem FROM mensagens_chat WHERE rm_aluno = m.rm_aluno ORDER BY id DESC LIMIT 1) as ultima_mensagem,
                   (SELECT data_envio FROM mensagens_chat WHERE rm_aluno = m.rm_aluno ORDER BY id DESC LIMIT 1) as ultima_msg_data,
                   COUNT(CASE WHEN m.remetente = 'ALUNO' AND m.lida = FALSE THEN 1 END) as nao_lidas
            FROM mensagens_chat m
            GROUP BY m.rm_aluno
            ORDER BY MAX(m.id) DESC;
        """)
        res = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(res)
    except Exception as e:
        if conn:
            conn.close()
        return jsonify({"success": False, "error": str(e)}), 500

