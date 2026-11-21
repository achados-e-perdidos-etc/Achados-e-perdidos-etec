"""
Blueprint de Autenticação e Gestão de Usuários
Rotas de verificação, cadastro, login convencional, login Google OAuth institucional e redefinição de senha.
"""
import random
import secrets
import requests
from datetime import datetime, timedelta, timezone
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from psycopg2.extras import RealDictCursor

from config import JWT_SECRET, EMAIL_SECRETARIA, ADMIN_SENHA, ADMIN_SENHA_HASH, GOOGLE_CLIENT_ID
from database import get_db_connection
from utils.security import token_required, gerar_token_aluno, gerar_token_secretaria, atualizar_identidade_token, identidade_aluno
from utils.helpers import validar_email_institucional
from services.email_service import disparar_email

auth_bp = Blueprint('auth', __name__)
from blueprints.professores import professores_bp
auth_bp.register_blueprint(professores_bp)

@auth_bp.route('/api/auth/verificar', methods=['GET', 'OPTIONS'])
@token_required
def verificar_token():
    """Valida a sessão ativa retornando os dados do usuário autenticado."""
    return jsonify({"success": True, "user": getattr(request, 'user', {})})

@auth_bp.route('/api/auth/google', methods=['OPTIONS', 'POST'])
def login_google_institucional():
    """
    Autenticação Single Sign-On (SSO) com Google Identity Services.
    Valida o token JWT emitido pelo Google e assegura que o e-mail pertence
    ao domínio oficial do Centro Paula Souza (@aluno.cps.sp.gov.br).
    """
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200

    if not GOOGLE_CLIENT_ID:return jsonify(success=False,message='Login Google não configurado.'),503
    dados = request.get_json(silent=True)
    if not isinstance(dados,dict) or not isinstance(dados.get('credential'),str) or len(dados['credential'])>8192:return jsonify(success=False,message='Credencial inválida.'),400
    credential = dados['credential'].strip()
    
    if not credential:
        return jsonify({"success": False, "message": "Credencial do Google não informada."}), 400

    try:
        # Validação do ID Token na API oficial do Google OAuth2
        resp = requests.get(
            f"https://oauth2.googleapis.com/tokeninfo?id_token={credential}",
            timeout=10
        )
        if resp.status_code != 200:
            return jsonify({"success": False, "message": "Token do Google inválido ou expirado."}), 401
            
        payload = resp.json()
        if payload.get("aud")!=GOOGLE_CLIENT_ID or payload.get("iss") not in ("accounts.google.com","https://accounts.google.com") or int(payload.get("exp",0))<=datetime.now(timezone.utc).timestamp():return jsonify(success=False,message="Credencial do Google inválida."),401
        email = (payload.get('email') or '').strip().lower()
        nome = (payload.get('name') or 'Aluno ETEC').strip()
        picture = payload.get('picture', '')
        email_verified = payload.get('email_verified') in (True, 'true', 'True')
        
        if not email or not email_verified:
            return jsonify({"success": False, "message": "O e-mail da conta Google não foi verificado."}), 400

        # Validação restrita do domínio @aluno.cps.sp.gov.br
        valido, msg_ou_email = validar_email_institucional(email)
        if not valido:
            return jsonify({
                "success": False, 
                "message": f"Acesso exclusivo para alunos e servidores da ETEC. O e-mail '{email}' não pertence ao domínio @aluno.cps.sp.gov.br."
            }), 403

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM alunos WHERE email = %s;", (email,))
        aluno_existente = cursor.fetchone()

        rm = 'PENDENTE'
        if aluno_existente:
            rm = aluno_existente.get('rm') or 'PENDENTE'
            # Atualiza o nome do aluno caso tenha mudado no Google
            cursor.execute("UPDATE alunos SET nome = %s WHERE email = %s;", (nome, email))
            conn.commit()
        else:
            return jsonify(success=False,message='Crie sua conta institucional e aceite os termos antes de usar este acesso.'),403

        cursor.close()
        conn.close()

        token = gerar_token_aluno(email, nome, rm)
        return jsonify({
            "success": True,
            "token": token,
            "aluno": {
                "nome": nome,
                "email": email,
                "rm": rm,
                "picture": picture,
                "precisa_rm": (rm == 'PENDENTE' or not rm)
            }
        })
    except Exception:
        return jsonify(success=False,message="Não foi possível validar o acesso Google."),503
    finally:
        if 'conn' in locals():conn.close()

@auth_bp.route('/api/auth/atualizar-rm', methods=['OPTIONS', 'POST'])
@token_required
def atualizar_rm():
    """Permite ao estudante registrar ou atualizar o seu número de matrícula (RM)."""
    if request.method == 'OPTIONS':
        return jsonify({"success": True}), 200

    dados = request.json or {}
    novo_rm = str(dados.get('rm', '')).strip()
    user = getattr(request, 'user', {})
    email = user.get('email')

    if not identidade_aluno() or not 3<=len(novo_rm)<=20 or not novo_rm.isascii() or not novo_rm.isdigit():
        return jsonify({"success": False, "message": "RM inválido."}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE alunos SET rm = %s WHERE email = %s;", (novo_rm, email))
        cursor.execute("UPDATE mural_perdidos SET rm_aluno = %s WHERE email_aluno = %s;", (novo_rm, email))
        conn.commit()
        cursor.close()
        conn.close()

        # Gera novo token com RM atualizado
        novo_token = atualizar_identidade_token(user,novo_rm)
        return jsonify({"success": True, "token": novo_token, "rm": novo_rm})
    except Exception as e:
        return jsonify(success=False,message="Não foi possível concluir a operação."),503

@auth_bp.route('/api/auth/enviar-codigo', methods=['OPTIONS', 'POST'])
def enviar_codigo():
    if request.method=='OPTIONS':return jsonify(success=True)
    from services.autenticacao_service import operar
    return operar('enviar',get_db_connection)

@auth_bp.route('/api/auth/cadastrar', methods=['OPTIONS', 'POST'])
def cadastrar_aluno():
    if request.method=='OPTIONS':return jsonify(success=True)
    from services.autenticacao_service import operar
    return operar('cadastrar',get_db_connection)

@auth_bp.route('/api/auth/login-aluno', methods=['OPTIONS', 'POST'])
def login_aluno():
    if request.method=='OPTIONS':return jsonify(success=True)
    from services.autenticacao_service import operar
    return operar('login',get_db_connection)

@auth_bp.route('/api/auth/redefinir', methods=['OPTIONS', 'POST'])
def redefinir_senha():
    if request.method=='OPTIONS':return jsonify(success=True)
    from services.autenticacao_service import operar
    return operar('redefinir',get_db_connection)

@auth_bp.route('/api/login', methods=['OPTIONS', 'POST'])
def login_secretaria():
    if request.method=='OPTIONS':return jsonify(success=True)
    from services.autenticacao_service import administrador
    return administrador(get_db_connection,EMAIL_SECRETARIA,ADMIN_SENHA_HASH,ADMIN_SENHA)
