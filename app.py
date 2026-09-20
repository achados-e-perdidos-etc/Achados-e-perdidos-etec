"""
Fábrica da Aplicação Flask (Application Factory)
ETEC Achados e Perdidos - Versão 3.0 Completa (Fases 1, 2 e 3 com IA)
"""
import os
import traceback
from flask import Flask, request, jsonify
from flask_cors import CORS

from config import BASE_DIR, DATABASE_URL
from database import init_db
from blueprints.auth import auth_bp
from blueprints.itens import itens_bp
from blueprints.mural import mural_bp
from blueprints.chat import chat_bp
from blueprints.relatorios import relatorios_bp
from blueprints.frontend import frontend_bp
from blueprints.push import push_bp
from blueprints.ai import ai_bp

def create_app():
    """
    Inicializa e configura a aplicação Flask com todos os seus módulos e middlewares.
    """
    app = Flask(__name__, static_folder=BASE_DIR, static_url_path='')
    
    # Configuração de CORS para chamadas da API
    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=False)
    
    # Middleware: Tratamento de requisições preflight (OPTIONS)
    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            res = jsonify({"success": True})
            res.headers['Access-Control-Allow-Origin'] = '*'
            res.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            res.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
            res.headers['Access-Control-Max-Age'] = '86400'
            return res, 200

    # Middleware: Cabeçalhos HTTP de segurança e controle de cache
    @app.after_request
    def after_request(response):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, Accept, x-access-token'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, PATCH'
        if request.path.endswith('.html') or request.path == '/' or request.path.endswith('.js'):
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        return response

    # Manipulador global de exceções não capturadas
    @app.errorhandler(Exception)
    def handle_global_exception(e):
        tb = traceback.format_exc()
        print(f"🔥 [ERRO FLASK GLOBAL] {request.method} {request.path}:\n{tb}")
        return jsonify({
            "success": False,
            "error": str(e),
            "tipo": type(e).__name__,
            "metodo": request.method,
            "rota": request.path,
            "traceback": tb,
            "message": f"Erro interno no servidor ao processar {request.method} {request.path}: {str(e)}"
        }), 500

    # Registro de todos os Blueprints
    app.register_blueprint(frontend_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(itens_bp)
    app.register_blueprint(mural_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(relatorios_bp)
    app.register_blueprint(push_bp)
    app.register_blueprint(ai_bp)

    # Inicialização do banco se DATABASE_URL estiver configurada
    if DATABASE_URL:
        init_db()

    return app

# Instância da aplicação para execução via WSGI (Gunicorn / Railway)
app = create_app()

if __name__ == "__main__":
    from config import PORT
    app.run(host='0.0.0.0', port=PORT)
