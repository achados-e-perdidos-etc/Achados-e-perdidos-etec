"""
Blueprint de Autenticação e Gestão de Usuários
Rotas de verificação, cadastro, login e redefinição de senha para alunos e secretaria.
"""
import random
from datetime import datetime, timedelta, timezone
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from psycopg2.extras import RealDictCursor

from config import JWT_SECRET, EMAIL_SECRETARIA, ADMIN_SENHA, ADMIN_SENHA_HASH
from database import get_db_connection
from utils.security import token_required, gerar_token_aluno, gerar_token_secretaria
from utils.helpers import validar_email_institucional
from services.email_service import disparar_email

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/api/auth/verificar', methods=['GET', 'OPTIONS'])
@token_required
def verificar_token():
    """Valida a sessão ativa retornando os dados do usuário autenticado."""
    return jsonify({"success": True, "user": getattr(request, 'user', {})})

@auth_bp.route('/api/auth/enviar-codigo', methods=['OPTIONS', 'POST'])
def enviar_codigo():
    """
    Envia código de verificação numérico de 6 dígitos para o e-mail institucional.
    Valida domínios oficiais (@aluno.cps.sp.gov.br e institucionais associados).
    """
    email_bruto = request.json.get('email', '')
    valido, res = validar_email_institucional(email_bruto)
    if not valido:
        return jsonify({"success": False, "message": res}), 400
    
    email = res
    codigo = str(random.randint(100000, 999999))
    expiracao = datetime.now() + timedelta(minutes=15)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO codigos_auth (email, codigo, expiracao) 
            VALUES (%s, %s, %s) 
            ON CONFLICT (email) DO UPDATE 
            SET codigo = EXCLUDED.codigo, expiracao = EXCLUDED.expiracao;
        """, (email, codigo, expiracao))
        conn.commit()
        cursor.close()
        conn.close()
        
        html = f"""
        <div style="font-family: Arial, sans-serif; padding: 24px; background: #0d1117; color: #c9d1d9; border-radius: 12px; max-width: 500px; margin: auto;">
            <h2 style="color: #dc2626; margin-top: 0;">ETEC Achados e Perdidos</h2>
            <p style="font-size: 14px;">Olá estudante! Utilize o código abaixo para autenticar sua conta no sistema:</p>
            <div style="background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; text-align: center; margin: 20px 0;">
                <span style="font-size: 32px; font-weight: bold; letter-spacing: 6px; color: #10b981;">{codigo}</span>
            </div>
            <p style="font-size: 12px; color: #8b949e;">Este código expira em 15 minutos. Se você não solicitou, desconsidere esta mensagem.</p>
        </div>
        """
        disparar_email(email, "Seu código de acesso - ETEC Achados e Perdidos", html)
        return jsonify({"success": True, "message": "Código enviado para seu e-mail institucional."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@auth_bp.route('/api/auth/cadastrar', methods=['OPTIONS', 'POST'])
def cadastrar_aluno():
    """Valida o código de 6 dígitos e cadastra o aluno com senha criptografada."""
    data = request.json or {}
    email_bruto = data.get('email', '')
    codigo = data.get('codigo', '').strip()
    nome = data.get('nome', '').strip()
    rm = data.get('rm', '').strip()
    senha = data.get('senha', '').strip()

    valido, res = validar_email_institucional(email_bruto)
    if not valido:
        return jsonify({"success": False, "message": res}), 400
    email = res

    if not all([codigo, nome, rm, senha]):
        return jsonify({"success": False, "message": "Todos os campos são obrigatórios."}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT codigo, expiracao FROM codigos_auth WHERE email = %s;", (email,))
        reg = cursor.fetchone()
        
        if not reg or reg['codigo'] != codigo or reg['expiracao'] < datetime.now():
            return jsonify({"success": False, "message": "Código inválido ou expirado."}), 400
        
        cursor.execute("SELECT email FROM alunos WHERE email = %s;", (email,))
        if cursor.fetchone():
            return jsonify({"success": False, "message": "E-mail já cadastrado. Faça login."}), 400
        
        senha_hash = generate_password_hash(senha)
        cursor.execute(
            "INSERT INTO alunos (email, nome, rm, senha_hash) VALUES (%s, %s, %s, %s);", 
            (email, nome, rm, senha_hash)
        )
        cursor.execute("DELETE FROM codigos_auth WHERE email = %s;", (email,))
        conn.commit()
        cursor.close()
        conn.close()
        
        token = gerar_token_aluno(email, nome, rm)
        return jsonify({
            "success": True, 
            "token": token, 
            "aluno": {"nome": nome, "rm": rm, "email": email}
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@auth_bp.route('/api/auth/login-aluno', methods=['OPTIONS', 'POST'])
def login_aluno():
    """Autentica o aluno via e-mail institucional e senha com verificação de hash."""
    dados = request.json or {}
    email = dados.get('email', '').lower().strip()
    senha = dados.get('senha', '').strip()
    
    if not email or not senha:
        return jsonify({"success": False, "message": "Informe e-mail e senha."}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM alunos WHERE email = %s;", (email,))
        aluno = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if aluno and check_password_hash(aluno['senha_hash'], senha):
            token = gerar_token_aluno(aluno['email'], aluno['nome'], aluno['rm'])
            return jsonify({
                "success": True, 
                "token": token, 
                "aluno": {"nome": aluno['nome'], "rm": aluno['rm'], "email": aluno['email']}
            })
        return jsonify({"success": False, "message": "Senha incorreta ou usuário não encontrado."}), 401
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@auth_bp.route('/api/auth/redefinir', methods=['OPTIONS', 'POST'])
def redefinir_senha():
    """Redefine a senha do aluno após confirmação do código enviado por e-mail."""
    dados = request.json or {}
    email = dados.get('email', '').lower().strip()
    codigo = dados.get('codigo', '').strip()
    nova_senha = dados.get('senha', '').strip()
    
    if not all([email, codigo, nova_senha]):
        return jsonify({"success": False, "message": "Preencha todos os campos."}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT codigo, expiracao FROM codigos_auth WHERE email = %s;", (email,))
        reg = cursor.fetchone()
        if not reg or reg['codigo'] != codigo or reg['expiracao'] < datetime.now():
            return jsonify({"success": False, "message": "Código inválido ou expirado."}), 400
        
        senha_hash = generate_password_hash(nova_senha)
        cursor.execute("UPDATE alunos SET senha_hash = %s WHERE email = %s;", (senha_hash, email))
        cursor.execute("DELETE FROM codigos_auth WHERE email = %s;", (email,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "Senha redefinida com sucesso."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@auth_bp.route('/api/login', methods=['OPTIONS', 'POST'])
def login_secretaria():
    """Autentica o operador da secretaria escolar gerando token de administrador."""
    dados = request.json or {}
    email = (dados.get('email') or '').strip().lower()
    senha = (dados.get('senha') or '').strip()
    
    if not email or not senha:
        return jsonify({"success": False, "message": "Preencha e-mail e senha."}), 400

    login_valido = False
    if email == EMAIL_SECRETARIA:
        if ADMIN_SENHA and senha == ADMIN_SENHA:
            login_valido = True
        elif ADMIN_SENHA_HASH:
            try:
                login_valido = check_password_hash(ADMIN_SENHA_HASH, senha)
            except Exception:
                login_valido = (senha == ADMIN_SENHA_HASH)

    if login_valido:
        token = gerar_token_secretaria(email)
        return jsonify({"success": True, "token": token})
    return jsonify({"success": False, "message": "Credenciais inválidas."}), 401
