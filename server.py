from utils.uploads import SCHEMA_UPLOADS
from utils.chat_retencao import SCHEMA_RETENCAO
from utils.validacao_item import validar_item, validar_categoria
from utils.entregas import cancelar_entregas, registrar_entrega
from utils.entregas import SCHEMA_ENTREGAS
from utils.cadastros import SCHEMA_CADASTROS
from utils.notificacoes import SCHEMA_NOTIFICACOES
"""
ETEC Achados e Perdidos - Backend Unificado (Fase 1, 2 e 3 com IA)
Versão Single-File: Tudo em um único arquivo para upload simples no GitHub sem pastas.
"""
import os
import logging
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
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import HTTPException
import cloudinary
import cloudinary.uploader
import jwt
from PIL import Image
from services.ai_vision_service import analisar_imagem_com_ia
from services import push_delivery
from services.cloudinary_service import processar_fotos, FalhaUploadFotos
from utils.privacy import item_publico, relato_publico
from utils.security import consulta_publica, token_required, secretaria_required, categorias_required, pode_acessar_chat, identidade_aluno, identidade_portal
from utils.helpers import validar_email_institucional
from utils.doacoes import DOACOES_PENDENTES_SQL
from utils.professores import SCHEMA_ACESSO_PROFESSORES
from utils.push import SCHEMA_PUSH, SCHEMA_ENTREGAS_PUSH, SCHEMA_EMAIL_CHAT, SCHEMA_LIMITE_PUSH, INDICE_ENTREGAS_PUSH
from config import JWT_SECRET

# ============================================================
# CONFIGURAÇÕES E AMBIENTE
# ============================================================
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, static_folder=BASE_DIR, static_url_path='')
from blueprints.professores import professores_bp
app.register_blueprint(professores_bp)
from blueprints.Push import push_bp
app.register_blueprint(push_bp)
from blueprints.uploads import uploads_bp
app.register_blueprint(uploads_bp)
from blueprints.notificacoes import notificacoes_bp
app.register_blueprint(notificacoes_bp)
from blueprints.cadastros import cadastros_bp
app.register_blueprint(cadastros_bp)

CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=False)

# Limites por IP; em produção multi-worker, configure storage compartilhado (ex.: Redis).
limiter = Limiter(get_remote_address, app=app, default_limits=["300 per hour"], storage_uri=os.environ.get("RATELIMIT_STORAGE_URI", "memory://"), headers_enabled=True)
logging.basicConfig(level=os.environ.get('LOG_LEVEL', 'INFO'), format='%(asctime)s %(levelname)s %(name)s %(message)s')
logger = logging.getLogger('etec_achados')

def limpar_texto_entrada(valor, limite=1000):
    """Normaliza campos textuais recebidos por JSON e remove caracteres de controle."""
    if valor is None:
        return ""
    if not isinstance(valor, (str, int, float)):
        return ""
    texto = str(valor).replace("\x00", "")
    texto = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]", "", texto)
    return texto.strip()[:limite]

app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_UPLOAD_BYTES', 8 * 1024 * 1024))

@app.errorhandler(FalhaUploadFotos)
def falha_upload_fotos(error):
    return jsonify({'success': False, 'message': str(error)}), 502

@app.errorhandler(413)
def payload_too_large(error):
    return jsonify({"success": False, "error": {"code": "PAYLOAD_TOO_LARGE", "message": "A imagem ou requisição excede o limite de 8 MB."}}), 413

@app.errorhandler(429)
def rate_limit_exceeded(error):
    return jsonify({"success": False, "error": {"code": "RATE_LIMITED", "message": "Muitas tentativas em pouco tempo. Aguarde e tente novamente."}}), 429

@app.errorhandler(Exception)
def handle_unexpected_error(error):
    if isinstance(error, HTTPException):
        return jsonify({"success": False, "error": error.description, "code": error.name.upper().replace(" ", "_")}), error.code
    logger.exception("Falha não tratada | path=%s method=%s", request.path, request.method)
    return jsonify({"success": False, "error": "Ocorreu um erro interno. Informe o horário e o código ao suporte.", "code": "INTERNAL_ERROR", "request_path": request.path}), 500


DATABASE_URL = os.environ.get("DATABASE_URL")
EMAIL_SECRETARIA = os.environ.get("ADMIN_EMAIL", "achadoseperdidosetec@gmail.com").strip().lower()
ADMIN_SENHA = os.environ.get("ADMIN_SENHA", "").strip()
ADMIN_SENHA_HASH = os.environ.get("ADMIN_SENHA_HASH", "").strip()

DOMINIOS_EMAIL_PERMITIDOS = [
    "@aluno.cps.sp.gov.br", "@cps.sp.gov.br", "@etec.sp.gov.br"
]

VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "").strip()
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
def gerar_token_aluno(email, nome, rm, dias_validade=30):
    exp = datetime.now(timezone.utc) + timedelta(days=dias_validade)
    return jwt.encode({"email": email, "nome": nome, "rm": rm, "role": "aluno", "auth_version": 2, "exp": exp}, JWT_SECRET, algorithm="HS256")

def gerar_token_secretaria(email, dias_validade=7):
    exp = datetime.now(timezone.utc) + timedelta(days=dias_validade)
    return jwt.encode({"user": "secretaria", "role": "secretaria", "email": email, "auth_version": 2, "exp": exp}, JWT_SECRET, algorithm="HS256")

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
        cursor.execute(SCHEMA_ACESSO_PROFESSORES)
        cursor.execute(SCHEMA_ENTREGAS)
        cursor.execute(SCHEMA_NOTIFICACOES)
        cursor.execute(SCHEMA_CADASTROS)
        cursor.execute(SCHEMA_PUSH)
        cursor.execute(SCHEMA_ENTREGAS_PUSH)
        cursor.execute(INDICE_ENTREGAS_PUSH)
        cursor.execute(SCHEMA_EMAIL_CHAT)
        cursor.execute(SCHEMA_RETENCAO)
        cursor.execute(SCHEMA_UPLOADS)
        cursor.execute(SCHEMA_LIMITE_PUSH)
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

# ------------------------------------------------------------
# PÁGINA 404 PERSONALIZADA
# - Navegador abrindo um endereço que não existe -> 404.html (status 404)
# - Chamadas da API, imagens, scripts etc. -> JSON, para não quebrar o front
# ------------------------------------------------------------
@app.errorhandler(404)
def pagina_nao_encontrada(erro):
    if request.path.startswith('/api/') or 'text/html' not in request.headers.get('Accept', ''):
        return jsonify({"success": False, "message": "Rota não encontrada."}), 404
    try:
        resposta = send_from_directory(app.static_folder, '404.html')
        resposta.status_code = 404
        return resposta
    except Exception:
        return "Página não encontrada", 404

# ============================================================
# ROTAS DE IA (FASE 3)
# ============================================================
@app.route('/api/ia/analisar-imagem', methods=['OPTIONS', 'POST'])
@limiter.limit('20 per minute')
def rota_ia_img():
    if request.method == 'OPTIONS': return jsonify({"success": True}), 200
    d = request.json or {}
    foto = d.get('foto') or d.get('imagem')
    if not foto: return jsonify({"success": False, "message": "Nenhuma imagem informada."}), 400
    if not isinstance(foto, str) or len(foto) > 11_500_000:
        return jsonify({"success": False, "error": {"code": "INVALID_IMAGE", "message": "Imagem inválida ou maior que o limite permitido."}}), 413
    res, err = analisar_imagem_com_ia(foto)
    if err: return jsonify({"success": False, "error": {"code": "VISION_ANALYSIS_FAILED", "message": "Não foi possível analisar a imagem.", "detail": str(err)[:300]}}), 400
    # Cruzamento de OCR com alunos cadastrados; não retorna e-mail ao navegador.
    res["aluno_correspondente"] = None
    rm_ocr = re.sub(r"[^A-Za-z0-9]", "", str(res.get("ocr_rm") or ""))[:20]
    nome_ocr = re.sub(r"\s+", " ", str(res.get("ocr_nome_aluno") or "")).strip()[:100]
    if res.get("pode_preencher") and res.get("ocr_confianca") == "alta" and (rm_ocr or nome_ocr):
        conn = None
        try:
            conn = get_db_connection()
            c = conn.cursor(cursor_factory=RealDictCursor)
            if rm_ocr:
                c.execute("SELECT nome, rm FROM alunos WHERE regexp_replace(COALESCE(rm,''), '[^A-Za-z0-9]', '', 'g') = %s LIMIT 1", (rm_ocr,))
                aluno = c.fetchone()
            else:
                aluno = None
            if not aluno and nome_ocr and len(nome_ocr.split()) >= 2:
                c.execute("SELECT nome, rm FROM alunos WHERE lower(nome) = lower(%s) LIMIT 1", (nome_ocr,))
                aluno = c.fetchone()
            if aluno:
                res["aluno_correspondente"] = {"nome": aluno.get("nome"), "rm_encontrado": bool(rm_ocr and aluno.get("rm"))}
                res["ocr_rm"] = str(aluno.get("rm") or rm_ocr)
            c.close()
        except Exception:
            logger.exception("Falha no cruzamento OCR/alunos")
        finally:
            if conn:
                conn.close()
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
    except Exception:
        logger.exception("Falha na rota de autenticação/notificação | path=%s", request.path)
        return jsonify({"success": False, "message": "Não foi possível concluir a operação.", "code": "REQUEST_FAILED", "path": request.path}), 500

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
    except Exception:
        logger.exception("Falha na rota de autenticação/notificação | path=%s", request.path)
        return jsonify({"success": False, "message": "Não foi possível concluir a operação.", "code": "REQUEST_FAILED", "path": request.path}), 500

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
    except Exception:
        logger.exception("Falha na rota de autenticação/notificação | path=%s", request.path)
        return jsonify({"success": False, "message": "Não foi possível concluir a operação.", "code": "REQUEST_FAILED", "path": request.path}), 500

@app.route('/api/auth/login-aluno', methods=['OPTIONS', 'POST'])
def log_aluno():
    if request.method == 'OPTIONS': return jsonify({"success": True}), 200
    d = request.json or {}
    email, senha = d.get('email', '').lower().strip(), d.get('senha', '').strip()
    
    try:
        conn = get_db_connection(); c = conn.cursor(cursor_factory=RealDictCursor)
        c.execute("SELECT * FROM alunos WHERE email = %s;", (email,))
        a = c.fetchone(); c.close(); conn.close()
        if a and check_password_hash(a['senha_hash'], senha):
            return jsonify({"success": True, "token": gerar_token_aluno(a['email'], a['nome'], a['rm']), "aluno": {"nome": a['nome'], "rm": a['rm'], "email": a['email']}})
        return jsonify({"success": False, "message": "Credenciais incorretas."}), 401
    except Exception:
        logger.exception("Falha na rota de autenticação/notificação | path=%s", request.path)
        return jsonify({"success": False, "message": "Não foi possível concluir a operação.", "code": "REQUEST_FAILED", "path": request.path}), 500

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
    except Exception:
        logger.exception("Falha na rota de autenticação/notificação | path=%s", request.path)
        return jsonify({"success": False, "message": "Não foi possível concluir a operação.", "code": "REQUEST_FAILED", "path": request.path}), 500

@app.route('/api/login', methods=['OPTIONS', 'POST'])
@limiter.limit('10 per minute')
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
@categorias_required
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
@consulta_publica
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
        return jsonify(itens if request.user.get('role') == 'secretaria' else [item_publico(it) for it in itens])
    except Exception as e: logger.exception("Falha de banco/rota | path=%s", request.path); return jsonify({"success": False, "error": "Não foi possível concluir a operação.", "code": "REQUEST_FAILED", "path": request.path}), 500

@app.route('/api/itens/pendentes', methods=['OPTIONS', 'GET'])
@secretaria_required
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
    except Exception as e: logger.exception("Falha de banco/rota | path=%s", request.path); return jsonify({"success": False, "error": "Não foi possível concluir a operação.", "code": "REQUEST_FAILED", "path": request.path}), 500

@app.route('/api/itens/cadastrar-aluno', methods=['OPTIONS', 'POST'])
@token_required
@limiter.limit('10 per minute')
def cad_item_aluno():
    autor = identidade_portal()
    if not autor:
        return jsonify({'success': False, 'message': 'Entre com sua conta institucional para cadastrar objetos.'}), 403
    d = request.get_json(silent=True)
    try:
        v = validar_item(d); validar_categoria(get_db_connection, v['categoria'])
    except ValueError as error: return jsonify(success=False,message=str(error)),400
    nome,desc,cat,data_enc,local,rm = v['nome'],v['descricao'],v['categoria'],v['data'],v['local'],autor['rm']
    urls = processar_fotos(d.get('fotos') or ([d.get('foto')] if d.get('foto') else []))
    try:
        conn = get_db_connection(); c = conn.cursor()
        c.execute("INSERT INTO itens (nome_item, descricao, categoria, data_encontrado, local_encontrado, foto, fotos_json, status, aprovado, cadastrado_por_aluno, rm_aluno, email_cadastrador) VALUES (%s, %s, %s, %s, %s, %s, %s, 'DISPONÍVEL', FALSE, TRUE, %s, %s);", (nome, desc, cat, data_enc, local, urls[0] if urls else '', json.dumps(urls), rm, autor['email']))
        conn.commit(); c.close(); conn.close()
        return jsonify({"success": True, "message": "Item enviado para moderação!"})
    except Exception as e: logger.exception("Falha de banco/rota | path=%s", request.path); return jsonify({"success": False, "error": "Não foi possível concluir a operação.", "code": "REQUEST_FAILED", "path": request.path}), 500

@app.route('/api/itens/<int:item_id>/aprovar', methods=['OPTIONS', 'PUT'])
@secretaria_required
def apr_item(item_id):
    try:
        conn = get_db_connection(); c = conn.cursor()
        c.execute("UPDATE itens SET aprovado = TRUE WHERE id = %s;", (item_id,))
        conn.commit(); c.close(); conn.close()
        return jsonify({"success": True})
    except Exception as e: logger.exception("Falha de banco/rota | path=%s", request.path); return jsonify({"success": False, "error": "Não foi possível concluir a operação.", "code": "REQUEST_FAILED", "path": request.path}), 500

@app.route('/api/itens', methods=['OPTIONS', 'POST'])
@secretaria_required
@limiter.limit('30 per minute')
def cad_item():
    d = request.get_json(silent=True)
    try:
        v = validar_item(d); validar_categoria(get_db_connection, v['categoria'])
    except ValueError as error: return jsonify(success=False,message=str(error)),400
    nome,desc,cat,data_enc,local,status = (v[k] for k in ['nome','descricao','categoria','data','local','status'])
    urls = processar_fotos(d.get('fotos') or ([d.get('foto')] if d.get('foto') else []))
    try:
        conn = get_db_connection(); c = conn.cursor(cursor_factory=RealDictCursor)
        c.execute("INSERT INTO itens (nome_item, descricao, categoria, data_encontrado, local_encontrado, foto, fotos_json, status, aprovado) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE) RETURNING id;", (nome, desc, cat, data_enc, local, urls[0] if urls else '', json.dumps(urls), status))
        nid = c.fetchone()['id']
        conn.commit()

        # OCR pode identificar RM em carteirinha/caderno; só notifica se RM existir no cadastro.
        ocr_rm = re.sub(r"[^A-Za-z0-9]", "", str(d.get('ocr_rm') or ''))[:20]
        if ocr_rm:
            try:
                c.execute("SELECT nome, rm, email FROM alunos WHERE regexp_replace(COALESCE(rm,''), '[^A-Za-z0-9]', '', 'g') = %s LIMIT 2;", (ocr_rm,))
                candidatos_ocr = c.fetchall()
                aluno_ocr = candidatos_ocr[0] if len(candidatos_ocr) == 1 else None
                if aluno_ocr:
                    msg = f"A secretaria cadastrou um objeto que pode conter seus dados: '{nome or desc}'. Entre no ETEC Achados ou fale com a secretaria para confirmar."
                    c.execute("INSERT INTO mensagens_chat (rm_aluno, nome_aluno, remetente, mensagem, data_envio, email_aluno) VALUES (%s, %s, 'SECRETARIA', %s, %s, %s);",
                              (aluno_ocr.get('rm') or ocr_rm, aluno_ocr.get('nome') or 'Aluno', msg, datetime.now().strftime("%d/%m/%Y %H:%M:%S"), aluno_ocr['email']))
                    if aluno_ocr.get('email'):
                        disparar_email(aluno_ocr['email'], "Possível item identificado - ETEC Achados",
                            f"<div style='font-family:Arial,sans-serif'><h2>Possível item identificado</h2><p>Olá {aluno_ocr.get('nome') or 'aluno'}, a secretaria cadastrou um objeto que pode estar associado aos seus dados: <strong>{nome or desc}</strong>.</p><p>Confirme a identificação com a secretaria.</p></div>")
                    conn.commit()
            except Exception:
                conn.rollback()
                logger.exception("Falha ao notificar aluno por OCR | item_id=%s", nid)

        destinatarios_push = set()
        try:
            termos_n = extrair_termos(f"{nome} {desc}")
            c.execute("SELECT * FROM mural_perdidos WHERE status = 'PROCURANDO' AND categoria = %s;", (cat,))
            for m in c.fetchall():
                if len(termos_n.intersection(extrair_termos(m.get('descricao', '')))) >= 1:
                    if m.get('email_aluno'): destinatarios_push.add(m['email_aluno'].strip().lower())
                    c.execute("INSERT INTO mensagens_chat (rm_aluno, nome_aluno, remetente, mensagem, data_envio, email_aluno) VALUES (%s, %s, 'SECRETARIA', %s, %s, %s);", (m['rm_aluno'], m['nome_aluno'], f"Possível pertence encontrado: '{nome or desc}'. Veja o catálogo!", datetime.now().strftime("%d/%m/%Y %H:%M:%S"), m.get("email_aluno")))
            conn.commit()
        except Exception:
            conn.rollback(); destinatarios_push.clear()
        c.close(); conn.close()
        for destino in destinatarios_push: push_delivery.notificar(destino, 'match')
        return jsonify({"success": True, "id": nid})
    except Exception as e: logger.exception("Falha de banco/rota | path=%s", request.path); return jsonify({"success": False, "error": "Não foi possível concluir a operação.", "code": "REQUEST_FAILED", "path": request.path}), 500

@app.route('/api/itens/<int:item_id>', methods=['OPTIONS', 'PUT', 'POST', 'DELETE'])
@secretaria_required
def gen_item(item_id):
    conn = None
    try:
        conn = get_db_connection(); c = conn.cursor(cursor_factory=RealDictCursor)
        if request.method == 'DELETE' or (request.is_json and request.json and request.json.get('_method') == 'DELETE'):
            c.execute("DELETE FROM entregues WHERE item_id = %s;", (item_id,))
            c.execute("DELETE FROM itens WHERE id = %s;", (item_id,))
            conn.commit(); c.close(); conn.close()
            return jsonify({"success": True})
        else:
            d = request.json or {}
            c.execute("SELECT * FROM itens WHERE id = %s FOR UPDATE;", (item_id,))
            it = c.fetchone()
            if not it: c.close(); conn.close(); return jsonify({"success": False}), 404
            try:
                v = validar_item(d,it); validar_categoria(get_db_connection,v['categoria'])
            except ValueError as error:
                conn.rollback();conn.close(); return jsonify(success=False,message=str(error)),400
            nome,desc,cat,data_enc,local,status = (v[k] for k in ['nome','descricao','categoria','data','local','status'])
            urls = processar_fotos(d['fotos']) if 'fotos' in d and d['fotos'] is not None else None
            c.execute("UPDATE itens SET nome_item=%s, descricao=%s, categoria=%s, data_encontrado=%s, local_encontrado=%s, status=%s, aprovado=TRUE WHERE id=%s;", (nome, desc, cat, data_enc, local, status, item_id))
            if urls is not None:
                c.execute('UPDATE itens SET foto=%s, fotos_json=%s WHERE id=%s;', (urls[0] if urls else '', json.dumps(urls), item_id))
            if status == 'ENTREGUE':
                registrar_entrega(c,item_id,nome,d,it,request.user['email'])
            else:
                cancelar_entregas(c,item_id,request.user['email'])
            conn.commit(); c.close(); conn.close()
            if status != it.get('status'):
                push_delivery.notificar(it.get('email_solicitante'), 'item')
            return jsonify({"success": True})
    except FalhaUploadFotos as error:
        if conn: conn.rollback(); conn.close()
        return jsonify({'success': False, 'message': str(error)}), 502
    except Exception as e: logger.exception("Falha de banco/rota | path=%s", request.path); return jsonify({"success": False, "error": "Não foi possível concluir a operação.", "code": "REQUEST_FAILED", "path": request.path}), 500

@app.route('/api/itens/<int:item_id>/recusar', methods=['OPTIONS', 'PUT', 'DELETE', 'POST'])
@secretaria_required
def rec_item(item_id):
    from services.entrega_service import reverter
    return reverter(get_db_connection,item_id)

@app.route('/api/itens/doacoes/concluir', methods=['OPTIONS', 'DELETE'])
@secretaria_required
def conc_doacoes():
    conn = get_db_connection(); c = conn.cursor()
    c.execute(f"UPDATE itens SET status = 'DOAÇÃO FEITA' WHERE {DOACOES_PENDENTES_SQL} AND aprovado = TRUE;")
    conn.commit(); c.close(); conn.close()
    return jsonify({"success": True})

@app.route('/api/solicitar', methods=['OPTIONS', 'POST'])
@token_required
def sol_item():
    aluno = identidade_aluno()
    if not aluno:
        return jsonify({'success': False, 'message': 'Somente alunos com RM informado podem solicitar a retirada de itens.'}), 403
    d = request.json or {}
    conn = get_db_connection(); c = conn.cursor()
    c.execute("UPDATE itens SET status = 'SOLICITADO', solicitado_por = %s, rm_aluno = %s, email_solicitante = %s WHERE id = %s AND status = 'DISPONÍVEL' AND (aprovado IS NULL OR aprovado = TRUE);", (aluno['nome'], aluno['rm'], aluno['email'], d.get('id')))
    af = c.rowcount; conn.commit(); c.close(); conn.close()
    if af > 0: return jsonify({"success": True})
    return jsonify({"success": False, "message": "Item indisponível."}), 400

# ============================================================
# ROTAS MURAL DE PERDIDOS
# ============================================================
@app.route('/api/mural', methods=['OPTIONS', 'GET', 'POST'])
@consulta_publica
def rotas_mural():
    if request.method == 'OPTIONS': return jsonify({"success": True}), 200
    if request.method == 'GET':
        conn = get_db_connection(); c = conn.cursor(cursor_factory=RealDictCursor)
        c.execute("SELECT * FROM mural_perdidos ORDER BY id DESC;")
        res = c.fetchall(); c.close(); conn.close()
        return jsonify(res if request.user.get('role') == 'secretaria' else [relato_publico(it) for it in res])
    else:
        aluno = identidade_aluno()
        if not aluno:
            return jsonify({'success': False, 'message': 'Somente alunos com RM informado podem publicar relatos de perda.'}), 403
        d = request.json or {}
        conn = get_db_connection(); c = conn.cursor()
        c.execute("INSERT INTO mural_perdidos (nome_aluno, rm_aluno, email_aluno, categoria, descricao, data_registro, status) VALUES (%s, %s, %s, %s, %s, %s, 'PROCURANDO');", (aluno['nome'], aluno['rm'], aluno['email'], d.get('categoria'), d.get('descricao'), datetime.now().strftime("%d/%m/%Y %H:%M")))
        conn.commit(); c.close(); conn.close()
        return jsonify({"success": True})

@app.route('/api/mural/aluno/<string:rm>', methods=['OPTIONS', 'GET'])
@token_required
def mural_al(rm):
    if request.user.get("role") != "secretaria" and rm != str(request.user.get("rm") or ""):
        return jsonify({"success": False, "message": "Acesso negado."}), 403
    conn = get_db_connection(); c = conn.cursor(cursor_factory=RealDictCursor)
    filtro, valor = ("rm_aluno", rm) if request.user.get("role") == "secretaria" else ("email_aluno", request.user.get("email"))
    c.execute(f"SELECT id, categoria, descricao, data_registro as data, status FROM mural_perdidos WHERE {filtro} = %s ORDER BY id DESC;", (valor,))
    res = c.fetchall(); c.close(); conn.close()
    return jsonify(res)

@app.route('/api/mural/<int:id>', methods=['OPTIONS', 'DELETE'])
@secretaria_required
def del_mural(id):
    conn = get_db_connection(); c = conn.cursor()
    c.execute("DELETE FROM mural_perdidos WHERE id = %s;", (id,))
    conn.commit(); c.close(); conn.close()
    return jsonify({"success": True})

# ============================================================
# ROTAS CHAT
# ============================================================
from services import chat_service, chat_retencao
app.before_request(chat_retencao.iniciar)

@app.route('/api/chat/enviar', methods=['POST','OPTIONS'])
@token_required
def env_chat(): return chat_service.enviar(get_db_connection)

@app.route('/api/chat/mensagens/<string:rm>', methods=['GET','OPTIONS'])
@token_required
def get_chat_msgs(rm): return chat_service.mensagens(get_db_connection, rm)

@app.route('/api/chat/legado/<string:rm>', methods=['GET','OPTIONS'])
@secretaria_required
def get_chat_legado(rm): return chat_service.mensagens(get_db_connection, rm, legado=True)

@app.route('/api/chat/conversas', methods=['GET','OPTIONS'])
@secretaria_required
def list_convs(): return chat_service.conversas(get_db_connection)

# ============================================================
# ROTAS RELATÓRIOS & SMART MATCH
# ============================================================
@app.route('/api/entregues', methods=['OPTIONS', 'GET'])
@secretaria_required
def rotas_entregues():
    conn = get_db_connection(); c = conn.cursor(cursor_factory=RealDictCursor)
    c.execute("SELECT * FROM entregues ORDER BY id DESC;" if request.args.get("incluir_canceladas") == "true" else "SELECT * FROM entregues WHERE cancelada_em IS NULL ORDER BY id DESC;")
    res = c.fetchall(); c.close(); conn.close()
    return jsonify(res)

@app.route('/api/estatisticas', methods=['OPTIONS', 'GET'])
@secretaria_required
def rotas_stats():
    verificar_e_atualizar_itens_doacao()
    conn = None
    try:
        conn = get_db_connection(); c = conn.cursor(cursor_factory=RealDictCursor)
        c.execute("SELECT COUNT(*) as total FROM itens WHERE aprovado = TRUE;")
        total_itens = c.fetchone()['total']
        c.execute("SELECT COUNT(*) as total FROM entregues WHERE cancelada_em IS NULL;")
        total_entregues = c.fetchone()['total']
        c.execute(f"SELECT COUNT(*) as total FROM itens WHERE {DOACOES_PENDENTES_SQL} AND aprovado = TRUE;")
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
        logger.exception("Falha de banco/rota | path=%s", request.path); return jsonify({"success": False, "error": "Não foi possível concluir a operação.", "code": "REQUEST_FAILED", "path": request.path}), 500

@app.route('/api/smart-match', methods=['OPTIONS', 'GET'])
@secretaria_required
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
    except Exception as e: logger.exception("Falha de banco/rota | path=%s", request.path); return jsonify({"success": False, "error": "Não foi possível concluir a operação.", "code": "REQUEST_FAILED", "path": request.path}), 500

@app.route('/api/itens/meus', methods=['OPTIONS', 'GET'])
@token_required
def meus_itens():
    email = request.user.get('email')
    if not email:
        return jsonify({'success': False, 'message': 'Sessão sem identidade.'}), 403
    conn = get_db_connection()
    try:
        c = conn.cursor(cursor_factory=RealDictCursor)
        c.execute("""SELECT id, COALESCE(nome_item, descricao) as nome, descricao as txt_descricao,
                     categoria, data_encontrado as txt_data, local_encontrado as txt_local,
                     foto, fotos_json, status FROM itens
                     WHERE email_solicitante = %s AND (aprovado IS NULL OR aprovado = TRUE)
                     ORDER BY id DESC;""", (email,))
        rows = c.fetchall()
        c.close()
        return jsonify([item_publico(item) for item in rows])
    finally:
        conn.close()

# ============================================================
# PONTO DE ENTRADA
# ============================================================
if __name__ == "__main__":
    porta = int(os.environ.get("PORT", PORT))
    print(f"🚀 Servidor ETEC iniciado na porta {porta}")
    app.run(host='0.0.0.0', port=porta)
