"""Acesso de professores sujeito à decisão da secretaria titular."""
import logging
from flask import Blueprint, jsonify, request
from utils.security import token_required, secretaria_titular_required
from utils.professores import email_de_professor
from services import professores_service as service

professores_bp = Blueprint('professores', __name__)

def _falha():
    logging.getLogger(__name__).exception('Falha ao processar acesso de professor')
    return jsonify({'success': False, 'message': 'Não foi possível consultar ou atualizar o acesso. Tente novamente.'}), 503

@professores_bp.route('/api/professores/acesso', methods=['GET', 'POST', 'OPTIONS'])
@token_required
def meu_acesso():
    user = request.user
    if not email_de_professor(user.get('email')) or (user.get('role') != 'aluno' and not user.get('acesso_delegado')):
        return jsonify({'success': False, 'message': 'Recurso disponível para contas institucionais de professores.'}), 403
    try:
        result = service.solicitar_acesso(user['email']) if request.method == 'POST' else getattr(request, 'professor_access', None)
        if request.method == 'POST' and not result:
            return jsonify({'success': False, 'message': 'Conta não encontrada. Faça login novamente.'}), 403
        return jsonify({'success': True, 'status': result['status'] if result else 'NAO_SOLICITADO'})
    except Exception:
        return _falha()

@professores_bp.route('/api/secretaria/professores', methods=['GET', 'OPTIONS'])
@secretaria_titular_required
def listar():
    try:
        return jsonify({'success': True, 'solicitacoes': service.listar_acessos()})
    except Exception:
        return _falha()

@professores_bp.route('/api/secretaria/professores/<path:email>/acesso', methods=['PUT', 'OPTIONS'])
@secretaria_titular_required
def decidir(email):
    email = email.strip().lower()
    acao = str((request.get_json(silent=True) or {}).get('acao') or '').upper()
    if not email_de_professor(email) or acao not in ('APROVAR', 'RECUSAR', 'REVOGAR'):
        return jsonify({'success': False, 'message': 'Ação ou professor inválido.'}), 400
    try:
        result = service.decidir_acesso(email, acao, request.user['email'])
        if not result:
            return jsonify({'success': False, 'message': 'A solicitação mudou. Atualize a lista antes de decidir.'}), 409
        return jsonify({'success': True, 'status': result['status']})
    except Exception:
        return _falha()
