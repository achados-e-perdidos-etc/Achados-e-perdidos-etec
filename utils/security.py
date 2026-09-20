"""
Módulo de Segurança e Autenticação
Gerencia verificação de JSON Web Tokens (JWT) e hashing de senhas.
"""
from functools import wraps
from datetime import datetime, timedelta, timezone
from flask import request, jsonify
import jwt
from werkzeug.security import generate_password_hash, check_password_hash
from config import JWT_SECRET

def token_required(f):
    """
    Middleware / Decorator para proteção de rotas privadas (Secretaria e Alunos).
    Injeta o payload decodificado em `request.user`.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method == 'OPTIONS':
            return jsonify({"success": True}), 200

        token = None
        auth_header = request.headers.get('Authorization', '')
        if auth_header:
            parts = auth_header.split()
            if len(parts) >= 2 and parts[0].lower() == 'bearer':
                token = parts[1].strip('"\'')
            elif len(parts) == 1:
                token = parts[0].strip('"\'')

        if not token:
            token = request.headers.get('x-access-token', '').strip('"\'')
        if not token:
            token = request.args.get('token', '').strip('"\'')
        if not token and request.is_json and request.json:
            token = str(request.json.get('token') or '').strip('"\'')

        if not token or token.lower() in ['null', 'undefined', 'none', '']:
            return jsonify({
                "success": False, 
                "message": "Acesso negado: Sessão não encontrada ou token ausente. Faça login novamente."
            }), 401

        try:
            payload = jwt.decode(
                token, 
                JWT_SECRET, 
                algorithms=["HS256"], 
                leeway=timedelta(seconds=60), 
                options={"verify_exp": True}
            )
            request.user = payload
        except jwt.ExpiredSignatureError:
            return jsonify({
                "success": False, 
                "message": "Sua sessão expirou. Faça login novamente.", 
                "expired": True
            }), 401
        except Exception as e:
            return jsonify({
                "success": False, 
                "message": f"Token inválido: {str(e)}"
            }), 401

        return f(*args, **kwargs)
    return decorated

def gerar_token_aluno(email, nome, rm, dias_validade=30):
    """
    Gera um token JWT para sessão do aluno.
    """
    exp = datetime.now(timezone.utc) + timedelta(days=dias_validade)
    return jwt.encode(
        {"email": email, "nome": nome, "rm": rm, "role": "aluno", "exp": exp},
        JWT_SECRET,
        algorithm="HS256"
    )

def gerar_token_secretaria(email, dias_validade=7):
    """
    Gera um token JWT para sessão da secretaria escolar.
    """
    exp = datetime.now(timezone.utc) + timedelta(days=dias_validade)
    return jwt.encode(
        {"user": "secretaria", "role": "secretaria", "email": email, "exp": exp},
        JWT_SECRET,
        algorithm="HS256"
    )
