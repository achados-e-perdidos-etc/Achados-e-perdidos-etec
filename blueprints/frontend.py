"""
Blueprint de Interface Web e Arquivos Estáticos
Roteamento para index.html, painel da secretaria, recursos visuais e tratamento de erro 404.
"""
from flask import Blueprint, send_from_directory, request, current_app, jsonify

frontend_bp = Blueprint('frontend', __name__)

@frontend_bp.route('/logo_secretaria.png')
def logo_secretaria():
    return send_from_directory(current_app.static_folder, 'logo_secretaria.png')

@frontend_bp.route('/favicon.ico')
def favicon():
    ref = request.headers.get('Referer', '')
    if 'controle_etec' in ref or 'secretaria' in ref or 'admin' in ref:
        return send_from_directory(current_app.static_folder, 'logo_secretaria.png')
    return send_from_directory(current_app.static_folder, 'logo.png')

@frontend_bp.route('/controle_etec_7788.html')
@frontend_bp.route('/secretaria')
@frontend_bp.route('/admin')
def secretaria_web():
    return send_from_directory(current_app.static_folder, 'controle_etec_7788.html')

@frontend_bp.route('/')
def home():
    return send_from_directory(current_app.static_folder, 'index.html')

@frontend_bp.app_errorhandler(404)
def pagina_nao_encontrada(erro):
    """
    404 personalizado.
    - Chamadas de API (/api/...) -> resposta curta em JSON.
    - Qualquer outra rota/página no navegador -> renderiza a tela 404.html interativa.
    """
    if request.path.startswith('/api/'):
        return jsonify({'erro': 'Rota de API não encontrada'}), 404

    try:
        resposta = send_from_directory(current_app.static_folder, '404.html')
        resposta.status_code = 404
        return resposta
    except Exception:
        return 'Página não encontrada', 404
