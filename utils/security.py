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
from utils.professores import email_de_professor
from utils.helpers import validar_email_institucional

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
                options={"verify_exp": True, "require": ["exp", "email", "role"]}
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

        # Permissions are checked on every request, so revocation also affects old tokens.
        request.user.pop('acesso_delegado', None)
        if request.user.get('role') != 'secretaria' and email_de_professor(request.user.get('email')):
            from services.professores_service import buscar_acesso
            try:
                acesso = buscar_acesso(request.user['email'])
            except Exception:
                return jsonify({'success': False, 'message': 'Não foi possível verificar sua permissão. Tente novamente.'}), 503
            request.professor_access = acesso
            if acesso and acesso['status'] == 'APROVADO':
                request.user['role'] = 'secretaria'
                request.user['acesso_delegado'] = True

        if request.user.get('role') not in ('aluno', 'secretaria'):
            return jsonify(success=False, message='Perfil de acesso inválido.'), 403
        request.user['perfil'] = ('moderador' if request.user.get('acesso_delegado') else 'administrador_geral') if request.user['role'] == 'secretaria' else 'aluno'
        request.user['permissoes'] = ((['cadastrar'] if email_de_professor(request.user.get('email')) else ['cadastrar', 'reclamar', 'relatar']) if request.user['role'] == 'aluno'
            else ['moderar', 'entregar', 'auditar'] + ([] if request.user.get('acesso_delegado') else ['gerir_acessos']))

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
    """GET anônimo é público; escritas e consultas com token exigem sessão."""
    autenticado = token_required(f)
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method not in ('GET', 'OPTIONS'):
            return autenticado(*args, **kwargs)
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

def identidade_portal():
    """Identidade assinada para cadastrar objetos, inclusive como professor."""
    user = getattr(request, 'user', {})
    valido, email = validar_email_institucional(user.get('email'))
    professor = email_de_professor(email) if valido else False
    perfil_permitido = user.get('role') == 'aluno' or (
        professor and user.get('role') == 'secretaria' and user.get('acesso_delegado'))
    nome = user.get('nome')
    rm = user.get('rm')
    if not valido or not perfil_permitido or not isinstance(nome, str) or not nome.strip():
        return None
    if not isinstance(rm, str) or not rm.strip():
        return None
    return {'nome': nome, 'email': email, 'rm': 'PROFESSOR' if professor else rm}

def identidade_aluno():
    """Dados da sessão para operações pessoais; não comprova vínculo do RM."""
    identidade = identidade_portal()
    if (not identidade or not identidade['email'].endswith('@aluno.cps.sp.gov.br')
            or request.user.get('role') != 'aluno'
            or identidade['rm'].strip().upper() in ('ALUNO', 'PENDENTE', 'PROFESSOR')):
        return None
    return identidade

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



def secretaria_titular_required(f):
    """Professores podem operar o painel, mas não conceder privilégios."""
    @secretaria_required
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.user.get('acesso_delegado'):
            return jsonify({'success': False, 'message': 'Somente a secretaria titular pode autorizar professores.'}), 403
        return f(*args, **kwargs)
    return decorated
