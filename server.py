"""
ETEC Achados e Perdidos - Backend Unificado (Fase 1, 2 e 3 com IA)
Versão Single-File: Tudo em um único arquivo para upload simples no GitHub sem pastas.
"""
import os
import io
import json
import re
import base64
import random
import requests
import psycopg2
from threading import Thread
from datetime import datetime, timedelta, timezone
from functools import wraps
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import cloudinary
import cloudinary.uploader
import jwt
from PIL import Image

# ============================================================
# CONFIGURAÇÕES E AMBIENTE
# ============================================================
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, static_folder=BASE_DIR, static_url_path='')

CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=False)

DATABASE_URL = os.environ.get("DATABASE_URL")
JWT_SECRET = os.environ.get("JWT_SECRET", "@#Etec_Achad0s_2026_Secret_T0ken!)").strip()
EMAIL_SECRETARIA = os.environ.get("ADMIN_EMAIL", "achadoseperdidosetec@gmail.com").strip().lower()
ADMIN_SENHA = os.environ.get("ADMIN_SENHA", "").strip()
ADMIN_SENHA_HASH = os.environ.get("ADMIN_SENHA_HASH", "").strip()

DOMINIOS_EMAIL_PERMITIDOS = [
    "@aluno.cps.sp.gov.br"
]

VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "BEl62iUYgUivxIkv69yViEuiBIa-Ib9-SkvMeAtA3LFgDZKrxZJjSPO2S-2jT_GL5prEQC43XP0_12N_sample").strip()
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "").strip()
VAPID_CLAIMS_EMAIL = os.environ.get("VAPID_CLAIMS_EMAIL", "mailto:achadoseperdidosetec@gmail.com").strip()

CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET")

if CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY:
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET,
        secure=True
    )

BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "").strip()
SMTP_SENDER = os.environ.get("SMTP_SENDER", "achadoseperdidosetec@gmail.com").strip()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_AI_API_KEY", "").strip()
PORT = int(os.environ.get("PORT", 5000))

ULTIMA_VERIFICACAO_DOACOES = None

# ============================================================
# MIDDLEWARES CORS E CACHE
# ============================================================
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
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, Accept, x-access-token'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, PATCH'
    if request.path.endswith('.html') or request.path == '/' or request.path.endswith('.js'):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

# ============================================================
# SEGURANÇA E TOKENS JWT
# ============================================================
def token_required(f):
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
        if not token: token = request.headers.get('x-access-token', '').strip('"\'')
        if not token: token = request.args.get('token', '').strip('"\'')
        if not token and request.is_json and request.json:
            token = str(request.json.get('token') or '').strip('"\'')

        if not token or token.lower() in ['null', 'undefined', 'none', '']:
            return jsonify({"success": False, "message": "Sessão não encontrada ou token ausente."}), 401
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"], leeway=timedelta(seconds=60), options={"verify_exp": True})
            request.user = payload
        except jwt.ExpiredSignatureError:
            return jsonify({"success": False, "message": "Sessão expirada. Faça login novamente.", "expired": True}), 401
        except Exception as e:
            return jsonify({"success": False, "message": f"Token inválido: {str(e)}"}), 401
        return f(*args, **kwargs)
    return decorated

def gerar_token_aluno(email, nome, rm, dias_validade=30):
    exp = datetime.now(timezone.utc) + timedelta(days=dias_validade)
    return jwt.encode({"email": email, "nome": nome, "rm": rm, "role": "aluno", "exp": exp}, JWT_SECRET, algorithm="HS256")

def gerar_token_secretaria(email, dias_validade=7):
    exp = datetime.now(timezone.utc) + timedelta(days=dias_validade)
    return jwt.encode({"user": "secretaria", "role": "secretaria", "email": email, "exp": exp}, JWT_SECRET, algorithm="HS256")

# ============================================================
# BANCO DE DADOS E MIGRATIONS
# ============================================================
def get_db_connection():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL não configurada no ambiente.")
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def calcular_dias_passados(data_str):
    if not data_str: return 0
    data_limpa = str(data_str).strip()
    for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d/%m/%y']:
        try:
            dt = datetime.strptime(data_limpa, fmt)
            return max(0, (datetime.now() - dt).days)
        except Exception:
            continue
    return 0

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
        ids_para_doacao = [i['id'] for i in itens if calcular_dias_passados(i.get('data_encontrado')) >= 90]
        if ids_para_doacao:
            cursor.execute("UPDATE itens SET status = 'PARA DOAÇÃO' WHERE id = ANY(%s);", (ids_para_doacao,))
            conn.commit()
            print(f"[Doações 90 Dias] {len(ids_para_doacao)} item(ns) atualizado(s) para 'PARA DOAÇÃO'.")
        cursor.close(); conn.close()
    except Exception as e:
        print(f"[Doações 90 Dias] Aviso: {e}")
        if conn: conn.close()

def init_db():
    if not DATABASE_URL: return
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS categorias (id SERIAL PRIMARY KEY, nome VARCHAR(50) UNIQUE NOT NULL);')
        cursor.execute('''CREATE TABLE IF NOT EXISTS itens (
            id SERIAL PRIMARY KEY, nome_item VARCHAR(150), descricao TEXT NOT NULL,
            categoria VARCHAR(50) NOT NULL, data_encontrado VARCHAR(20) NOT NULL,
            local_encontrado VARCHAR(100) NOT NULL, foto TEXT, fotos_json TEXT,
            status VARCHAR(30) DEFAULT 'DISPONÍVEL', solicitado_por VARCHAR(100),
            rm_aluno VARCHAR(20), email_solicitante VARCHAR(150),
            aprovado BOOLEAN DEFAULT TRUE, cadastrado_por_aluno BOOLEAN DEFAULT FALSE
        );''')

        for col, col_tipo in [
            ("nome_item", "VARCHAR(150)"), ("foto", "TEXT"), ("fotos_json", "TEXT"),
            ("status", "VARCHAR(30) DEFAULT 'DISPONÍVEL'"), ("solicitado_por", "VARCHAR(100)"),
            ("rm_aluno", "VARCHAR(20)"), ("email_solicitante", "VARCHAR(150)"),
            ("aprovado", "BOOLEAN DEFAULT TRUE"), ("cadastrado_por_aluno", "BOOLEAN DEFAULT FALSE")
        ]:
            try:
                cursor.execute(f"ALTER TABLE itens ADD COLUMN IF NOT EXISTS {col} {col_tipo};")
                conn.commit()
            except Exception: conn.rollback()

        try:
            cursor.execute("UPDATE itens SET aprovado = TRUE WHERE aprovado IS NULL;")
            conn.commit()
        except Exception: conn.rollback()

        try:
            cursor.execute("SELECT setval(pg_get_serial_sequence('itens', 'id'), COALESCE((SELECT MAX(id) FROM itens), 1));")
            conn.commit()
        except Exception: conn.rollback()

        cursor.execute('''CREATE TABLE IF NOT EXISTS entregues (
            id SERIAL PRIMARY KEY, item_id INT NOT NULL, nome_item TEXT NOT NULL,
            retirado_por VARCHAR(100) NOT NULL, rm_retirante VARCHAR(30) NOT NULL,
            turma_curso VARCHAR(50), data_entrega VARCHAR(30) NOT NULL, funcionario_responsavel VARCHAR(100)
        );''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS mural_perdidos (
            id SERIAL PRIMARY KEY, nome_aluno VARCHAR(100) NOT NULL, rm_aluno VARCHAR(20) NOT NULL,
            email_aluno VARCHAR(150), categoria VARCHAR(50) NOT NULL, descricao TEXT NOT NULL,
            data_registro VARCHAR(30) NOT NULL, status VARCHAR(30) DEFAULT 'PROCURANDO'
        );''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS mensagens_chat (
            id SERIAL PRIMARY KEY, rm_aluno VARCHAR(20) NOT NULL, nome_aluno VARCHAR(100) NOT NULL,
            remetente VARCHAR(20) NOT NULL, mensagem TEXT NOT NULL, data_envio VARCHAR(30) NOT NULL, lida BOOLEAN DEFAULT FALSE
        );''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS alunos (
            email VARCHAR(150) PRIMARY KEY, nome VARCHAR(100) NOT NULL, rm VARCHAR(20) NOT NULL, senha_hash TEXT NOT NULL
        );''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS codigos_auth (
            email VARCHAR(150) PRIMARY KEY, codigo VARCHAR(6) NOT NULL, expiracao TIMESTAMP NOT NULL
        );''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS push_subscriptions (
            id SERIAL PRIMARY KEY, rm_aluno VARCHAR(20) UNIQUE NOT NULL, subscription_json TEXT NOT NULL
        );''')

        cursor.execute("SELECT COUNT(*) FROM categorias;")
        if cursor.fetchone()[0] == 0:
            for c in ['MOCHILA', 'ROUPAS', 'ACESSÓRIOS', 'ESCOLARES', 'ELETRÔNICOS', 'OUTROS']:
                cursor.execute("INSERT INTO categorias (nome) VALUES (%s) ON CONFLICT DO NOTHING;", (c,))

        conn.commit(); cursor.close(); conn.close()
        verificar_e_atualizar_itens_doacao(forcar=True)
    except Exception as e:
        print(f"Erro DB init: {e}")

if DATABASE_URL:
    init_db()

# ============================================================
# INTELIGÊNCIA ARTIFICIAL E PROCESSAMENTO DE LINGUAGEM
# ============================================================
STOPWORDS = {
    'perdi', 'minha', 'meu', 'uma', 'um', 'no', 'na', 'em', 'de', 'da', 'do',
    'com', 'sem', 'favor', 'acho', 'que', 'para', 'pela', 'pelo', 'onde',
    'qual', 'quem', 'isso', 'esse', 'essa', 'este', 'esta', 'seja', 'ser'
}

GRUPOS_SINONIMOS = [
    {'moletom', 'casaco', 'blusa', 'jaqueta', 'agasalho', 'sueter', 'corta-vento', 'cardigan'},
    {'calça', 'bermuda', 'shorts', 'legging', 'jeans'},
    {'camiseta', 'camisa', 'regata', 'uniforme'},
    {'tenis', 'calcado', 'sapato', 'sandalia', 'chinelo'},
    {'estojo', 'penal', 'necessaire'},
    {'caderno', 'bloco', 'agenda', 'fichario', 'planner'},
    {'livro', 'apostila', 'manual', 'dicionario'},
    {'caneta', 'lapiseira', 'lapis', 'marcador', 'marca-texto'},
    {'garrafa', 'squeeze', 'termica', 'cantil', 'garrafinha', 'copo'},
    {'mochila', 'bolsa', 'sacola', 'mala', 'pochete', 'bag'},
    {'oculos', 'armacao', 'lente'},
    {'chave', 'chaveiro', 'cadeado', 'tag'},
    {'guarda-chuva', 'sombrinha'},
    {'bone', 'chapeu', 'touca', 'gorro'},
    {'fone', 'headphone', 'headset', 'airpods', 'earbuds', 'auricular'},
    {'carregador', 'cabo', 'adaptador', 'fonte', 'usb'},
    {'celular', 'smartphone', 'telefone', 'iphone', 'motorola', 'samsung', 'xiaomi'},
    {'calculadora', 'cientifica'}
]

CORES_RGB = [
    ("preto", (20, 20, 20)), ("branco", (235, 235, 235)), ("cinza", (128, 128, 128)),
    ("azul", (30, 80, 190)), ("vermelho", (200, 30, 30)), ("verde", (35, 145, 55)),
    ("amarelo", (230, 210, 30)), ("rosa", (230, 100, 150)), ("roxo", (120, 40, 160)),
    ("marrom", (110, 60, 30)), ("laranja", (230, 110, 20))
]

CORES_LISTA = {
    'preto', 'preta', 'azul', 'vermelho', 'vermelha', 'rosa', 'verde',
    'amarelo', 'amarela', 'cinza', 'branco', 'branca', 'prata', 'dourado',
    'marrom', 'roxo', 'roxa', 'laranja', 'bege', 'vinho', 'grafite'
}

def extrair_termos(texto):
    if not texto: return set()
    palavras = re.findall(r'[a-zA-Z0-9áéíóúãõâêîôûç]+', str(texto).lower())
    return {p for p in palavras if len(p) >= 3 and p not in STOPWORDS}

def expandir_termos_semanticos(termos_set):
    expandidos = set(termos_set)
    for termo in termos_set:
        termo_l = termo.lower().strip()
        for grupo in GRUPOS_SINONIMOS:
            if termo_l in grupo: expandidos.update(grupo)
    return expandidos

def calcular_afinidade_semantica(texto_a, texto_b):
    ta, tb = extrair_termos(texto_a), extrair_termos(texto_b)
    if not ta or not tb: return 0.0, []
    exatos = ta.intersection(tb)
    ea, eb = expandir_termos_semanticos(ta), expandir_termos_semanticos(tb)
    sinonimos = ea.intersection(tb).union(eb.intersection(ta)) - exatos
    score = (len(exatos) * 1.0 + len(sinonimos) * 0.75) / max(1, max(len(ta), len(tb)))
    motivos = []
    if exatos: motivos.append(f"Termos idênticos: {', '.join(sorted(list(exatos))[:3])}")
    if sinonimos: motivos.append(f"Sinônimos: {', '.join(sorted(list(sinonimos))[:3])}")
    return min(1.0, score), motivos

def calcular_smart_match(relato, item):
    score = 0
    detalhes = []
    cat_relato = (relato.get('categoria') or '').strip().upper()
    cat_item = (item.get('categoria') or '').strip().upper()
    if cat_relato and cat_item and cat_relato == cat_item:
        score += 30
        detalhes.append(f"Mesma categoria ({cat_relato})")

    txt_relato = (relato.get('descricao') or '')
    txt_item = f"{item.get('nome') or ''} {item.get('txt_descricao') or item.get('descricao') or ''}"
    ta, ti = extrair_termos(txt_relato), extrair_termos(txt_item)
    exatos = ta.intersection(ti)
    sinonimos = expandir_termos_semanticos(ta).intersection(ti) - exatos
    if ta:
        pct = (len(exatos) * 1.0 + len(sinonimos) * 0.75) / max(1, len(ta))
        score += min(40, round(pct * 40))
        if exatos: detalhes.append(f"Termos: {', '.join(sorted(list(exatos))[:3])}")
        if sinonimos: detalhes.append(f"Sinônimo IA: {', '.join(sorted(list(sinonimos))[:2])}")

    pr = set(re.findall(r'[a-zA-Záéíóúãõâêîôûç]+', txt_relato.lower()))
    pi = set(re.findall(r'[a-zA-Záéíóúãõâêîôûç]+', txt_item.lower()))
    cores = pr.intersection(CORES_LISTA).intersection(pi.intersection(CORES_LISTA))
    if cores:
        score += 15
        detalhes.append(f"Cor compatível: {', '.join(sorted(list(cores)))}")

    loc = (item.get('txt_local') or item.get('local_encontrado') or '').lower().strip()
    if loc and len(loc) > 2 and loc in txt_relato.lower():
        score += 15
        detalhes.append(f"Local compatível ({loc})")
    return min(100, score), detalhes

def extrair_cores_predominantes_local(imagem_bytes):
    try:
        img = Image.open(io.BytesIO(imagem_bytes)).convert('RGB')
        img.thumbnail((60, 60))
        cont = {}
        for r, g, b in list(img.getdata()):
            cor = min(CORES_RGB, key=lambda it: ((r-it[1][0])**2 + (g-it[1][1])**2 + (b-it[1][2])**2)**0.5)[0]
            cont[cor] = cont.get(cor, 0) + 1
        return [c for c, _ in sorted(cont.items(), key=lambda x: x[1], reverse=True)[:2]]
    except Exception: return ["cinza"]

def analisar_imagem_com_ia(imagem_entrada):
    if not imagem_entrada: return None, "Imagem não informada."
    img_b64, img_bytes, mime = "", None, "image/jpeg"
    if str(imagem_entrada).startswith('http'):
        try:
            r = requests.get(imagem_entrada, timeout=8)
            img_bytes = r.content
            img_b64 = base64.b64encode(img_bytes).decode('utf-8')
            if 'png' in imagem_entrada.lower(): mime = "image/png"
        except Exception as e: return None, str(e)
    elif "base64," in str(imagem_entrada):
        parts = str(imagem_entrada).split("base64,")
        img_b64 = parts[1]
        try: img_bytes = base64.b64decode(img_b64)
        except: pass
        if "image/png" in parts[0]: mime = "image/png"
    else:
        img_b64 = str(imagem_entrada)
        try: img_bytes = base64.b64decode(img_b64)
        except: pass

    if GEMINI_API_KEY and img_b64:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
            prompt = """Analise a foto do pertence escolar e retorne estritamente um JSON valido:
{"nome": "Titulo conciso", "categoria": "ROUPAS, ACESSORIOS, ESCOLARES, ELETRONICOS, MOCHILA ou OUTROS", "cores": ["cor1"], "descricao": "Descricao visual detalhada", "tags": ["tag1"]}"""
            resp = requests.post(url, json={
                "contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": mime, "data": img_b64}}]}],
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 500}
            }, headers={"Content-Type": "application/json"}, timeout=10)
            if resp.status_code == 200:
                raw = resp.json()['candidates'][0]['content']['parts'][0]['text'].strip()
                raw = re.sub(r'^```json\s*', '', raw)
                raw = re.sub(r'\s*```$', '', raw).strip()
                res = json.loads(raw)
                res['metodo'] = 'gemini_vision'
                return res, None
        except Exception as e: print(f"[Gemini] Erro: {e}")

    cores = extrair_cores_predominantes_local(img_bytes) if img_bytes else []
    cores_s = ', '.join(cores) if cores else 'não identificada'
    return {
        "nome": f"Item Escolar ({cores_s.title()})",
        "categoria": "OUTROS", "cores": cores,
        "descricao": f"Pertence escolar cor {cores_s}.",
        "tags": cores + ["etec"], "metodo": "visao_local"
    }, None

def processar_fotos(fotos_array):
    urls = []
    if not fotos_array: return urls
    for f in fotos_array:
        if not f: continue
        if str(f).startswith('http'): urls.append(str(f))
        else:
            try:
                res = cloudinary.uploader.upload(f, folder="etec_achados")
                if "secure_url" in res: urls.append(res["secure_url"])
            except Exception as e: print(f"[Cloudinary] {e}")
    return urls

def disparar_email(dest, assunto, html):
    def _send():
        if not BREVO_API_KEY or not dest: return
        try:
            requests.post("https://api.brevo.com/v3/smtp/email", json={
                "sender": {"name": "Achados e Perdidos ETEC", "email": SMTP_SENDER},
                "to": [{"email": dest}], "subject": assunto, "htmlContent": html
            }, headers={"accept": "application/json", "api-key": BREVO_API_KEY, "content-type": "application/json"}, timeout=10)
        except Exception as e: print(f"[Brevo] {e}")
    Thread(target=_send).start()

def validar_email_institucional(email):
    if not email: return False, "E-mail vazio."
    e = email.strip().lower()
    if not any(e.endswith(d) for d in DOMINIOS_EMAIL_PERMITIDOS):
        return False, f"Apenas e-mails ({', '.join(DOMINIOS_EMAIL_PERMITIDOS)}) permitidos."
    return True, e

# ============================================================
# ROTAS FRONTEND & STATIC
# ============================================================
@app.route('/logo_secretaria.png')
def logo_sec(): return send_from_directory(app.static_folder, 'logo_secretaria.png')

@app.route('/favicon.ico')
def fav():
    ref = request.headers.get('Referer', '')
    if 'controle_etec' in ref or 'secretaria' in ref or 'admin' in ref:
        return send_from_directory(app.static_folder, 'logo_secretaria.png')
    return send_from_directory(app.static_folder, 'logo.png')

@app.route('/controle_etec_7788.html')
@app.route('/secretaria')
@app.route('/admin')
def sec_web(): return send_from_directory(app.static_folder, 'controle_etec_7788.html')

@app.route('/')
def home(): return send_from_directory(app.static_folder, 'index.html')

# ============================================================
# ROTAS DE IA (FASE 3)
# ============================================================
@app.route('/api/ia/analisar-imagem', methods=['OPTIONS', 'POST'])
def rota_ia_img():
    if request.method == 'OPTIONS': return jsonify({"success": True}), 200
    d = request.json or {}
    foto = d.get('foto') or d.get('imagem')
    if not foto: return jsonify({"success": False, "message": "Nenhuma imagem informada."}), 400
    res, err = analisar_imagem_com_ia(foto)
    if err: return jsonify({"success": False, "message": err}), 500
    return jsonify({"success": True, "resultado": res})

@app.route('/api/ia/comparar-semantica', methods=['OPTIONS', 'POST'])
def rota_ia_sem():
    if request.method == 'OPTIONS': return jsonify({"success": True}), 200
    d = request.json or {}
    score, mot = calcular_afinidade_semantica(d.get('texto_a') or d.get('relato') or '', d.get('texto_b') or d.get('item') or '')
    return jsonify({"success": True, "score_percentual": round(score * 100, 1), "motivos": mot})

# ============================================================
# ROTAS PUSH NOTIFICATIONS
# ============================================================
@app.route('/api/push/public-key', methods=['OPTIONS', 'GET'])
def get_vapid_key():
    if request.method == 'OPTIONS': return jsonify({"success": True}), 200
    return jsonify({"success": True, "publicKey": VAPID_PUBLIC_KEY})

@app.route('/api/push/subscribe', methods=['OPTIONS', 'POST'])
def sub_push():
    if request.method == 'OPTIONS': return jsonify({"success": True}), 200
    d = request.json or {}
    rm, sub = str(d.get('rm') or '').strip(), d.get('subscription')
    if not rm or not sub: return jsonify({"success": False}), 400
    sub_j = json.dumps(sub) if isinstance(sub, (dict, list)) else str(sub)
    try:
        conn = get_db_connection(); c = conn.cursor()
        c.execute("INSERT INTO push_subscriptions (rm_aluno, subscription_json) VALUES (%s, %s) ON CONFLICT (rm_aluno) DO UPDATE SET subscription_json = EXCLUDED.subscription_json;", (rm, sub_j))
        conn.commit(); c.close(); conn.close()
        return jsonify({"success": True})
    except Exception as e: return jsonify({"success": False, "message": str(e)}), 500

# ============================================================
# ROTAS AUTENTICAÇÃO
# ============================================================
@app.route('/api/auth/verificar', methods=['GET', 'OPTIONS'])
@token_required
def ver_token(): return jsonify({"success": True, "user": getattr(request, 'user', {})})

@app.route('/api/auth/atualizar-rm', methods=['OPTIONS', 'POST'])
@token_required
def upd_rm():
    nrm = str((request.json or {}).get('rm', '')).strip()
    user = getattr(request, 'user', {})
    email = user.get('email')
    if not nrm or len(nrm) < 3: return jsonify({"success": False, "message": "RM inválido."}), 400
    try:
        conn = get_db_connection(); c = conn.cursor()
        c.execute("UPDATE alunos SET rm = %s WHERE email = %s;", (nrm, email))
        c.execute("UPDATE mural_perdidos SET rm_aluno = %s WHERE email_aluno = %s;", (nrm, email))
        conn.commit(); c.close(); conn.close()
        return jsonify({"success": True, "token": gerar_token_aluno(email, user.get('nome', ''), nrm), "rm": nrm})
    except Exception as e: return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/auth/enviar-codigo', methods=['OPTIONS', 'POST'])
def env_cod():
    val, email = validar_email_institucional((request.json or {}).get('email', ''))
    if not val: return jsonify({"success": False, "message": email}), 400
    cod = str(random.randint(100000, 999999))
    try:
        conn = get_db_connection(); c = conn.cursor()
        c.execute("INSERT INTO codigos_auth (email, codigo, expiracao) VALUES (%s, %s, %s) ON CONFLICT (email) DO UPDATE SET codigo = EXCLUDED.codigo, expiracao = EXCLUDED.expiracao;", (email, cod, datetime.now() + timedelta(minutes=15)))
        conn.commit(); c.close(); conn.close()
        disparar_email(email, "Código de acesso ETEC", f"<div style='padding:20px;'><h2 style='color:#dc2626;'>Código ETEC</h2><p style='font-size:24px;font-weight:bold;'>{cod}</p></div>")
        return jsonify({"success": True})
    except Exception as e: return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/auth/cadastrar', methods=['OPTIONS', 'POST'])
def cad_aluno():
    d = request.json or {}
    val, email = validar_email_institucional(d.get('email', ''))
    if not val: return jsonify({"success": False, "message": email}), 400
    cod, nome, rm, senha = d.get('codigo', '').strip(), d.get('nome', '').strip(), d.get('rm', '').strip(), d.get('senha', '').strip()
    if not rm:
        rm = 'PROFESSOR' if any(email.endswith(d) for d in ['@cps.sp.gov.br', '@etec.sp.gov.br']) else 'ALUNO'
    try:
        conn = get_db_connection(); c = conn.cursor(cursor_factory=RealDictCursor)
        c.execute("SELECT codigo, expiracao FROM codigos_auth WHERE email = %s;", (email,))
        reg = c.fetchone()
        if not reg or reg['codigo'] != cod or reg['expiracao'] < datetime.now():
            return jsonify({"success": False, "message": "Código inválido ou expirado."}), 400
        c.execute("SELECT email FROM alunos WHERE email = %s;", (email,))
        if c.fetchone(): return jsonify({"success": False, "message": "E-mail já cadastrado."}), 400
        c.execute("INSERT INTO alunos (email, nome, rm, senha_hash) VALUES (%s, %s, %s, %s);", (email, nome, rm, generate_password_hash(senha)))
        c.execute("DELETE FROM codigos_auth WHERE email = %s;", (email,))
        conn.commit(); c.close(); conn.close()
        return jsonify({"success": True, "token": gerar_token_aluno(email, nome, rm), "aluno": {"nome": nome, "rm": rm, "email": email}})
    except Exception as e: return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/auth/login-aluno', methods=['OPTIONS', 'POST'])
def log_aluno():
    if request.method == 'OPTIONS': return jsonify({"success": True}), 200
    d = request.json or {}
    email, senha = d.get('email', '').lower().strip(), d.get('senha', '').strip()
    
    # ACESSO PROFESSOR: digitar 'professor' no e-mail e na senha
    if email == 'professor' and senha.lower() == 'professor':
        token = gerar_token_aluno("professor@cps.sp.gov.br", "Professor(a)", "PROFESSOR")
        return jsonify({
            "success": True,
            "token": token,
            "aluno": {
                "nome": "Professor(a)",
                "rm": "PROFESSOR",
                "email": "professor@cps.sp.gov.br"
            }
        })
    try:
        conn = get_db_connection(); c = conn.cursor(cursor_factory=RealDictCursor)
        c.execute("SELECT * FROM alunos WHERE email = %s;", (email,))
        a = c.fetchone(); c.close(); conn.close()
        if a and check_password_hash(a['senha_hash'], senha):
            return jsonify({"success": True, "token": gerar_token_aluno(a['email'], a['nome'], a['rm']), "aluno": {"nome": a['nome'], "rm": a['rm'], "email": a['email']}})
        return jsonify({"success": False, "message": "Credenciais incorretas."}), 401
    except Exception as e: return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/auth/redefinir', methods=['OPTIONS', 'POST'])
def red_senha():
    d = request.json or {}
    email, cod, senha = d.get('email', '').lower().strip(), d.get('codigo', '').strip(), d.get('senha', '').strip()
    try:
        conn = get_db_connection(); c = conn.cursor(cursor_factory=RealDictCursor)
        c.execute("SELECT codigo, expiracao FROM codigos_auth WHERE email = %s;", (email,))
        reg = c.fetchone()
        if not reg or reg['codigo'] != cod or reg['expiracao'] < datetime.now():
            return jsonify({"success": False, "message": "Código inválido ou expirado."}), 400
        c.execute("UPDATE alunos SET senha_hash = %s WHERE email = %s;", (generate_password_hash(senha), email))
        c.execute("DELETE FROM codigos_auth WHERE email = %s;", (email,))
        conn.commit(); c.close(); conn.close()
        return jsonify({"success": True, "message": "Senha redefinida com sucesso."})
    except Exception as e: return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/login', methods=['OPTIONS', 'POST'])
def log_sec():
    d = request.json or {}
    email, senha = (d.get('email') or '').strip().lower(), (d.get('senha') or '').strip()
    valido = False
    if email == EMAIL_SECRETARIA:
        if ADMIN_SENHA and senha == ADMIN_SENHA: valido = True
        elif ADMIN_SENHA_HASH:
            try: valido = check_password_hash(ADMIN_SENHA_HASH, senha)
            except: valido = (senha == ADMIN_SENHA_HASH)
    if valido: return jsonify({"success": True, "token": gerar_token_secretaria(email)})
    return jsonify({"success": False, "message": "Credenciais inválidas."}), 401

# ============================================================
# ROTAS ITENS E CATEGORIAS
# ============================================================
@app.route('/api/categorias/<string:nome>', methods=['OPTIONS', 'DELETE'])
@app.route('/api/categorias', methods=['OPTIONS', 'GET', 'POST', 'DELETE'])
def rotas_cat(nome=None):
    if request.method == 'OPTIONS': return jsonify({"success": True}), 200
    if request.method == 'GET':
        conn = get_db_connection(); c = conn.cursor(cursor_factory=RealDictCursor)
        c.execute("SELECT * FROM categorias ORDER BY id ASC;")
        res = c.fetchall(); c.close(); conn.close()
        return jsonify(res)
    elif request.method == 'POST':
        nc = ((request.json or {}).get('nome') or '').strip().upper()
        if not nc: return jsonify({"success": False}), 400
        conn = get_db_connection(); c = conn.cursor()
        c.execute("INSERT INTO categorias (nome) VALUES (%s) ON CONFLICT DO NOTHING;", (nc,))
        conn.commit(); c.close(); conn.close()
        return jsonify({"success": True})
    elif request.method == 'DELETE':
        cat_n = (nome or (request.json or {}).get('nome') or request.args.get('nome') or '').strip().upper()
        conn = get_db_connection(); c = conn.cursor()
        c.execute("DELETE FROM categorias WHERE UPPER(nome) = %s;", (cat_n,))
        conn.commit(); c.close(); conn.close()
        return jsonify({"success": True})

@app.route('/api/itens', methods=['OPTIONS', 'GET'])
def get_all_itens():
    try:
        verificar_e_atualizar_itens_doacao()
        conn = get_db_connection(); c = conn.cursor(cursor_factory=RealDictCursor)
        c.execute("""
            SELECT id, COALESCE(nome_item, descricao) as nome, descricao as txt_descricao,
                   categoria, data_encontrado as txt_data, local_encontrado as txt_local,
                   foto, fotos_json, status, solicitado_por, rm_aluno,
                   COALESCE(aprovado, TRUE) as aprovado,
                   COALESCE(cadastrado_por_aluno, FALSE) as cadastrado_por_aluno
            FROM itens WHERE (aprovado IS NULL OR aprovado = TRUE) ORDER BY id DESC;
        """)
        itens = c.fetchall()
        for it in itens:
            try: it['fotos'] = json.loads(it['fotos_json']) if it.get('fotos_json') else ([it['foto']] if it.get('foto') else [])
            except: it['fotos'] = [it['foto']] if it.get('foto') else []
        c.close(); conn.close()
        return jsonify(itens)
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/itens/pendentes', methods=['OPTIONS', 'GET'])
@token_required
def get_pend():
    try:
        conn = get_db_connection(); c = conn.cursor(cursor_factory=RealDictCursor)
        c.execute("SELECT id, nome_item as nome, descricao as txt_descricao, categoria, data_encontrado as txt_data, local_encontrado as txt_local, foto, fotos_json, status, rm_aluno FROM itens WHERE aprovado = FALSE ORDER BY id DESC;")
        itens = c.fetchall()
        for it in itens:
            try: it['fotos'] = json.loads(it['fotos_json']) if it.get('fotos_json') else []
            except: it['fotos'] = []
        c.close(); conn.close()
        return jsonify(itens)
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/itens/cadastrar-aluno', methods=['OPTIONS', 'POST'])
def cad_item_aluno():
    d = request.json or {}
    nome, desc, cat = (d.get('nome') or '').strip(), (d.get('descricao') or '').strip(), (d.get('categoria') or 'OUTROS').strip()
    data_enc, local, rm = (d.get('data') or datetime.now().strftime("%d/%m/%Y")).strip(), (d.get('local') or 'Não informado').strip(), (d.get('rm') or '').strip()
    urls = processar_fotos(d.get('fotos') or ([d.get('foto')] if d.get('foto') else []))
    try:
        conn = get_db_connection(); c = conn.cursor()
        c.execute("INSERT INTO itens (nome_item, descricao, categoria, data_encontrado, local_encontrado, foto, fotos_json, status, aprovado, cadastrado_por_aluno, rm_aluno) VALUES (%s, %s, %s, %s, %s, %s, %s, 'DISPONÍVEL', FALSE, TRUE, %s);", (nome, desc, cat, data_enc, local, urls[0] if urls else '', json.dumps(urls), rm))
        conn.commit(); c.close(); conn.close()
        return jsonify({"success": True, "message": "Item enviado para moderação!"})
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/itens/<int:item_id>/aprovar', methods=['OPTIONS', 'PUT'])
@token_required
def apr_item(item_id):
    try:
        conn = get_db_connection(); c = conn.cursor()
        c.execute("UPDATE itens SET aprovado = TRUE WHERE id = %s;", (item_id,))
        conn.commit(); c.close(); conn.close()
        return jsonify({"success": True})
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/itens', methods=['OPTIONS', 'POST'])
@token_required
def cad_item():
    d = request.json or {}
    nome, desc, cat = (d.get('nome') or '').strip(), (d.get('descricao') or '').strip(), (d.get('categoria') or 'OUTROS').strip()
    data_enc, local, status = (d.get('data') or datetime.now().strftime("%d/%m/%Y")).strip(), (d.get('local') or 'Não informado').strip(), (d.get('status') or 'DISPONÍVEL').strip()
    if not desc: return jsonify({"success": False, "error": "Descrição obrigatória."}), 400
    urls = processar_fotos(d.get('fotos') or ([d.get('foto')] if d.get('foto') else []))
    try:
        conn = get_db_connection(); c = conn.cursor(cursor_factory=RealDictCursor)
        c.execute("INSERT INTO itens (nome_item, descricao, categoria, data_encontrado, local_encontrado, foto, fotos_json, status, aprovado) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE) RETURNING id;", (nome, desc, cat, data_enc, local, urls[0] if urls else '', json.dumps(urls), status))
        nid = c.fetchone()['id']
        conn.commit()

        try:
            termos_n = extrair_termos(f"{nome} {desc}")
            c.execute("SELECT * FROM mural_perdidos WHERE status = 'PROCURANDO' AND categoria = %s;", (cat,))
            for m in c.fetchall():
                if len(termos_n.intersection(extrair_termos(m.get('descricao', '')))) >= 1:
                    c.execute("INSERT INTO mensagens_chat (rm_aluno, nome_aluno, remetente, mensagem, data_envio) VALUES (%s, %s, 'SECRETARIA', %s, %s);", (m['rm_aluno'], m['nome_aluno'], f"Possível pertence encontrado: '{nome or desc}'. Veja o catálogo!", datetime.now().strftime("%d/%m/%Y %H:%M:%S")))
            conn.commit()
        except Exception: conn.rollback()
        c.close(); conn.close()
        return jsonify({"success": True, "id": nid})
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/itens/<int:item_id>', methods=['OPTIONS', 'PUT', 'POST', 'DELETE'])
@token_required
def gen_item(item_id):
    try:
        conn = get_db_connection(); c = conn.cursor(cursor_factory=RealDictCursor)
        if request.method == 'DELETE' or (request.is_json and request.json and request.json.get('_method') == 'DELETE'):
            c.execute("DELETE FROM entregues WHERE item_id = %s;", (item_id,))
            c.execute("DELETE FROM itens WHERE id = %s;", (item_id,))
            conn.commit(); c.close(); conn.close()
            return jsonify({"success": True})
        else:
            d = request.json or {}
            c.execute("SELECT * FROM itens WHERE id = %s;", (item_id,))
            it = c.fetchone()
            if not it: c.close(); conn.close(); return jsonify({"success": False}), 404
            nome = (d.get('nome') or it.get('nome_item', '')).strip()
            desc = (d.get('descricao') or it.get('descricao', '')).strip()
            cat = (d.get('categoria') or it.get('categoria', 'OUTROS')).strip()
            data_enc = (d.get('data') or it.get('data_encontrado', '')).strip()
            local = (d.get('local') or it.get('local_encontrado', '')).strip()
            status = (d.get('status') or it.get('status', 'DISPONÍVEL')).strip()

            c.execute("UPDATE itens SET nome_item=%s, descricao=%s, categoria=%s, data_encontrado=%s, local_encontrado=%s, status=%s, aprovado=TRUE WHERE id=%s;", (nome, desc, cat, data_enc, local, status, item_id))
            if status.upper() == 'ENTREGUE':
                c.execute("DELETE FROM entregues WHERE item_id = %s;", (item_id,))
                c.execute("INSERT INTO entregues (item_id, nome_item, retirado_por, rm_retirante, turma_curso, data_entrega, funcionario_responsavel) VALUES (%s, %s, %s, %s, %s, %s, %s);", (item_id, nome or desc, d.get('retirado_por', it.get('solicitado_por', '')), d.get('rm_retirante', it.get('rm_aluno', '')), d.get('turma_curso', '-'), d.get('data_entrega', datetime.now().strftime("%d/%m/%Y %H:%M")), d.get('funcionario_responsavel', 'Secretaria')))
            conn.commit(); c.close(); conn.close()
            return jsonify({"success": True})
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/itens/<int:item_id>/recusar', methods=['OPTIONS', 'PUT', 'DELETE', 'POST'])
@token_required
def rec_item(item_id):
    try:
        conn = get_db_connection(); c = conn.cursor(cursor_factory=RealDictCursor)
        c.execute("SELECT aprovado FROM itens WHERE id = %s;", (item_id,))
        it = c.fetchone()
        if it and it.get('aprovado') is False:
            c.execute("DELETE FROM itens WHERE id = %s;", (item_id,))
            msg = "Item recusado e excluído."
        else:
            c.execute("UPDATE itens SET status = 'DISPONÍVEL', solicitado_por = NULL, rm_aluno = NULL, email_solicitante = NULL WHERE id = %s;", (item_id,))
            msg = "Item retornado para DISPONÍVEL."
        conn.commit(); c.close(); conn.close()
        return jsonify({"success": True, "message": msg})
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/itens/doacoes/concluir', methods=['OPTIONS', 'DELETE'])
@token_required
def conc_doacoes():
    conn = get_db_connection(); c = conn.cursor()
    c.execute("DELETE FROM itens WHERE UPPER(status) LIKE 'DOAÇÃO%' OR UPPER(status) LIKE 'DOACAO%';")
    conn.commit(); c.close(); conn.close()
    return jsonify({"success": True})

@app.route('/api/solicitar', methods=['OPTIONS', 'POST'])
def sol_item():
    d = request.json or {}
    conn = get_db_connection(); c = conn.cursor()
    c.execute("UPDATE itens SET status = 'SOLICITADO', solicitado_por = %s, rm_aluno = %s, email_solicitante = %s WHERE id = %s AND status = 'DISPONÍVEL';", (d.get('nome'), d.get('rm'), d.get('email'), d.get('id')))
    af = c.rowcount; conn.commit(); c.close(); conn.close()
    if af > 0: return jsonify({"success": True})
    return jsonify({"success": False, "message": "Item indisponível."}), 400

# ============================================================
# ROTAS MURAL DE PERDIDOS
# ============================================================
@app.route('/api/mural', methods=['OPTIONS', 'GET', 'POST'])
def rotas_mural():
    if request.method == 'OPTIONS': return jsonify({"success": True}), 200
    if request.method == 'GET':
        conn = get_db_connection(); c = conn.cursor(cursor_factory=RealDictCursor)
        c.execute("SELECT * FROM mural_perdidos ORDER BY id DESC;")
        res = c.fetchall(); c.close(); conn.close()
        return jsonify(res)
    else:
        d = request.json or {}
        conn = get_db_connection(); c = conn.cursor()
        c.execute("INSERT INTO mural_perdidos (nome_aluno, rm_aluno, email_aluno, categoria, descricao, data_registro, status) VALUES (%s, %s, %s, %s, %s, %s, 'PROCURANDO');", (d.get('nome'), d.get('rm'), d.get('email'), d.get('categoria'), d.get('descricao'), datetime.now().strftime("%d/%m/%Y %H:%M")))
        conn.commit(); c.close(); conn.close()
        return jsonify({"success": True})

@app.route('/api/mural/aluno/<string:rm>', methods=['OPTIONS', 'GET'])
def mural_al(rm):
    conn = get_db_connection(); c = conn.cursor(cursor_factory=RealDictCursor)
    c.execute("SELECT id, categoria, descricao, data_registro as data, status FROM mural_perdidos WHERE rm_aluno = %s ORDER BY id DESC;", (rm,))
    res = c.fetchall(); c.close(); conn.close()
    return jsonify(res)

@app.route('/api/mural/<int:id>', methods=['OPTIONS', 'DELETE'])
@token_required
def del_mural(id):
    conn = get_db_connection(); c = conn.cursor()
    c.execute("DELETE FROM mural_perdidos WHERE id = %s;", (id,))
    conn.commit(); c.close(); conn.close()
    return jsonify({"success": True})

# ============================================================
# ROTAS CHAT
# ============================================================
@app.route('/api/chat/enviar', methods=['OPTIONS', 'POST'])
def env_chat():
    d = request.json or {}
    rm, nome, rem, msg = str(d.get('rm', '')).strip(), d.get('nome', 'Anônimo').strip(), d.get('remetente', 'ALUNO').upper().strip(), d.get('mensagem', '').strip()
    if not rm or not msg: return jsonify({"success": False}), 400
    conn = get_db_connection(); c = conn.cursor()
    c.execute("INSERT INTO mensagens_chat (rm_aluno, nome_aluno, remetente, mensagem, data_envio) VALUES (%s, %s, %s, %s, %s);", (rm, nome, rem, msg, datetime.now().strftime("%d/%m/%Y %H:%M:%S")))
    conn.commit(); c.close(); conn.close()
    return jsonify({"success": True})

@app.route('/api/chat/mensagens/<string:rm>', methods=['OPTIONS', 'GET'])
def get_chat_msgs(rm):
    conn = get_db_connection(); c = conn.cursor(cursor_factory=RealDictCursor)
    c.execute("SELECT * FROM mensagens_chat WHERE rm_aluno = %s ORDER BY id ASC;", (rm,))
    msgs = c.fetchall()
    if request.args.get('marcar_lida', 'false').lower() == 'true' and msgs:
        outro = 'SECRETARIA' if request.args.get('origem', 'ALUNO').upper() == 'ALUNO' else 'ALUNO'
        c.execute("UPDATE mensagens_chat SET lida = TRUE WHERE rm_aluno = %s AND remetente = %s AND lida = FALSE;", (rm, outro))
        conn.commit()
    c.close(); conn.close()
    return jsonify(msgs)

@app.route('/api/chat/conversas', methods=['OPTIONS', 'GET'])
@token_required
def list_convs():
    try:
        conn = get_db_connection(); c = conn.cursor(cursor_factory=RealDictCursor)
        c.execute("""
            SELECT m.rm_aluno,
                   COALESCE((SELECT nome FROM alunos WHERE rm = m.rm_aluno LIMIT 1), 'Aluno RM ' || m.rm_aluno) as nome_aluno,
                   (SELECT mensagem FROM mensagens_chat WHERE rm_aluno = m.rm_aluno ORDER BY id DESC LIMIT 1) as ultima_mensagem,
                   (SELECT data_envio FROM mensagens_chat WHERE rm_aluno = m.rm_aluno ORDER BY id DESC LIMIT 1) as ultima_msg_data,
                   COUNT(CASE WHEN m.remetente = 'ALUNO' AND m.lida = FALSE THEN 1 END) as nao_lidas
            FROM mensagens_chat m GROUP BY m.rm_aluno ORDER BY MAX(m.id) DESC;
        """)
        res = c.fetchall(); c.close(); conn.close()
        return jsonify(res)
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

# ============================================================
# ROTAS RELATÓRIOS & SMART MATCH
# ============================================================
@app.route('/api/entregues', methods=['OPTIONS', 'GET'])
@token_required
def rotas_entregues():
    conn = get_db_connection(); c = conn.cursor(cursor_factory=RealDictCursor)
    c.execute("SELECT * FROM entregues ORDER BY id DESC;")
    res = c.fetchall(); c.close(); conn.close()
    return jsonify(res)

@app.route('/api/estatisticas', methods=['OPTIONS', 'GET'])
@token_required
def rotas_stats():
    verificar_e_atualizar_itens_doacao()
    conn = None
    try:
        conn = get_db_connection(); c = conn.cursor(cursor_factory=RealDictCursor)
        c.execute("SELECT COUNT(*) as total FROM itens WHERE aprovado = TRUE;")
        total_itens = c.fetchone()['total']
        c.execute("SELECT COUNT(*) as total FROM entregues;")
        total_entregues = c.fetchone()['total']
        c.execute("SELECT COUNT(*) as total FROM itens WHERE (status LIKE 'DOAÇÃO%' OR status LIKE 'DOACAO%') AND aprovado = TRUE;")
        total_doacoes = c.fetchone()['total']
        c.execute("SELECT COUNT(*) as total FROM itens WHERE status = 'DISPONÍVEL' AND aprovado = TRUE;")
        total_disponiveis = c.fetchone()['total']
        c.execute("SELECT COUNT(*) as total FROM itens WHERE status = 'SOLICITADO' AND aprovado = TRUE;")
        total_solicitados = c.fetchone()['total']

        c.execute("SELECT COALESCE(categoria, 'OUTROS') as categoria, COUNT(*) as qtd FROM itens WHERE aprovado = TRUE GROUP BY categoria ORDER BY qtd DESC;")
        cats = c.fetchall()
        c.execute("SELECT COALESCE(local_encontrado, 'Indefinido') as local, COUNT(*) as qtd FROM itens WHERE aprovado = TRUE AND local_encontrado IS NOT NULL AND local_encontrado != '' GROUP BY local_encontrado ORDER BY qtd DESC LIMIT 6;")
        locs = c.fetchall()
        tot = total_itens + total_entregues
        taxa = round((total_entregues / tot * 100), 1) if tot > 0 else 0.0
        c.close(); conn.close()
        return jsonify({"success": True, "total_itens": total_itens, "total_entregues": total_entregues, "total_doacoes": total_doacoes, "total_disponiveis": total_disponiveis, "total_solicitados": total_solicitados, "taxa_devolucao": taxa, "por_categoria": cats, "por_local": locs})
    except Exception as e:
        if conn: conn.close()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/smart-match', methods=['OPTIONS', 'GET'])
@token_required
def rotas_sm_match():
    try:
        conn = get_db_connection(); c = conn.cursor(cursor_factory=RealDictCursor)
        c.execute("SELECT id, nome_aluno, rm_aluno, email_aluno, categoria, descricao, data_registro FROM mural_perdidos WHERE status = 'PROCURANDO' OR status IS NULL ORDER BY id DESC;")
        relatos = c.fetchall()
        c.execute("SELECT id, COALESCE(nome_item, descricao) as nome, descricao as txt_descricao, categoria, data_encontrado as txt_data, local_encontrado as txt_local, foto, fotos_json, status FROM itens WHERE aprovado = TRUE AND status = 'DISPONÍVEL';")
        itens = c.fetchall()
        for it in itens:
            try: it['fotos'] = json.loads(it['fotos_json']) if it.get('fotos_json') else []
            except: it['fotos'] = []
        resultados = []
        for r in relatos:
            matches = []
            for it in itens:
                sc, mot = calcular_smart_match(r, it)
                if sc >= 45: matches.append({"item": it, "score": sc, "motivos": mot})
            matches.sort(key=lambda x: x['score'], reverse=True)
            resultados.append({"relato": r, "total_matches": len(matches), "top_score": matches[0]['score'] if matches else 0, "matches": matches[:5]})
        c.close(); conn.close()
        return jsonify({"success": True, "resultados": resultados})
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

# ============================================================
# PONTO DE ENTRADA
# ============================================================
if __name__ == "__main__":
    porta = int(os.environ.get("PORT", PORT))
    print(f"🚀 Servidor ETEC iniciado na porta {porta}")
    app.run(host='0.0.0.0', port=porta)
