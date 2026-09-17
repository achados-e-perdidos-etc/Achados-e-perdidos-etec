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
from datetime import datetime, timedelta
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import cloudinary
import cloudinary.uploader
import jwt

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, static_folder=BASE_DIR, static_url_path='')

ORIGENS_PERMITIDAS = ["https://etec-achados.up.railway.app", "http://localhost:5000", "http://127.0.0.1:5000"]
CORS(app, resources={r"/api/*": {"origins": ORIGENS_PERMITIDAS}})

DATABASE_URL = os.environ.get("DATABASE_URL")

cloudinary.config( 
  cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME"), 
  api_key = os.environ.get("CLOUDINARY_API_KEY"), 
  api_secret = os.environ.get("CLOUDINARY_API_SECRET"),
  secure = True
)

JWT_SECRET = os.environ.get("JWT_SECRET", "chave_fallback_local_temporaria_apenas")
EMAIL_SECRETARIA = os.environ.get("ADMIN_EMAIL", "secretaria@etec.sp.gov.br")
SENHA_SECRETARIA_HASH = os.environ.get("ADMIN_SENHA_HASH", "pbkdf2:sha256:600000$dummy$hash")

BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
SMTP_SENDER = os.environ.get("SMTP_SENDER", "secretaria@etec.sp.gov.br")

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            parts = request.headers['Authorization'].split()
            if len(parts) == 2 and parts[0] == 'Bearer': token = parts[1]
        if not token: return jsonify({"success": False, "message": "Acesso negado: Token ausente."}), 401
        try: jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        except: return jsonify({"success": False, "message": "Acesso negado: Token inválido ou expirado."}), 401
        return f(*args, **kwargs)
    return decorated

def get_db_connection(): return psycopg2.connect(DATABASE_URL, sslmode='require')

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
        if foto.startswith('http'): urls_finais.append(foto)
        else:
            try: urls_finais.append(cloudinary.uploader.upload(foto, folder="etec_achados")["secure_url"])
            except Exception as e: print(f"Erro Cloudinary: {e}")
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
        if cursor.execute("SELECT COUNT(*) FROM categorias;") or cursor.fetchone()[0] == 0:
            for c in ['MOCHILA', 'ROUPAS', 'ACESSÓRIOS', 'ESCOLARES', 'ELETRÔNICOS', 'OUTROS']:
                cursor.execute("INSERT INTO categorias (nome) VALUES (%s) ON CONFLICT DO NOTHING;", (c,))
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS itens (
            id SERIAL PRIMARY KEY, nome_item VARCHAR(150), descricao TEXT NOT NULL, categoria VARCHAR(50) NOT NULL, 
            data_encontrado VARCHAR(20) NOT NULL, local_encontrado VARCHAR(100) NOT NULL, foto_base64 TEXT, 
            fotos_json TEXT, status VARCHAR(30) DEFAULT 'DISPONÍVEL', solicitado_por VARCHAR(100), rm_aluno VARCHAR(20), 
            email_solicitante VARCHAR(150), aprovado BOOLEAN DEFAULT TRUE, cadastrado_por_aluno BOOLEAN DEFAULT FALSE
        );''')
        
        # Garantir colunas novas se a tabela já existia
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='itens' AND column_name='aprovado';")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE itens ADD COLUMN aprovado BOOLEAN DEFAULT TRUE, ADD COLUMN cadastrado_por_aluno BOOLEAN DEFAULT FALSE;")

        cursor.execute('''CREATE TABLE IF NOT EXISTS entregues (id SERIAL PRIMARY KEY, item_id INT NOT NULL, nome_item TEXT NOT NULL, retirado_por VARCHAR(100) NOT NULL, rm_retirante VARCHAR(30) NOT NULL, turma_curso VARCHAR(50), data_entrega VARCHAR(30) NOT NULL, funcionario_responsavel VARCHAR(100));''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS mural_perdidos (id SERIAL PRIMARY KEY, nome_aluno VARCHAR(100) NOT NULL, rm_aluno VARCHAR(20) NOT NULL, email_aluno VARCHAR(150), categoria VARCHAR(50) NOT NULL, descricao TEXT NOT NULL, data_registro VARCHAR(30) NOT NULL, status VARCHAR(30) DEFAULT 'PROCURANDO');''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS mensagens_chat (id SERIAL PRIMARY KEY, rm_aluno VARCHAR(20) NOT NULL, nome_aluno VARCHAR(100) NOT NULL, remetente VARCHAR(20) NOT NULL, mensagem TEXT NOT NULL, data_envio VARCHAR(30) NOT NULL, lida BOOLEAN DEFAULT FALSE);''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS alunos (email VARCHAR(150) PRIMARY KEY, nome VARCHAR(100) NOT NULL, rm VARCHAR(20) NOT NULL, senha_hash TEXT NOT NULL);''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS codigos_auth (email VARCHAR(150) PRIMARY KEY, codigo VARCHAR(6) NOT NULL, expiracao TIMESTAMP NOT NULL);''')
        
        # Tabela para Push Notifications
        cursor.execute('''CREATE TABLE IF NOT EXISTS push_subscriptions (id SERIAL PRIMARY KEY, rm_aluno VARCHAR(20) UNIQUE NOT NULL, subscription_json TEXT NOT NULL);''')

        conn.commit(); cursor.close(); conn.close()
    except Exception as e: print(f"Erro DB: {e}")

if DATABASE_URL: init_db()

@app.route('/')
def home(): return send_from_directory(app.static_folder, 'index.html')

# ==========================================
# ROTAS DE AUTENTICAÇÃO DO ALUNO
# ==========================================
@app.route('/api/auth/enviar-codigo', methods=['POST'])
def enviar_codigo():
    email = request.json.get('email', '').strip().lower()
    if not email.endswith('@aluno.cps.sp.gov.br'): return jsonify({"success": False, "message": "Use apenas o e-mail institucional (@aluno.cps.sp.gov.br)."}), 400
    
    codigo = str(random.randint(100000, 999999))
    expiracao = datetime.now() + timedelta(minutes=15)
    try:
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute("INSERT INTO codigos_auth (email, codigo, expiracao) VALUES (%s, %s, %s) ON CONFLICT (email) DO UPDATE SET codigo = EXCLUDED.codigo, expiracao = EXCLUDED.expiracao;", (email, codigo, expiracao))
        conn.commit(); cursor.close(); conn.close()
        html = f"<div style='font-family: Arial; padding: 20px; border: 1px solid #ddd; border-radius: 10px;'><h2 style='color: #dc2626;'>Código de Acesso - Achados e Perdidos ETEC</h2><p>Seu código de segurança é: <strong style='font-size: 24px; color: #000;'>{codigo}</strong></p><p>Válido por 15 minutos.</p></div>"
        disparar_email(email, "Seu código de acesso - Achados e Perdidos ETEC", html)
        return jsonify({"success": True})
    except Exception as e: return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/auth/cadastrar', methods=['POST'])
def cadastrar_aluno():
    data = request.json or {}
    email, codigo, nome, rm, senha = data.get('email', '').lower(), data.get('codigo'), data.get('nome'), data.get('rm'), data.get('senha')
    try:
        conn = get_db_connection(); cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT codigo, expiracao FROM codigos_auth WHERE email = %s;", (email,))
        reg = cursor.fetchone()
        if not reg or reg['codigo'] != codigo or reg['expiracao'] < datetime.now(): return jsonify({"success": False, "message": "Código inválido ou expirado."}), 400
        
        cursor.execute("SELECT email FROM alunos WHERE email = %s;", (email,))
        if cursor.fetchone(): return jsonify({"success": False, "message": "E-mail já cadastrado. Faça login."}), 400
        
        senha_hash = generate_password_hash(senha)
        cursor.execute("INSERT INTO alunos (email, nome, rm, senha_hash) VALUES (%s, %s, %s, %s);", (email, nome, rm, senha_hash))
        cursor.execute("DELETE FROM codigos_auth WHERE email = %s;", (email,))
        conn.commit(); cursor.close(); conn.close()
        
        token = jwt.encode({"email": email, "nome": nome, "rm": rm, "exp": datetime.utcnow() + timedelta(days=30)}, JWT_SECRET, algorithm="HS256")
        return jsonify({"success": True, "token": token, "aluno": {"nome": nome, "rm": rm, "email": email}})
    except Exception as e: return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/auth/login-aluno', methods=['POST'])
def login_aluno():
    email, senha = request.json.get('email', '').lower(), request.json.get('senha', '')
    try:
        conn = get_db_connection(); cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM alunos WHERE email = %s;", (email,))
        aluno = cursor.fetchone()
        cursor.close(); conn.close()
        if aluno and check_password_hash(aluno['senha_hash'], senha):
            token = jwt.encode({"email": aluno['email'], "nome": aluno['nome'], "rm": aluno['rm'], "exp": datetime.utcnow() + timedelta(days=30)}, JWT_SECRET, algorithm="HS256")
            return jsonify({"success": True, "token": token, "aluno": {"nome": aluno['nome'], "rm": aluno['rm'], "email": aluno['email']}})
        return jsonify({"success": False, "message": "Senha incorreta ou usuário não encontrado."}), 401
    except Exception as e: return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/auth/redefinir', methods=['POST'])
def redefinir_senha():
    email, codigo, nova_senha = request.json.get('email', '').lower(), request.json.get('codigo'), request.json.get('senha')
    try:
        conn = get_db_connection(); cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT codigo, expiracao FROM codigos_auth WHERE email = %s;", (email,))
        reg = cursor.fetchone()
        if not reg or reg['codigo'] != codigo or reg['expiracao'] < datetime.now(): return jsonify({"success": False, "message": "Código inválido/expirado."}), 400
        
        senha_hash = generate_password_hash(nova_senha)
        cursor.execute("UPDATE alunos SET senha_hash = %s WHERE email = %s;", (senha_hash, email))
        if cursor.rowcount == 0: return jsonify({"success": False, "message": "Conta não encontrada."}), 404
        cursor.execute("DELETE FROM codigos_auth WHERE email = %s;", (email,))
        conn.commit(); cursor.close(); conn.close()
        return jsonify({"success": True})
    except Exception as e: return jsonify({"success": False, "message": str(e)}), 500

# ==========================================
# ROTAS DO SISTEMA
# ==========================================
@app.route('/api/login', methods=['POST'])
def login_secretaria():
    email, senha = request.json.get('email', '').strip().lower(), request.json.get('senha', '').strip()
    if email == EMAIL_SECRETARIA and check_password_hash(SENHA_SECRETARIA_HASH, senha):
        token = jwt.encode({"user": "secretaria", "exp": datetime.utcnow() + timedelta(hours=4)}, JWT_SECRET, algorithm="HS256")
        return jsonify({"success": True, "token": token})
    return jsonify({"success": False, "message": "Credenciais inválidas"}), 401

@app.route('/api/categorias', methods=['GET', 'POST'])
def categorias():
    if request.method == 'GET':
        conn = get_db_connection(); cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM categorias ORDER BY id ASC;")
        res = cursor.fetchall(); cursor.close(); conn.close()
        return jsonify(res)
    else:
        nome = (request.json.get('nome') or '').strip().upper()
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute("INSERT INTO categorias (nome) VALUES (%s) ON CONFLICT DO NOTHING;", (nome,))
        conn.commit(); cursor.close(); conn.close()
        return jsonify({"success": True})

@app.route('/api/itens', methods=['GET'])
def get_itens():
    try:
        conn = get_db_connection(); cursor = conn.cursor(cursor_factory=RealDictCursor)
        # Retorna apenas itens aprovados para o catálogo geral
        cursor.execute("SELECT id, nome_item as nome, descricao as txt_descricao, categoria, data_encontrado as txt_data, local_encontrado as txt_local, foto_base64 as foto, fotos_json, status, solicitado_por, rm_aluno, aprovado, cadastrado_por_aluno FROM itens WHERE aprovado = TRUE ORDER BY id DESC;")
        itens = cursor.fetchall()
        for item in itens:
            try: item['fotos'] = json.loads(item['fotos_json']) if item.get('fotos_json') else ([] if not item.get('foto') else [item['foto']])
            except: item['fotos'] = []
        cursor.close(); conn.close()
        return jsonify(itens)
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/itens/pendentes', methods=['GET'])
@token_required
def get_itens_pendentes():
    try:
        conn = get_db_connection(); cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT id, nome_item as nome, descricao as txt_descricao, categoria, data_encontrado as txt_data, local_encontrado as txt_local, foto_base64 as foto, fotos_json, status, rm_aluno FROM itens WHERE aprovado = FALSE ORDER BY id DESC;")
        itens = cursor.fetchall()
        for item in itens:
            try: item['fotos'] = json.loads(item['fotos_json']) if item.get('fotos_json') else ([] if not item.get('foto') else [item['foto']])
            except: item['fotos'] = []
        cursor.close(); conn.close()
        return jsonify(itens)
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/itens/cadastrar-aluno', methods=['POST'])
def cadastrar_item_aluno():
    data = request.json or {}
    nome, descricao, categoria = data.get('nome'), data.get('descricao'), data.get('categoria')
    data_enc, local, rm = data.get('data'), data.get('local'), data.get('rm')
    urls_nuvem = processar_fotos(data.get('fotos', []))
    try:
        conn = get_db_connection(); cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('''INSERT INTO itens (nome_item, descricao, categoria, data_encontrado, local_encontrado, foto_base64, fotos_json, status, aprovado, cadastrado_por_aluno, rm_aluno) VALUES (%s, %s, %s, %s, %s, %s, %s, 'DISPONÍVEL', FALSE, TRUE, %s) RETURNING id;''', (nome, descricao, categoria, data_enc, local, urls_nuvem[0] if urls_nuvem else '', json.dumps(urls_nuvem), rm))
        conn.commit(); cursor.close(); conn.close()
        return jsonify({"success": True, "message": "Item enviado para moderação da secretaria!"})
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/itens/<int:item_id>/aprovar', methods=['PUT'])
@token_required
def aprovar_item(item_id):
    try:
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute("UPDATE itens SET aprovado = TRUE WHERE id = %s;", (item_id,))
        conn.commit(); cursor.close(); conn.close()
        return jsonify({"success": True})
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/itens', methods=['POST'])
@token_required
def cadastrar_item():
    data = request.json or {}
    nome, descricao, categoria, data_enc, local, status = data.get('nome'), data.get('descricao'), data.get('categoria'), data.get('data'), data.get('local'), data.get('status', 'DISPONÍVEL')
    urls_nuvem = processar_fotos(data.get('fotos', []))
    try:
        conn = get_db_connection(); cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('''INSERT INTO itens (nome_item, descricao, categoria, data_encontrado, local_encontrado, foto_base64, fotos_json, status, aprovado) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE) RETURNING id;''', (nome, descricao, categoria, data_enc, local, urls_nuvem[0] if urls_nuvem else '', json.dumps(urls_nuvem), status))
        novo_id = cursor.fetchone()['id']
        
        try:
            termos_novo = extrair_termos((nome or "") + " " + (descricao or ""))
            cursor.execute("SELECT * FROM mural_perdidos WHERE status = 'PROCURANDO' AND categoria = %s;", (categoria,))
            for mural in cursor.fetchall():
                if len(termos_novo.intersection(extrair_termos(mural['descricao']))) >= 1:
                    cursor.execute("INSERT INTO mensagens_chat (rm_aluno, nome_aluno, remetente, mensagem, data_envio) VALUES (%s, %s, %s, %s, %s);", (mural['rm_aluno'], mural['nome_aluno'], 'SECRETARIA', f"A secretaria registrou um objeto parecido com: '{nome}'. Veja o catálogo!", datetime.now().strftime("%d/%m/%Y %H:%M:%S")))
                    if mural.get('email_aluno'):
                        disparar_email(mural['email_aluno'], "Item Encontrado! ETEC Achados", f"<div style='font-family:Arial;'><h2 style='color:#dc2626;'>Possível Match!</h2><p>Olá {mural['nome_aluno']}, a secretaria registrou um item que bate com o seu relato: <strong>{nome}</strong>. Acesse o site para conferir.</p></div>")
        except: pass
        conn.commit(); cursor.close(); conn.close()
        return jsonify({"success": True, "id": novo_id})
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/itens/<int:item_id>', methods=['PUT', 'DELETE'])
@token_required
def gerenciar_item(item_id):
    conn = get_db_connection(); cursor = conn.cursor(cursor_factory=RealDictCursor)
    if request.method == 'DELETE':
        cursor.execute("DELETE FROM entregues WHERE item_id = %s;", (item_id,))
        cursor.execute("DELETE FROM itens WHERE id = %s;", (item_id,))
    else:
        data = request.json or {}
        nome, descricao, categoria, data_enc, local, status = data.get('nome'), data.get('descricao'), data.get('categoria'), data.get('data'), data.get('local'), data.get('status', 'DISPONÍVEL')
        if descricao and data_enc and local:
            fotos_rec = data.get('fotos')
            if fotos_rec:
                urls = processar_fotos(fotos_rec)
                cursor.execute("UPDATE itens SET nome_item=%s, descricao=%s, categoria=%s, data_encontrado=%s, local_encontrado=%s, foto_base64=%s, fotos_json=%s, status=%s WHERE id=%s;", (nome, descricao, categoria, data_enc, local, urls[0], json.dumps(urls), status, item_id))
            else: cursor.execute("UPDATE itens SET nome_item=%s, descricao=%s, categoria=%s, data_encontrado=%s, local_encontrado=%s, status=%s WHERE id=%s;", (nome, descricao, categoria, data_enc, local, status, item_id))
        else: cursor.execute("UPDATE itens SET status=%s WHERE id=%s;", (status, item_id))
        
        if status.upper() == 'ENTREGUE':
            cursor.execute("DELETE FROM entregues WHERE item_id = %s;", (item_id,))
            cursor.execute("INSERT INTO entregues (item_id, nome_item, retirado_por, rm_retirante, turma_curso, data_entrega, funcionario_responsavel) VALUES (%s, %s, %s, %s, %s, %s, %s);", (item_id, nome or descricao, data.get('retirado_por', ''), data.get('rm_retirante', ''), data.get('turma_curso', '-'), data.get('data_entrega', data_enc), data.get('funcionario_responsavel', 'Secretaria')))
    conn.commit(); cursor.close(); conn.close()
    return jsonify({"success": True})

@app.route('/api/itens/<int:item_id>/recusar', methods=['PUT'])
@token_required
def recusar_solicitacao(item_id):
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("UPDATE itens SET status = 'DISPONÍVEL', solicitado_por = NULL, rm_aluno = NULL, email_solicitante = NULL WHERE id = %s;", (item_id,))
    conn.commit(); cursor.close(); conn.close()
    return jsonify({"success": True})

@app.route('/api/itens/doacoes/concluir', methods=['DELETE'])
@token_required
def concluir_doacoes():
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("DELETE FROM itens WHERE UPPER(status) = 'DOAÇÃO FEITA' OR UPPER(status) = 'DOACAO FEITA';")
    conn.commit(); cursor.close(); conn.close()
    return jsonify({"success": True})

@app.route('/api/mural', methods=['GET', 'POST'])
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
        conn.commit(); cursor.close(); conn.close()
        return jsonify({"success": True})

@app.route('/api/mural/<int:id>', methods=['DELETE'])
@token_required
def deletar_mural(id):
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("DELETE FROM mural_perdidos WHERE id = %s;", (id,))
    conn.commit(); cursor.close(); conn.close()
    return jsonify({"success": True})

@app.route('/api/solicitar', methods=['POST'])
def solicitar_item():
    data = request.json or {}
    item_id, nome, rm, email_aluno = data.get('id'), data.get('nome'), data.get('rm'), data.get('email')
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("UPDATE itens SET status = 'SOLICITADO', solicitado_por = %s, rm_aluno = %s, email_solicitante = %s WHERE id = %s AND status = 'DISPONÍVEL';", (nome, rm, email_aluno, item_id))
    afetados = cursor.rowcount
    conn.commit(); cursor.close(); conn.close()
    if afetados > 0: return jsonify({"success": True, "message": "Solicitação enviada com sucesso! Dirija-se à secretaria."})
    return jsonify({"success": False, "message": "Este item não está mais disponível."}), 400

@app.route('/api/chat/enviar', methods=['POST'])
def enviar_chat():
    data = request.json or {}
    rm, nome, remetente, mensagem = str(data.get('rm', '')).strip(), data.get('nome', 'Anônimo').strip(), data.get('remetente', 'ALUNO').upper().strip(), data.get('mensagem', '').strip()
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("INSERT INTO mensagens_chat (rm_aluno, nome_aluno, remetente, mensagem, data_envio) VALUES (%s, %s, %s, %s, %s);", (rm, nome, remetente, mensagem, datetime.now().strftime("%d/%m/%Y %H:%M:%S")))
    conn.commit(); cursor.close(); conn.close()
    return jsonify({"success": True})

@app.route('/api/chat/mensagens/<string:rm>', methods=['GET'])
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

@app.route('/api/chat/conversas', methods=['GET'])
@token_required
def listar_conversas():
    conn = get_db_connection(); cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT rm_aluno, MAX(nome_aluno) as nome_aluno, MAX(data_envio) as ultima_msg_data, COUNT(CASE WHEN remetente = 'ALUNO' AND lida = FALSE THEN 1 END) as nao_lidas FROM mensagens_chat GROUP BY rm_aluno ORDER BY MAX(id) DESC;")
    res = cursor.fetchall(); cursor.close(); conn.close()
    return jsonify(res)

@app.route('/api/entregues', methods=['GET'])
@token_required
def get_entregues():
    conn = get_db_connection(); cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM entregues ORDER BY id DESC;")
    res = cursor.fetchall(); cursor.close(); conn.close()
    return jsonify(res)

@app.route('/api/estatisticas', methods=['GET'])
@token_required
def estatisticas():
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
