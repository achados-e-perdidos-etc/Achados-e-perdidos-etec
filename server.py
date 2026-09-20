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

CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=False)

@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        res = jsonify({"success": True})
        res.headers['Access-Control-Allow-Origin'] = '*'
        res.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        res.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
        res.headers['Access-Control-Max-Age'] = '86400'
        return res, 200

@app.after_request
def after_request(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    return response


DATABASE_URL = os.environ.get("DATABASE_URL")

cloudinary.config( 
  cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME"), 
  api_key = os.environ.get("CLOUDINARY_API_KEY"), 
  api_secret = os.environ.get("CLOUDINARY_API_SECRET"),
  secure = True
)

JWT_SECRET = os.environ.get("JWT_SECRET", "@#Etec_Achad0s_2026_Secret_T0ken!)").strip()
EMAIL_SECRETARIA = os.environ.get("ADMIN_EMAIL", "achadoseperdidosetec@gmail.com").strip().lower()

ADMIN_SENHA = os.environ.get("ADMIN_SENHA", "").strip()
ADMIN_SENHA_HASH = os.environ.get("ADMIN_SENHA_HASH", "").strip()

BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
SMTP_SENDER = os.environ.get("SMTP_SENDER", "achadoseperdidosetec@gmail.com")

# Controle de intervalo para a verificação de 90 dias
ULTIMA_VERIFICACAO_DOACOES = None

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
                token = parts[1].strip('"\'')
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
            return jsonify({"success": False, "message": "Sua sessão expirou. Faça login novamente.", "expired": True}), 401
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
        if not foto: continue
        if foto.startswith('http'): 
            urls_finais.append(foto)
        else:
            try: 
                res_upload = cloudinary.uploader.upload(foto, folder="etec_achados")
                if "secure_url" in res_upload:
                    urls_finais.append(res_upload["secure_url"])
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

def calcular_dias_passados(data_str):
    if not data_str: return 0
    data_limpa = str(data_str).strip()
    formatos = ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d/%m/%y']
    for fmt in formatos:
        try:
            dt = datetime.strptime(data_limpa, fmt)
            return (datetime.now() - dt).days
        except Exception:
            continue
    return 0

# Verificação com controle de intervalo (não sobrecarrega o banco)
def verificar_e_atualizar_itens_doacao(forcar=False):
    global ULTIMA_VERIFICACAO_DOACOES
    agora = datetime.now()
    if not forcar and ULTIMA_VERIFICACAO_DOACOES and (agora - ULTIMA_VERIFICACAO_DOACOES).total_seconds() < 3600:
        return
    ULTIMA_VERIFICACAO_DOACOES = agora

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT id, data_encontrado FROM itens WHERE UPPER(status) = 'DISPONÍVEL';")
        itens = cursor.fetchall()
        ids_para_doacao = []
        for item in itens:
            dias = calcular_dias_passados(item.get('data_encontrado'))
            if dias >= 90:
                ids_para_doacao.append(item['id'])
        
        if ids_para_doacao:
            cursor.execute("UPDATE itens SET status = 'PARA DOAÇÃO' WHERE id = ANY(%s);", (ids_para_doacao,))
            conn.commit()
            print(f"[Doações 90 Dias] {len(ids_para_doacao)} item(ns) atualizado(s) para 'PARA DOAÇÃO'.")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Aviso ao atualizar doações 90 dias: {e}")
        if conn: conn.close()

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS categorias (id SERIAL PRIMARY KEY, nome VARCHAR(50) UNIQUE NOT NULL);')
        cursor.execute('''CREATE TABLE IF NOT EXISTS itens (
            id SERIAL PRIMARY KEY, 
            nome_item VARCHAR(150), 
            descricao TEXT NOT NULL, 
            categoria VARCHAR(50) NOT NULL, 
            data_encontrado VARCHAR(20) NOT NULL, 
            local_encontrado VARCHAR(100) NOT NULL, 
            foto TEXT, 
            fotos_json TEXT, 
            status VARCHAR(30) DEFAULT 'DISPONÍVEL', 
            solicitado_por VARCHAR(100), 
            rm_aluno VARCHAR(20), 
            email_solicitante VARCHAR(150), 
            aprovado BOOLEAN DEFAULT TRUE, 
            cadastrado_por_aluno BOOLEAN DEFAULT FALSE
        );''')

        colunas_migracao = [
            ("nome_item", "VARCHAR(150)"),
            ("foto", "TEXT"),
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
                conn.commit()
            except Exception:
                conn.rollback()

        try:
            cursor.execute("UPDATE itens SET aprovado = TRUE WHERE aprovado IS NULL;")
            conn.commit()
        except Exception:
            conn.rollback()

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
        verificar_e_atualizar_itens_doacao(forcar=True)
    except Exception as e: 
        print(f"Erro DB init: {e}")

if DATABASE_URL: init_db()

@app.route('/controle_etec_7788.html')
@app.route('/secretaria')
@app.route('/admin')
def secretaria_web():
    return send_from_directory(app.static_folder, 'controle_etec_7788.html')

@app.route('/')
def home(): 
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/auth/verificar', methods=['GET', 'OPTIONS'])
@token_required
def verificar_token():
    return jsonify({"success": True, "user": getattr(request, 'user', {})})

@app.route('/api/auth/enviar-codigo', methods=['OPTIONS', 'POST'])
def enviar_codigo():
    email = request.json.get('email', '').strip().lower()
    if not email.endswith('@aluno.cps.sp.gov.br'): 
        return jsonify({"success": False, "message": "Use apenas o e-mail institucional."}), 400
    
    codigo = str(random.randint(100000, 999999))
    expiracao = datetime.now() + timedelta(minutes=15)
    try:
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute("INSERT INTO codigos_auth (email, codigo, expiracao) VALUES (%s, %s, %s) ON CONFLICT (email) DO UPDATE SET codigo = EXCLUDED.codigo, expiracao = EXCLUDED.expiracao;", (email, codigo, expiracao))
        conn.commit(); cursor.close(); conn.close()
        html = f"<div style='font-family: Arial; padding: 20px;'><h2 style='color: #dc2626;'>Código de Acesso - ETEC</h2><p>Seu código: <strong style='font-size: 24px;'>{codigo}</strong></p></div>"
        disparar_email(email, "Seu código de acesso - ETEC", html)
        return jsonify({"success": True})
    except Exception as e: 
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/auth/cadastrar', methods=['OPTIONS', 'POST'])
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
        
        token = jwt.encode({"email": email, "nome": nome, "rm": rm, "role": "aluno", "exp": datetime.now(timezone.utc) + timedelta(days=30)}, JWT_SECRET, algorithm="HS256")
        return jsonify({"success": True, "token": token, "aluno": {"nome": nome, "rm": rm, "email": email}})
    except Exception as e: 
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/auth/login-aluno', methods=['OPTIONS', 'POST'])
def login_aluno():
    email, senha = request.json.get('email', '').lower().strip(), request.json.get('senha', '').strip()
    try:
        conn = get_db_connection(); cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM alunos WHERE email = %s;", (email,))
        aluno = cursor.fetchone()
        cursor.close(); conn.close()
        if aluno and check_password_hash(aluno['senha_hash'], senha):
            token = jwt.encode({"email": aluno['email'], "nome": aluno['nome'], "rm": aluno['rm'], "role": "aluno", "exp": datetime.now(timezone.utc) + timedelta(days=30)}, JWT_SECRET, algorithm="HS256")
            return jsonify({"success": True, "token": token, "aluno": {"nome": aluno['nome'], "rm": aluno['rm'], "email": aluno['email']}})
        return jsonify({"success": False, "message": "Senha incorreta ou usuário não encontrado."}), 401
    except Exception as e: 
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/auth/redefinir', methods=['OPTIONS', 'POST'])
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

@app.route('/api/login', methods=['OPTIONS', 'POST'])
def login_secretaria():
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
            try: login_valido = check_password_hash(ADMIN_SENHA_HASH, senha)
            except: login_valido = (senha == ADMIN_SENHA_HASH)

    if login_valido:
        token = jwt.encode({"user": "secretaria", "role": "secretaria", "email": email, "exp": datetime.now(timezone.utc) + timedelta(days=7)}, JWT_SECRET, algorithm="HS256")
        return jsonify({"success": True, "token": token})
    return jsonify({"success": False, "message": "Credenciais inválidas."}), 401

@app.route('/api/categorias', methods=['OPTIONS', 'GET', 'POST'])
def categorias():
    if request.method == 'GET':
        conn = get_db_connection(); cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM categorias ORDER BY id ASC;")
        res = cursor.fetchall(); cursor.close(); conn.close()
        return jsonify(res)
    else:
        nome = (request.json.get('nome') or '').strip().upper()
        if not nome: return jsonify({"success": False}), 400
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute("INSERT INTO categorias (nome) VALUES (%s) ON CONFLICT DO NOTHING;", (nome,))
        conn.commit(); cursor.close(); conn.close()
        return jsonify({"success": True})

@app.route('/api/itens', methods=['OPTIONS', 'GET'])
def get_itens():
    conn = None
    try:
        verificar_e_atualizar_itens_doacao()
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cursor.execute("""
                SELECT id, 
                       COALESCE(nome_item, descricao) as nome, 
                       descricao as txt_descricao, 
                       categoria, 
                       data_encontrado as txt_data, 
                       local_encontrado as txt_local, 
                       foto, fotos_json, status, solicitado_por, rm_aluno, 
                       COALESCE(aprovado, TRUE) as aprovado, 
                       COALESCE(cadastrado_por_aluno, FALSE) as cadastrado_por_aluno 
                FROM itens 
                WHERE (aprovado IS NULL OR aprovado = TRUE)
                ORDER BY id DESC;
            """)
            itens = cursor.fetchall()
        except Exception as q_err:
            conn.rollback()
            cursor.execute("""
                SELECT id, 
                       COALESCE(nome_item, descricao) as nome, 
                       descricao as txt_descricao, 
                       categoria, 
                       data_encontrado as txt_data, 
                       local_encontrado as txt_local, 
                       foto, status, solicitado_por, rm_aluno 
                FROM itens 
                ORDER BY id DESC;
            """)
            itens = cursor.fetchall()

        for item in itens:
            try: 
                item['fotos'] = json.loads(item['fotos_json']) if item.get('fotos_json') else ([] if not item.get('foto') else [item['foto']])
            except: 
                item['fotos'] = [item['foto']] if item.get('foto') else []
            if 'aprovado' not in item:
                item['aprovado'] = True
            if 'cadastrado_por_aluno' not in item:
                item['cadastrado_por_aluno'] = False
        cursor.close()
        conn.close()
        return jsonify(itens)
    except Exception as e: 
        if conn: conn.close()
        print(f"Erro em get_itens: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/itens/pendentes', methods=['OPTIONS', 'GET'])
@token_required
def get_itens_pendentes():
    try:
        conn = get_db_connection(); cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT id, nome_item as nome, descricao as txt_descricao, categoria, data_encontrado as txt_data, local_encontrado as txt_local, foto, fotos_json, status, rm_aluno FROM itens WHERE aprovado = FALSE ORDER BY id DESC;")
        itens = cursor.fetchall()
        for item in itens:
            try: 
                item['fotos'] = json.loads(item['fotos_json']) if item.get('fotos_json') else ([] if not item.get('foto') else [item['foto']])
            except: 
                item['fotos'] = []
        cursor.close(); conn.close()
        return jsonify(itens)
    except Exception as e: 
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/itens/cadastrar-aluno', methods=['OPTIONS', 'POST'])
def cadastrar_item_aluno():
    data = request.json or {}
    nome = (data.get('nome') or '').strip()
    descricao = (data.get('descricao') or '').strip()
    categoria = (data.get('categoria') or 'OUTROS').strip()
    data_enc = (data.get('data') or datetime.now().strftime("%d/%m/%Y")).strip()
    local = (data.get('local') or 'Não informado').strip()
    rm = (data.get('rm') or '').strip()
    
    lista_entrada = data.get('fotos', [])
    if not lista_entrada and data.get('foto'):
        lista_entrada = [data.get('foto')]

    urls_nuvem = processar_fotos(lista_entrada)
    foto_capa = urls_nuvem[0] if urls_nuvem else ''
    fotos_json_str = json.dumps(urls_nuvem)

    try:
        conn = get_db_connection(); cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('''INSERT INTO itens (nome_item, descricao, categoria, data_encontrado, local_encontrado, foto, fotos_json, status, aprovado, cadastrado_por_aluno, rm_aluno) VALUES (%s, %s, %s, %s, %s, %s, %s, 'DISPONÍVEL', FALSE, TRUE, %s) RETURNING id;''', (nome, descricao, categoria, data_enc, local, foto_capa, fotos_json_str, rm))
        conn.commit(); cursor.close(); conn.close()
        return jsonify({"success": True, "message": "Item enviado para moderação!"})
    except Exception as e: 
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/itens/<int:item_id>/aprovar', methods=['OPTIONS', 'PUT'])
@token_required
def aprovar_item(item_id):
    try:
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute("UPDATE itens SET aprovado = TRUE WHERE id = %s;", (item_id,))
        conn.commit(); cursor.close(); conn.close()
        return jsonify({"success": True, "message": "Item aprovado com sucesso!"})
    except Exception as e: 
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/itens', methods=['OPTIONS', 'POST'])
@token_required
def cadastrar_item():
    data = request.json or {}
    nome = (data.get('nome') or '').strip()
    descricao = (data.get('descricao') or '').strip()
    categoria = (data.get('categoria') or 'OUTROS').strip()
    data_enc = (data.get('data') or datetime.now().strftime("%d/%m/%Y")).strip()
    local = (data.get('local') or 'Não informado').strip()
    status = (data.get('status') or 'DISPONÍVEL').strip()

    if not descricao:
        return jsonify({"success": False, "error": "A descrição é obrigatória."}), 400

    lista_entrada = data.get('fotos', [])
    if not lista_entrada and data.get('foto'):
        lista_entrada = [data.get('foto')]

    urls_nuvem = processar_fotos(lista_entrada)
    foto_capa = urls_nuvem[0] if urls_nuvem else ''
    fotos_json_str = json.dumps(urls_nuvem)

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('''
            INSERT INTO itens (
                nome_item, descricao, categoria, data_encontrado, 
                local_encontrado, foto, fotos_json, status, aprovado
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE) 
            RETURNING id;
        ''', (nome, descricao, categoria, data_enc, local, foto_capa, fotos_json_str, status))
        
        row = cursor.fetchone()
        novo_id = row['id'] if isinstance(row, dict) else row[0]
        conn.commit()

        try:
            termos_novo = extrair_termos(f"{nome} {descricao}")
            cursor.execute("SELECT * FROM mural_perdidos WHERE status = 'PROCURANDO' AND categoria = %s;", (categoria,))
            for mural in cursor.fetchall():
                termos_mural = extrair_termos(mural.get('descricao', ''))
                if len(termos_novo.intersection(termos_mural)) >= 1:
                    msg_match = f"A secretaria registrou um objeto parecido: '{nome or descricao}'. Veja o catálogo!"
                    cursor.execute(
                        "INSERT INTO mensagens_chat (rm_aluno, nome_aluno, remetente, mensagem, data_envio) VALUES (%s, %s, %s, %s, %s);", 
                        (mural['rm_aluno'], mural['nome_aluno'], 'SECRETARIA', msg_match, datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
                    )
                    if mural.get('email_aluno'):
                        disparar_email(
                            mural['email_aluno'], 
                            "Item Encontrado! ETEC Achados", 
                            f"<div style='font-family:Arial;'><h2 style='color:#dc2626;'>Possível Match!</h2><p>Olá {mural['nome_aluno']}, a secretaria registrou um item parecido: <strong>{nome or descricao}</strong>.</p></div>"
                        )
            conn.commit()
        except Exception:
            if conn: conn.rollback()

        cursor.close()
        conn.close()
        return jsonify({"success": True, "id": novo_id, "message": "Item salvo com sucesso!"})
    except Exception as e: 
        if conn: conn.rollback(); conn.close()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/itens/<int:item_id>', methods=['OPTIONS', 'PUT', 'DELETE'])
@token_required
def gerenciar_item(item_id):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        if request.method == 'DELETE':
            cursor.execute("DELETE FROM entregues WHERE item_id = %s;", (item_id,))
            cursor.execute("DELETE FROM itens WHERE id = %s;", (item_id,))
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({"success": True, "message": "Item excluído com sucesso."})
        else:
            data = request.json or {}
            cursor.execute("SELECT * FROM itens WHERE id = %s;", (item_id,))
            item_atual = cursor.fetchone()
            if not item_atual:
                cursor.close(); conn.close()
                return jsonify({"success": False, "message": "Item não encontrado."}), 404

            nome = data.get('nome') if ('nome' in data and data.get('nome') is not None) else item_atual.get('nome_item', '')
            descricao = data.get('descricao') if ('descricao' in data and data.get('descricao') is not None) else item_atual.get('descricao', '')
            categoria = data.get('categoria') if ('categoria' in data and data.get('categoria') is not None) else item_atual.get('categoria', 'OUTROS')
            data_enc = data.get('data') if ('data' in data and data.get('data') is not None) else item_atual.get('data_encontrado', '')
            local = data.get('local') if ('local' in data and data.get('local') is not None) else item_atual.get('local_encontrado', '')
            status = data.get('status') if ('status' in data and data.get('status') is not None) else item_atual.get('status', 'DISPONÍVEL')

            nome = (str(nome) or '').strip()
            descricao = (str(descricao) or '').strip()
            categoria = (str(categoria) or 'OUTROS').strip()
            data_enc = (str(data_enc) or '').strip()
            local = (str(local) or '').strip()
            status = (str(status) or 'DISPONÍVEL').strip()

            if not descricao:
                descricao = nome or 'Objeto'

            if 'fotos' in data and data.get('fotos') is not None:
                fotos_rec = data.get('fotos') or []
                urls = processar_fotos(fotos_rec)
                foto_capa = urls[0] if urls else (item_atual.get('foto') or '')
                fotos_json_str = json.dumps(urls) if urls else (item_atual.get('fotos_json') or '[]')
                cursor.execute("""
                    UPDATE itens 
                    SET nome_item=%s, descricao=%s, categoria=%s, data_encontrado=%s, 
                        local_encontrado=%s, foto=%s, fotos_json=%s, status=%s, aprovado=TRUE 
                    WHERE id=%s;
                """, (nome, descricao, categoria, data_enc, local, foto_capa, fotos_json_str, status, item_id))
            else:
                cursor.execute("""
                    UPDATE itens 
                    SET nome_item=%s, descricao=%s, categoria=%s, data_encontrado=%s, 
                        local_encontrado=%s, status=%s, aprovado=TRUE 
                    WHERE id=%s;
                """, (nome, descricao, categoria, data_enc, local, status, item_id))

            if status.upper() == 'ENTREGUE':
                cursor.execute("DELETE FROM entregues WHERE item_id = %s;", (item_id,))
                cursor.execute("""
                    INSERT INTO entregues (
                        item_id, nome_item, retirado_por, rm_retirante, turma_curso, 
                        data_entrega, funcionario_responsavel
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s);
                """, (
                    item_id, nome or descricao, 
                    data.get('retirado_por', item_atual.get('solicitado_por', '')), 
                    data.get('rm_retirante', item_atual.get('rm_aluno', '')), 
                    data.get('turma_curso', '-'), 
                    data.get('data_entrega', datetime.now().strftime("%d/%m/%Y %H:%M")), 
                    data.get('funcionario_responsavel', 'Secretaria')
                ))

            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({"success": True, "message": "Item atualizado com sucesso!"})
    except Exception as e:
        if conn: conn.rollback(); conn.close()
        print(f"Erro em gerenciar_item: {e}")
        return jsonify({"success": False, "error": str(e), "message": f"Erro interno ao atualizar item: {str(e)}"}), 500


@app.route('/api/itens/<int:item_id>/recusar', methods=['OPTIONS', 'PUT'])
@token_required
def recusar_solicitacao(item_id):
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("UPDATE itens SET status = 'DISPONÍVEL', solicitado_por = NULL, rm_aluno = NULL, email_solicitante = NULL WHERE id = %s;", (item_id,))
    conn.commit(); cursor.close(); conn.close()
    return jsonify({"success": True})

@app.route('/api/itens/doacoes/concluir', methods=['OPTIONS', 'DELETE'])
@token_required
def concluir_doacoes():
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("DELETE FROM itens WHERE UPPER(status) = 'DOAÇÃO FEITA' OR UPPER(status) = 'DOACAO FEITA';")
    conn.commit(); cursor.close(); conn.close()
    return jsonify({"success": True})

@app.route('/api/mural', methods=['OPTIONS', 'GET', 'POST'])
def mural():
    if request.method == 'GET':
        conn = get_db_connection(); cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM mural_perdidos ORDER BY id DESC;")
        res = cursor.fetchall(); cursor.close(); conn.close()
        return jsonify(res)
    else:
        data = request.json or {}
        nome, rm, email_aluno, categoria, descricao = data.get('nome'), data.get('rm'), data.get('email'), data.get('categoria'), data.get('descricao')
        conn = get_db_connection(); cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("INSERT INTO mural_perdidos (nome_aluno, rm_aluno, email_aluno, categoria, descricao, data_registro, status) VALUES (%s, %s, %s, %s, %s, %s, 'PROCURANDO') RETURNING id;", (nome, rm, email_aluno, categoria, descricao, datetime.now().strftime("%d/%m/%Y %H:%M")))
        
        matches = []
        try:
            termos_relato = extrair_termos(descricao or "")
            cursor.execute("SELECT id, nome_item as nome, descricao as txt_descricao, categoria, foto, fotos_json FROM itens WHERE aprovado = TRUE AND status = 'DISPONÍVEL' AND categoria = %s;", (categoria,))
            for item in cursor.fetchall():
                try: 
                    item['fotos'] = json.loads(item['fotos_json']) if item.get('fotos_json') else ([] if not item.get('foto') else [item['foto']])
                except: 
                    item['fotos'] = []
                termos_item = extrair_termos((item.get('nome') or "") + " " + (item.get('txt_descricao') or ""))
                if len(termos_relato.intersection(termos_item)) >= 1:
                    matches.append(item)
        except Exception as e:
            print("Erro ao checar matches:", e)
            
        conn.commit(); cursor.close(); conn.close()
        return jsonify({"success": True, "matches_encontrados": matches})

@app.route('/api/mural/aluno/<string:rm>', methods=['OPTIONS', 'GET'])
def mural_aluno(rm):
    try:
        conn = get_db_connection(); cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT id, categoria, descricao, data_registro as data, status FROM mural_perdidos WHERE rm_aluno = %s ORDER BY id DESC;", (rm,))
        res = cursor.fetchall(); cursor.close(); conn.close()
        return jsonify(res)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/mural/<int:id>', methods=['OPTIONS', 'DELETE'])
@token_required
def deletar_mural(id):
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("DELETE FROM mural_perdidos WHERE id = %s;", (id,))
    conn.commit(); cursor.close(); conn.close()
    return jsonify({"success": True})

@app.route('/api/solicitar', methods=['OPTIONS', 'POST'])
def solicitar_item():
    data = request.json or {}
    item_id, nome, rm, email_aluno = data.get('id'), data.get('nome'), data.get('rm'), data.get('email')
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("UPDATE itens SET status = 'SOLICITADO', solicitado_por = %s, rm_aluno = %s, email_solicitante = %s WHERE id = %s AND status = 'DISPONÍVEL';", (nome, rm, email_aluno, item_id))
    afetados = cursor.rowcount
    conn.commit(); cursor.close(); conn.close()
    if afetados > 0: 
        return jsonify({"success": True, "message": "Solicitação enviada com sucesso!"})
    return jsonify({"success": False, "message": "Este item não está mais disponível."}), 400

@app.route('/api/chat/enviar', methods=['OPTIONS', 'POST'])
def enviar_chat():
    data = request.json or {}
    rm, nome, remetente, mensagem = str(data.get('rm', '')).strip(), data.get('nome', 'Anônimo').strip(), data.get('remetente', 'ALUNO').upper().strip(), data.get('mensagem', '').strip()
    if not rm or not mensagem: return jsonify({"success": False}), 400
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("INSERT INTO mensagens_chat (rm_aluno, nome_aluno, remetente, mensagem, data_envio) VALUES (%s, %s, %s, %s, %s);", (rm, nome, remetente, mensagem, datetime.now().strftime("%d/%m/%Y %H:%M:%S")))
    conn.commit(); cursor.close(); conn.close()
    return jsonify({"success": True})

@app.route('/api/chat/mensagens/<string:rm>', methods=['OPTIONS', 'GET'])
def buscar_mensagens(rm):
    conn = get_db_connection(); cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM mensagens_chat WHERE rm_aluno = %s ORDER BY id ASC;", (rm,))
    msgs = cursor.fetchall()
    if request.args.get('marcar_lida', 'false').lower() == 'true' and msgs:
        outro = 'SECRETARIA' if request.args.get('origem', 'ALUNO').upper() == 'ALUNO' else 'ALUNO'
        cursor.execute("UPDATE mensagens_chat SET lida = TRUE WHERE rm_aluno = %s AND remetente = %s AND lida = FALSE;", (rm, outro))
        conn.commit()
    cursor.close(); conn.close()
    return jsonify(msgs)

@app.route('/api/chat/conversas', methods=['OPTIONS', 'GET'])
@token_required
def listar_conversas():
    conn = get_db_connection(); cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT rm_aluno, MAX(nome_aluno) as nome_aluno, MAX(data_envio) as ultima_msg_data, COUNT(CASE WHEN remetente = 'ALUNO' AND lida = FALSE THEN 1 END) as nao_lidas FROM mensagens_chat GROUP BY rm_aluno ORDER BY MAX(id) DESC;")
    res = cursor.fetchall(); cursor.close(); conn.close()
    return jsonify(res)

@app.route('/api/entregues', methods=['OPTIONS', 'GET'])
@token_required
def get_entregues():
    conn = get_db_connection(); cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM entregues ORDER BY id DESC;")
    res = cursor.fetchall(); cursor.close(); conn.close()
    return jsonify(res)

@app.route('/api/estatisticas', methods=['OPTIONS', 'GET'])
@token_required
def estatisticas():
    verificar_e_atualizar_itens_doacao()
    conn = get_db_connection(); cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT COUNT(*) as total FROM itens WHERE aprovado = TRUE;")
    total = cursor.fetchone()['total']
    cursor.execute("SELECT COUNT(*) as total FROM entregues;")
    entregues = cursor.fetchone()['total']
    cursor.execute("SELECT COUNT(*) as total FROM itens WHERE status LIKE 'DOAÇÃO%' AND aprovado = TRUE;")
    doacoes = cursor.fetchone()['total']
    cursor.close(); conn.close()
    return jsonify({"success": True, "total_itens": total, "total_entregues": entregues, "total_doacoes": doacoes})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
