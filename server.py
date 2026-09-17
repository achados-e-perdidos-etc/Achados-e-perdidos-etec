import os
import json
import re
import psycopg2
import requests
import random
from threading import Thread
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta, timezone
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import cloudinary
import cloudinary.uploader
import jwt

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, static_folder=BASE_DIR, static_url_path='')

# Configuração de CORS para permitir Web, Mobile e PWAs
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=False)

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

DATABASE_URL = os.environ.get("DATABASE_URL")

cloudinary.config( 
  cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME"), 
  api_key = os.environ.get("CLOUDINARY_API_KEY"), 
  api_secret = os.environ.get("CLOUDINARY_API_SECRET"),
  secure = True
)

# Chave secreta oficial do JWT
JWT_SECRET = os.environ.get("JWT_SECRET", "@#Etec_Achad0s_2026_Secret_T0ken!)").strip()
EMAIL_SECRETARIA = os.environ.get("ADMIN_EMAIL", "achadoseperdidosetec@gmail.com").strip().lower()

# Senha da secretaria definida no Railway
ADMIN_SENHA = os.environ.get("ADMIN_SENHA", "").strip()
ADMIN_SENHA_HASH = os.environ.get("ADMIN_SENHA_HASH", "").strip()

BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
SMTP_SENDER = os.environ.get("SMTP_SENDER", "achadoseperdidosetec@gmail.com")

# ==========================================
# SEGURANÇA E VALIDAÇÃO JWT
# ==========================================
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method == 'OPTIONS':
            return jsonify({"success": True}), 200

        token = None
        auth_header = request.headers.get('Authorization', '')
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == 'bearer':
                token = parts.strip('"\'' )
            elif len(parts) == 1:
                token = parts[0].strip('"\'' )

        if not token:
            token = request.args.get('token', '').strip('"\'' )

        if not token or token.lower() in ['null', 'undefined', 'none', '']:
            return jsonify({"success": False, "message": "Acesso negado: Token ausente."}), 401

        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"], leeway=timedelta(seconds=60), options={"verify_exp": True})
            request.user = payload
        except jwt.ExpiredSignatureError:
            return jsonify({"success": False, "message": "Sessão expirada. Faça login novamente.", "expired": True}), 401
        except Exception as e:
            return jsonify({"success": False, "message": f"Token inválido: {str(e)}"}), 401

        return f(*args, **kwargs)
    return decorated

def get_db_connection(): 
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def extrair_termos(texto):
    if not texto: return set()
    STOPWORDS = {'perdi', 'minha', 'meu', 'uma', 'um', 'no', 'na', 'em', 'de', 'da', 'do', 'com', 'sem', 'favor', 'acho', 'que'}
    palavras = re.findall(r'[a-zA-Z0-9áéíóúãõâêîôûç]+', texto.lower())
    termos = set()
    for p in palavras:
        if len(p) >= 3 and p not in STOPWORDS: termos.add(p)
    return termos

def processar_fotos(fotos_array):
    urls_finais = []
    if not fotos_array: return urls_finais
    for foto in fotos_array:
        if foto.startswith('http'): 
            urls_finais.append(foto)
        else:
            try: 
                urls_finais.append(cloudinary.uploader.upload(foto, folder="etec_achados")["secure_url"])
            except Exception as e: 
                print(f"Erro Cloudinary: {e}")
    return urls_finais

def enviar_email_api_async(destinatario, assunto, html_content):
    if not BREVO_API_KEY or not destinatario: return
    try:
        requests.post("https://api.brevo.com/v3/smtp/email", json={
            "sender": {"name": "Achados e Perdidos ETEC", "email": SMTP_SENDER},
            "to": [{"email": destinatario}], "subject": assunto, "htmlContent": html_content
        }, headers={"accept": "application/json", "api-key": BREVO_API_KEY, "content-type": "application/json"})
    except: pass

def disparar_email(destinatario, assunto, html_content):
    Thread(target=enviar_email_api_async, args=(destinatario, assunto, html_content)).start()

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('CREATE TABLE IF NOT EXISTS categorias (id SERIAL PRIMARY KEY, nome VARCHAR(50) UNIQUE NOT NULL);')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS itens (
            id SERIAL PRIMARY KEY, nome_item VARCHAR(150), descricao TEXT NOT NULL, categoria VARCHAR(50) NOT NULL, 
            data_encontrado VARCHAR(20) NOT NULL, local_encontrado VARCHAR(100) NOT NULL, foto_base64 TEXT, 
            fotos_json TEXT, status VARCHAR(30) DEFAULT 'DISPONÍVEL', solicitado_por VARCHAR(100), rm_aluno VARCHAR(20), 
            email_solicitante VARCHAR(150), aprovado BOOLEAN DEFAULT TRUE, cadastrado_por_aluno BOOLEAN DEFAULT FALSE
        );''')
        
        # Auto-reparo: adiciona colunas que possam faltar em bancos já existentes
        colunas_migracao = [
            ("nome_item", "VARCHAR(150)"),
            ("foto_base64", "TEXT"),
            ("fotos_json", "TEXT"),
            ("status", "VARCHAR(30) DEFAULT 'DISPONÍVEL'"),
            ("solicitado_por", "VARCHAR(100)"),
            ("rm_aluno", "VARCHAR(20)"),
            ("email_solicitante", "VARCHAR(150)"),
            ("aprovado", "BOOLEAN DEFAULT TRUE"),
            ("cadastrado_por_aluno", "BOOLEAN DEFAULT FALSE")
        ]
        for col_nome, col_tipo in colunas_migracao:
            try:
                cursor.execute(f"ALTER TABLE itens ADD COLUMN IF NOT EXISTS {col_nome} {col_tipo};")
            except Exception:
                conn.rollback()

        # Sincroniza a sequência de numeração do ID
        try:
            cursor.execute("SELECT setval(pg_get_serial_sequence('itens', 'id'), COALESCE((SELECT MAX(id) FROM itens), 1));")
        except Exception:
            conn.rollback()

        cursor.execute('''CREATE TABLE IF NOT EXISTS entregues (id SERIAL PRIMARY KEY, item_id INT NOT NULL, nome_item TEXT NOT NULL, retirado_por VARCHAR(100) NOT NULL, rm_retirante VARCHAR(30) NOT NULL, turma_curso VARCHAR(50), data_entrega VARCHAR(30) NOT NULL, funcionario_responsavel VARCHAR(100));''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS mural_perdidos (id SERIAL PRIMARY KEY, nome_aluno VARCHAR(100) NOT NULL, rm_aluno VARCHAR(20) NOT NULL, email_aluno VARCHAR(150), categoria VARCHAR(50) NOT NULL, descricao TEXT NOT NULL, data_registro VARCHAR(30) NOT NULL, status VARCHAR(30) DEFAULT 'PROCURANDO');''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS mensagens_chat (id SERIAL PRIMARY KEY, rm_aluno VARCHAR(20) NOT NULL, nome_aluno VARCHAR(100) NOT NULL, remetente VARCHAR(20) NOT NULL, mensagem TEXT NOT NULL, data_envio VARCHAR(30) NOT NULL, lida BOOLEAN DEFAULT FALSE);''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS alunos (email VARCHAR(150) PRIMARY KEY, nome VARCHAR(100) NOT NULL, rm VARCHAR(20) NOT NULL, senha_hash TEXT NOT NULL);''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS codigos_auth (email VARCHAR(150) PRIMARY KEY, codigo VARCHAR(6) NOT NULL, expiracao TIMESTAMP NOT NULL);''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS push_subscriptions (id SERIAL PRIMARY KEY, rm_aluno VARCHAR(20) UNIQUE NOT NULL, subscription_json TEXT NOT NULL);''')

        cursor.execute("SELECT COUNT(*) FROM categorias;")
        if cursor.fetchone()[0] == 0:
            for c in ['MOCHILA', 'ROUPAS', 'ACESSÓRIOS', 'ESCOLARES', 'ELETRÔNICOS', 'OUTROS']:
                cursor.execute("INSERT INTO categorias (nome) VALUES (%s) ON CONFLICT DO NOTHING;", (c,))

        conn.commit(); cursor.close(); conn.close()
    except Exception as e: 
        print(f"Erro DB init: {e}")

if DATABASE_URL: init_db()

@app.route('/')
def home(): 
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/auth/verificar', methods=['GET', 'OPTIONS'])
@token_required
def verificar_token():
    return jsonify({"success": True, "user": getattr(request, 'user', {})})

@app.route('/api/auth/enviar-codigo', methods=['POST'])
def enviar_codigo():
    email = request.json.get('email', '').strip().lower()
    if not email.endswith('@aluno.cps.sp.gov.br'): 
        return jsonify({"success": False, "message": "Use apenas o e-mail institucional (@aluno.cps.sp.gov.br)."}), 400
    
    codigo = str(random.randint(100000, 999999))
    expiracao = datetime.now() + timedelta(minutes=15)
    try:
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute("INSERT INTO codigos_auth (email, codigo, expiracao) VALUES (%s, %s, %s) ON CONFLICT (email) DO UPDATE SET codigo = EXCLUDED.codigo, expiracao = EXCLUDED.expiracao;", (email, codigo, expiracao))
        conn.commit(); cursor.close(); conn.close()
        html = f"<div style='font-family: Arial; padding: 20px; border: 1px solid #ddd; border-radius: 10px;'><h2 style='color: #dc2626;'>Código de Acesso - Achados e Perdidos ETEC</h2><p>Seu código: <strong style='font-size: 24px;'>{codigo}</strong></p><p>Válido por 15 minutos.</p></div>"
        disparar_email(email, "Seu código de acesso - Achados e Perdidos ETEC", html)
        return jsonify({"success": True})
    except Exception as e: 
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/auth/cadastrar', methods=['POST'])
def cadastrar_aluno():
    data = request.json or {}
    email, codigo, nome, rm, senha = data.get('email', '').lower().strip(), data.get('codigo', '').strip(), data.get('nome', '').strip(), data.get('rm', '').strip(), data.get('senha', '').strip()
    try:
        conn = get_db_connection(); cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT codigo, expiracao FROM codigos_auth WHERE email = %s;", (email,))
        reg = cursor.fetchone()
        if not reg or reg['codigo'] != codigo or reg['expiracao'] < datetime.now(): 
            return jsonify({"success": False, "message": "Código inválido ou expirado."}), 400
        
        cursor.execute("SELECT email FROM alunos WHERE email = %s;", (email,))
        if cursor.fetchone(): 
            return jsonify({"success": False, "message": "E-mail já cadastrado. Faça login."}), 400
        
        senha_hash = generate_password_hash(senha)
        cursor.execute("INSERT INTO alunos (email, nome, rm, senha_hash) VALUES (%s, %s, %s, %s);", (email, nome, rm, senha_hash))
        cursor.execute("DELETE FROM codigos_auth WHERE email = %s;", (email,))
        conn.commit(); cursor.close(); conn.close()
        
        token = jwt.encode({"email": email, "nome": nome, "rm": rm, "role": "aluno", "exp": datetime.now(timezone.utc) + timedelta(days=30), "iat": datetime.now(timezone.utc)}, JWT_SECRET, algorithm="HS256")
        return jsonify({"success": True, "token": token, "aluno": {"nome": nome, "rm": rm, "email": email}})
    except Exception as e: 
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/auth/login-aluno', methods=['POST'])
def login_aluno():
    email, senha = request.json.get('email', '').lower().strip(), request.json.get('senha', '').strip()
    try:
        conn = get_db_connection(); cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM alunos WHERE email = %s;", (email,))
        aluno = cursor.fetchone()
        cursor.close(); conn.close()
        if aluno and check_password_hash(aluno['senha_hash'], senha):
            token = jwt.encode({"email": aluno['email'], "nome": aluno['nome'], "rm": aluno['rm'], "role": "aluno", "exp": datetime.now(timezone.utc) + timedelta(days=30), "iat": datetime.now(timezone.utc)}, JWT_SECRET, algorithm="HS256")
            return jsonify({"success": True, "token": token, "aluno": {"nome": aluno['nome'], "rm": aluno['rm'], "email": aluno['email']}})
        return jsonify({"success": False, "message": "Senha incorreta ou usuário não encontrado."}), 401
    except Exception as e: 
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/auth/redefinir', methods=['POST'])
def redefinir_senha():
    email, codigo, nova_senha = request.json.get('email', '').lower().strip(), request.json.get('codigo', '').strip(), request.json.get('senha', '').strip()
    try:
        conn = get_db_connection(); cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT codigo, expiracao FROM codigos_auth WHERE email = %s;", (email,))
        reg = cursor.fetchone()
        if not reg or reg['codigo'] != codigo or reg['expiracao'] < datetime.now(): 
            return jsonify({"success": False, "message": "Código inválido ou expirado."}), 400
        
        senha_hash = generate_password_hash(nova_senha)
        cursor.execute("UPDATE alunos SET senha_hash = %s WHERE email = %s;", (senha_hash, email))
        cursor.execute("DELETE FROM codigos_auth WHERE email = %s;", (email,))
        conn.commit(); cursor.close(); conn.close()
        return jsonify({"success": True})
    except Exception as e: 
        return jsonify({"success": False, "message": str(e)}), 500

# ==========================================
# ROTAS DA SECRETARIA (LOGIN)
# ==========================================
@app.route('/api/login', methods=['POST'])
def login_secretaria():
    dados = request.json or {}
    email = (dados.get('email') or '').strip().lower()
    senha = (dados.get('senha') or '').strip()
    
    login_valido = False

    if email == EMAIL_SECRETARIA and
