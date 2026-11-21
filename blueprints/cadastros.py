from flask import Blueprint, jsonify, request, current_app
from psycopg2.extras import RealDictCursor
from database import get_db_connection
from utils.security import token_required, identidade_portal

cadastros_bp = Blueprint('cadastros', __name__)

@cadastros_bp.route('/api/itens/cadastrados-por-mim', methods=['GET','OPTIONS'])
@token_required
def meus_cadastros():
    conta = identidade_portal()
    if not conta: return jsonify(success=False, message='Entre com sua conta do portal.'), 403
    antes = request.args.get('antes')
    if antes is not None and (not antes.isdecimal() or not 0 < int(antes) <= 9223372036854775807):
        return jsonify(success=False, message='Página inválida.'), 400
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as c:
            c.execute('''SELECT id,item_id,nome,categoria,situacao,motivo_recusa,enviado_em,atualizado_em FROM cadastros_itens
                WHERE email_aluno=%s AND (%s::bigint IS NULL OR id<%s) ORDER BY id DESC LIMIT 31;''',
                (conta['email'],antes,antes))
            rows = c.fetchall()
            for row in rows:
                for key in ['enviado_em','atualizado_em']: row[key] = row[key].isoformat()
            return jsonify(success=True,cadastros=rows[:30],tem_mais=len(rows)>30)
    except Exception:
        current_app.logger.warning('Não foi possível consultar os cadastros da conta.')
        return jsonify(success=False,message='Não foi possível carregar seus cadastros.'), 503
    finally:
        if conn: conn.close()
