from flask import Blueprint, request, jsonify, current_app
from services import push_delivery
from utils.security import token_required, identidade_portal
from utils.push import validar_assinatura, validar_endpoint
from services import push_service

push_bp = Blueprint('push', __name__)

@push_bp.route('/api/push/public-key', methods=['OPTIONS', 'GET'])
def get_public_key():
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200
    chave = push_delivery.chave_publica()
    response = jsonify({'success': bool(chave), 'habilitado': bool(chave), 'publicKey': chave})
    response.headers['Cache-Control'] = 'no-store'
    return response

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


@push_bp.before_app_request
def iniciar_envios_pendentes():
    # Inicialização preguiçosa após migrações, inclusive para retomar a fila após restart.
    if current_app.config.get('PUSH_AUTOSTART', True) and push_delivery.configuracao():
        push_delivery.acordar_worker()


@push_bp.route('/api/push/test', methods=['POST', 'OPTIONS'])
@token_required
def testar_envio():
    conta = identidade_portal()
    if not conta:
        return jsonify({'success': False, 'message': 'Entre com sua conta institucional.'}), 403
    try:
        resultado = push_delivery.enfileirar_teste(conta['email'])
    except Exception:
        current_app.logger.warning('Não foi possível solicitar teste de notificação.')
        return jsonify({'success': False, 'message': 'Não foi possível solicitar o teste agora.'}), 503
    if resultado == 'desabilitado':
        return jsonify({'success': False, 'message': 'As notificações ainda não foram configuradas neste servidor.'}), 503
    if resultado == 'limite':
        return jsonify({'success': False, 'message': 'Aguarde 30 segundos antes de solicitar outro teste.'}), 429
    if resultado == 'sem_dispositivo':
        return jsonify({'success': False, 'message': 'Ative as notificações neste dispositivo antes do teste.'}), 400
    return jsonify({'success': True, 'queued': True, 'message': 'Teste solicitado. Aguarde a notificação.'}), 202
