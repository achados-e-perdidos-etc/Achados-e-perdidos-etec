import json
from flask import Blueprint, request, jsonify
from config import VAPID_PUBLIC_KEY
from database import get_db_connection

push_bp = Blueprint('push', __name__)

@push_bp.route('/api/push/public-key', methods=['OPTIONS', 'GET'])
def get_public_key():
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200
    return jsonify({"success": True, "publicKey": VAPID_PUBLIC_KEY})

@push_bp.route('/api/push/subscribe', methods=['OPTIONS', 'POST'])
def salvar_subscricao():
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200

    dados = request.json or {}
    rm = str(dados.get('rm') or '').strip()
    sub_data = dados.get('subscription')

    if not rm or not sub_data:
        return jsonify({"success": False, "message": "RM e dados de assinatura são obrigatórios."}), 400

    sub_json = json.dumps(sub_data) if isinstance(sub_data, (dict, list)) else str(sub_data)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO push_subscriptions (rm_aluno, subscription_json) 
            VALUES (%s, %s) 
            ON CONFLICT (rm_aluno) DO UPDATE 
            SET subscription_json = EXCLUDED.subscription_json;
        """, (rm, sub_json))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "Notificações push ativadas para este dispositivo."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
