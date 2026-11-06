"""
Módulo de Segurança e Autenticação
Gerencia verificação de JSON Web Tokens (JWT) e hashing de senhas.
"""
from functools import wraps
from datetime import datetime, timedelta, timezone
from flask import request, jsonify, make_response
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
            if payload.get("auth_version") != 2:
                return jsonify({"success": False, "message": "Faça login novamente para renovar sua sessão.", "expired": True}), 401
            request.user = payload
        except jwt.ExpiredSignatureError:
            return jsonify({
                "success": False, 
                "message": "Sua sessão expirou. Faça login novamente.", 
                "expired": True
            }), 401
        except Exception:
            return jsonify({
                "success": False, 
                "message": "Token inválido. Faça login novamente."
            }), 401

        response = make_response(f(*args, **kwargs))
        response.headers['Cache-Control'] = 'private, no-store'
        response.vary.add('Authorization')
        response.vary.add('x-access-token')
        return response
    return decorated

def secretaria_required(f):
    """Exige uma sessão autenticada com perfil da secretaria."""
    @token_required
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.user.get('role') != 'secretaria':
            return jsonify({"success": False, "message": "Acesso exclusivo da secretaria."}), 403
        return f(*args, **kwargs)
    return decorated

def consulta_publica(f):
    """GET anônimo é público; se houver token, sua validade é obrigatória."""
    autenticado = token_required(f)
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method == 'GET':
            if (request.headers.get('Authorization') or request.headers.get('x-access-token')
                    or request.args.get('token')):
                return autenticado(*args, **kwargs)
            request.user = {}
        response = make_response(f(*args, **kwargs))
        response.headers['Cache-Control'] = 'private, no-store'
        response.vary.add('Authorization')
        response.vary.add('x-access-token')
        return response
    return decorated

def categorias_required(f):
    """Mantém a consulta pública e protege as alterações de categorias."""
    protegido = secretaria_required(f)
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method in ('GET', 'OPTIONS'):
            return f(*args, **kwargs)
        return protegido(*args, **kwargs)
    return decorated

def pode_acessar_chat(rm):
    """O aluno acessa somente o próprio RM; a secretaria atende os alunos."""
    user = request.user
    if user.get('role') == 'secretaria':
        return bool(rm)
    proprio_rm = str(user.get('rm') or '').strip()
    return (
        user.get('role') == 'aluno'
        and proprio_rm.upper() not in ('', 'ALUNO', 'PENDENTE', 'PROFESSOR')
        and str(rm).strip() == proprio_rm
    )

def gerar_token_aluno(email, nome, rm, dias_validade=30):
    """
    Gera um token JWT para sessão do aluno.
    """
    exp = datetime.now(timezone.utc) + timedelta(days=dias_validade)
    return jwt.encode(
        {"email": email, "nome": nome, "rm": rm, "role": "aluno", "auth_version": 2, "exp": exp},
        JWT_SECRET,
        algorithm="HS256"
    )

def gerar_token_secretaria(email, dias_validade=7):
    """
    Gera um token JWT para sessão da secretaria escolar.
    """
    exp = datetime.now(timezone.utc) + timedelta(days=dias_validade)
    return jwt.encode(
        {"user": "secretaria", "role": "secretaria", "email": email, "auth_version": 2, "exp": exp},
        JWT_SECRET,
        algorithm="HS256"
    )

