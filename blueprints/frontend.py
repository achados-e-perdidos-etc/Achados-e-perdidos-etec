"""
Blueprint de Interface Web e Arquivos Estáticos
Roteamento para index.html, painel da secretaria, recursos visuais e tratamento de erro 404.
"""
import os
from flask import Blueprint, send_from_directory, request, current_app, jsonify

frontend_bp = Blueprint('frontend', __name__)

@frontend_bp.route('/logo_secretaria.png')
def logo_secretaria():
    return send_from_directory(current_app.root_path, 'logo_secretaria.png')

@frontend_bp.route('/favicon.ico')
def favicon():
    ref = request.headers.get('Referer', '')
    if 'controle_etec' in ref or 'secretaria' in ref or 'admin' in ref:
        return send_from_directory(current_app.root_path, 'logo_secretaria.png')
    return send_from_directory(current_app.root_path, 'logo.png')

@frontend_bp.route('/controle_etec_7788.html')
@frontend_bp.route('/secretaria')
@frontend_bp.route('/admin')
def secretaria_web():
    return send_from_directory(current_app.root_path, 'controle_etec_7788.html')

@frontend_bp.route('/')
def home():
    return send_from_directory(current_app.root_path, 'index.html')

@frontend_bp.app_errorhandler(404)
def pagina_nao_encontrada(erro):
    """
    Tratamento universal de erro 404.
    - Requisições de API (/api/...) -> Resposta JSON.
    - Qualquer rota no navegador -> Exibe a página interativa 404.html da raiz.
    """
    if request.path.startswith('/api/'):
        return jsonify({'erro': 'Rota de API não encontrada'}), 404

    # Busca o 404.html diretamente na raiz do projeto
    caminho_404 = os.path.join(current_app.root_path, '404.html')
    if os.path.exists(caminho_404):
        return send_from_directory(current_app.root_path, '404.html'), 404

    # Fallback caso o Flask esteja utilizando static_folder na raiz
    try:
        return send_from_directory(current_app.static_folder, '404.html'), 404
    except Exception:
        return 'Página não encontrada', 404
