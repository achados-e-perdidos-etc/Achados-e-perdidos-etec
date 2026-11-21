from flask import Blueprint, jsonify, request, current_app
from psycopg2.extras import RealDictCursor
from database import get_db_connection
from utils.security import token_required, identidade_portal

notificacoes_bp = Blueprint('notificacoes', __name__)


@notificacoes_bp.route('/api/notificacoes', methods=['GET', 'OPTIONS'])
@notificacoes_bp.route('/api/notificacoes/lidas', methods=['PUT', 'OPTIONS'])
@notificacoes_bp.route('/api/notificacoes/<int:aviso_id>/lida', methods=['PUT', 'OPTIONS'])
@token_required
def notificacoes(aviso_id=None):
    conta = identidade_portal()
    if not conta:
        return jsonify(success=False, message='Entre com sua conta do portal.'), 403
    antes = request.args.get('antes')
    dados = request.get_json(silent=True) or {}
    ate = dados.get('ate_id') if isinstance(dados, dict) else None
    if request.method == 'GET' and antes is not None:
        if not antes.isdecimal() or not 0 < int(antes) <= 9223372036854775807:
            return jsonify(success=False, message='Página inválida.'), 400
    if request.method == 'PUT' and aviso_id is None and (type(ate) is not int or not 0 < ate <= 9223372036854775807):
        return jsonify(success=False, message='Informe o último aviso exibido.'), 400
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as c:
            if request.method == 'GET':
                c.execute('SELECT COUNT(*) AS total FROM notificacoes WHERE email_aluno=%s AND NOT lida;', (conta['email'],))
                total = c.fetchone()['total']
                c.execute('''SELECT id,evento,titulo,corpo,criada_em,lida FROM notificacoes
                    WHERE email_aluno=%s AND (%s::bigint IS NULL OR id < %s)
                    ORDER BY id DESC LIMIT 31;''', (conta['email'], antes, antes))
                rows = c.fetchall()
                for row in rows: row['criada_em'] = row['criada_em'].isoformat()
                return jsonify(success=True, notificacoes=rows[:30], nao_lidas=total, tem_mais=len(rows)>30)
            if aviso_id is not None:
                c.execute('UPDATE notificacoes SET lida=TRUE WHERE id=%s AND email_aluno=%s RETURNING id;', (aviso_id, conta['email']))
                if not c.fetchone(): return jsonify(success=False, message='Aviso não encontrado.'), 404
            else:
                # Não marcar avisos que chegaram depois da tela exibida.
                c.execute('UPDATE notificacoes SET lida=TRUE WHERE email_aluno=%s AND id<=%s;', (conta['email'], ate))
            conn.commit()
            return jsonify(success=True)
    except Exception:
        if conn: conn.rollback()
        current_app.logger.warning('Central de notificações temporariamente indisponível.')
        return jsonify(success=False, message='Não foi possível carregar seus avisos. Tente novamente.'), 503
    finally:
        if conn: conn.close()
