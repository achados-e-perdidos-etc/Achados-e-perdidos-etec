"""Atendimento por conta. Histórico sem autoria fica restrito à secretaria."""
from datetime import datetime
from flask import request, jsonify, current_app
from psycopg2.extras import RealDictCursor
from utils.security import identidade_aluno, pode_acessar_chat
from utils.helpers import validar_email_institucional
from services import push_delivery


def _destino(cursor, rm, email):
    if request.user.get('role') != 'secretaria':
        conta = identidade_aluno()
        if not conta or not pode_acessar_chat(rm) or (email and email != conta['email']):
            return None, 403
        return conta, None
    if not isinstance(email, str) or not validar_email_institucional(email)[0]:
        return None, 409  # Clientes antigos nunca escolhem destinatário por RM.
    cursor.execute('SELECT email,nome,rm FROM alunos WHERE email=%s;', (email.strip().lower(),))
    conta = cursor.fetchone()
    if not conta or not conta['email'].endswith('@aluno.cps.sp.gov.br'):
        return None, 404
    return conta, None


def enviar(conectar):
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        return jsonify(success=False, message='Envie a mensagem em JSON.'), 400
    msg = dados.get('mensagem')
    if not isinstance(msg, str) or not msg.strip() or len(msg) > 4000 or '\x00' in msg:
        return jsonify(success=False, message='Informe uma mensagem de até 4000 caracteres.'), 400
    user = request.user
    rm = str(dados.get('rm') or user.get('rm') or '').strip()
    # Rejeitar acesso indevido antes de abrir conexão.
    if user.get('role') != 'secretaria' and not pode_acessar_chat(rm):
        return jsonify(success=False, message='Acesso negado a esta conversa.'), 403
    conn = None
    try:
        conn = conectar()
        with conn.cursor(cursor_factory=RealDictCursor) as c:
            conta, erro = _destino(c, rm, dados.get('email') if user.get('role') == 'secretaria' else None)
            if erro: return jsonify(success=False, message='Selecione a conta do aluno na lista de conversas.' if erro == 409 else 'Conversa não autorizada.'), erro
            rem = 'SECRETARIA' if user.get('role') == 'secretaria' else 'ALUNO'
            c.execute('''INSERT INTO mensagens_chat (rm_aluno,nome_aluno,remetente,mensagem,data_envio,email_aluno)
                VALUES (%s,%s,%s,%s,%s,%s);''', (conta['rm'], 'Secretaria' if rem == 'SECRETARIA' else conta['nome'], rem,
                msg.strip(), datetime.now().strftime('%d/%m/%Y %H:%M:%S'), conta['email']))
        conn.commit()
        if rem == 'SECRETARIA':
            try: push_delivery.notificar(conta['email'], 'chat')
            except Exception: current_app.logger.warning('Aviso indisponível; resposta do chat já foi gravada.')
        return jsonify(success=True)
    except Exception:
        if conn: conn.rollback()
        current_app.logger.warning('Falha temporária no envio da conversa.')
        return jsonify(success=False, message='Não foi possível enviar. Sua mensagem pode ser tentada novamente.'), 503
    finally:
        if conn: conn.close()


def mensagens(conectar, rm, legado=False):
    user = request.user
    if legado and user.get('role') != 'secretaria':
        return jsonify(success=False, message='Histórico restrito à secretaria.'), 403
    if not legado and user.get('role') != 'secretaria' and not pode_acessar_chat(rm):
        return jsonify(success=False, message='Acesso negado a esta conversa.'), 403
    conn = None
    try:
        conn = conectar()
        with conn.cursor(cursor_factory=RealDictCursor) as c:
            if legado:
                c.execute("SELECT * FROM mensagens_chat WHERE email_aluno IS NULL AND rm_aluno=%s AND criada_em >= CURRENT_TIMESTAMP - INTERVAL '30 days' ORDER BY id;", (rm,))
                return jsonify(c.fetchall())
            conta, erro = _destino(c, rm, request.args.get('email'))
            if erro: return jsonify(success=False, message='Selecione a conta do aluno para abrir a conversa.'), erro
            c.execute("SELECT * FROM mensagens_chat WHERE email_aluno=%s AND criada_em >= CURRENT_TIMESTAMP - INTERVAL '30 days' ORDER BY id;", (conta['email'],))
            rows = c.fetchall()
            if request.args.get('marcar_lida') == 'true' and rows:
                outro = 'ALUNO' if user.get('role') == 'secretaria' else 'SECRETARIA'
                # Não marcar mensagens recebidas depois do resultado exibido.
                c.execute('UPDATE mensagens_chat SET lida=TRUE WHERE email_aluno=%s AND remetente=%s AND id<=%s AND NOT lida;',
                          (conta['email'], outro, max(r['id'] for r in rows)))
                conn.commit()
            return jsonify(rows)
    except Exception:
        if conn: conn.rollback()
        current_app.logger.warning('Falha temporária ao consultar conversa.')
        return jsonify(success=False, message='Não foi possível carregar a conversa.'), 503
    finally:
        if conn: conn.close()


def conversas(conectar):
    conn = None
    try:
        conn = conectar()
        with conn.cursor(cursor_factory=RealDictCursor) as c:
            c.execute('''SELECT m.email_aluno, (m.email_aluno IS NULL) AS legado,
                (ARRAY_AGG(m.rm_aluno ORDER BY m.id DESC))[1] AS rm_aluno,
                COALESCE((SELECT a.nome FROM alunos a WHERE a.email=m.email_aluno),'Histórico sem autoria') AS nome_aluno,
                (ARRAY_AGG(m.mensagem ORDER BY m.id DESC))[1] AS ultima_mensagem,
                (ARRAY_AGG(m.data_envio ORDER BY m.id DESC))[1] AS ultima_msg_data,
                COUNT(*) FILTER (WHERE m.remetente='ALUNO' AND NOT m.lida) AS nao_lidas
                FROM mensagens_chat m WHERE m.criada_em >= CURRENT_TIMESTAMP - INTERVAL '30 days' GROUP BY m.email_aluno, CASE WHEN m.email_aluno IS NULL THEN m.rm_aluno END
                ORDER BY MAX(m.id) DESC;''')
            return jsonify(c.fetchall())
    except Exception:
        current_app.logger.warning('Falha temporária ao listar atendimentos.')
        return jsonify(success=False, message='Não foi possível atualizar os atendimentos.'), 503
    finally:
        if conn: conn.close()
