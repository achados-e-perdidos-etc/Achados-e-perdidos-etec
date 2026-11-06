from flask import Blueprint, request, jsonify, current_app
from config import VAPID_PUBLIC_KEY
from utils.security import token_required, identidade_portal
from utils.push import validar_assinatura, validar_endpoint
from services import push_service

push_bp = Blueprint('push', __name__)

@push_bp.route('/api/push/public-key', methods=['OPTIONS', 'GET'])
def get_public_key():
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200
    return jsonify({"success": True, "publicKey": VAPID_PUBLIC_KEY})

@push_bp.route('/api/push/subscribe', methods=['OPTIONS', 'POST', 'DELETE'])
@token_required
def salvar_subscricao():
    conta = identidade_portal()
    if not conta:
        return jsonify({'success': False, 'message': 'Entre com sua conta institucional para configurar notificações.'}), 403
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        return jsonify({'success': False, 'message': 'Envie os dados da notificação em JSON.'}), 400
    try:
        valor = (validar_endpoint(dados.get('endpoint')) if request.method == 'DELETE'
                 else validar_assinatura(dados.get('subscription')))
    except ValueError as error:
        return jsonify({'success': False, 'message': str(error)}), 400
    try:
        if request.method == 'DELETE':
            push_service.remover_assinatura(conta['email'], valor)
        else:
            push_service.salvar_assinatura(conta['email'], valor)
        return jsonify({'success': True})
    except Exception:
        # Erros SQL podem conter endpoint/chaves: não registrar seus detalhes.
        current_app.logger.error('Falha ao atualizar vínculo de notificações push.')
        return jsonify({'success': False, 'message': 'Não foi possível atualizar as notificações. Tente novamente.'}), 503
