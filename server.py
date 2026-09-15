import os
import json
import re
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta
from functools import wraps
from werkzeug.security import check_password_hash
import cloudinary
import cloudinary.uploader
import jwt

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__, static_folder=BASE_DIR, static_url_path='')

ORIGENS_PERMITIDAS = [
    "https://etec-achados.up.railway.app",
    "http://localhost:5000",
    "http://127.0.0.1:5000"
]
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

TENTATIVAS_LOGIN = {}
MAX_TENTATIVAS = 5
TEMPO_BLOQUEIO_MINUTOS = 15

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            parts = request.headers['Authorization'].split()
            if len(parts) == 2 and parts[0] == 'Bearer':
                token = parts[1]
        if not token: return jsonify({"success": False, "message": "Acesso negado: Token ausente."}), 401
        try: jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        except jwt.ExpiredSignatureError: return jsonify({"success": False, "message": "Token expirado."}), 401
        except jwt.InvalidTokenError: return jsonify({"success": False, "message": "Token inválido."}), 401
        return f(*args, **kwargs)
    return decorated

def get_db_connection():
    if not DATABASE_URL: raise ValueError("DATABASE_URL não configurada!")
    return psycopg2.connect(DATABASE_URL, sslmode='require')

STOPWORDS = {'perdi', 'minha', 'meu', 'uma', 'um', 'no', 'na', 'em', 'de', 'da', 'do', 'com', 'sem', 'ontem', 'hoje', 'favor', 'ajuda'}

def extrair_termos(texto):
    if not texto: return set()
    palavras = re.findall(r'[a-zA-Z0-9áéíóúãõâêîôûç]+', texto.lower())
    termos = set()
    for p in palavras:
        if len(p) >= 3 and p not in STOPWORDS:
            if p.endswith('zinha') or p.endswith('zinho'): p = p[:-5]
            elif p.endswith('inha') or p.endswith('inho'): p = p[:-4]
            termos.add(p)
    return termos

def processar_fotos(fotos_array):
    urls_finais = []
    if not fotos_array: return urls_finais
    for foto in fotos_array:
        if foto.startswith('http'): urls_finais.append(foto)
        else:
            try:
                res = cloudinary.uploader.upload(foto, folder="etec_achados")
                urls_finais.append(res["secure_url"])
            except Exception as e: print(e)
    return urls_finais

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS categorias (id SERIAL PRIMARY KEY, nome VARCHAR(50) UNIQUE NOT NULL);')
        cursor.execute("SELECT COUNT(*) FROM categorias;")
        if cursor.fetchone()[0] == 0:
            for c in ['MOCHILA', 'ROUPAS', 'ACESSÓRIOS', 'ESCOLARES', 'ELETRÔNICOS', 'OUTROS']:
                cursor.execute("INSERT INTO categorias (nome) VALUES (%s) ON CONFLICT DO NOTHING;", (c,))
        cursor.execute('''CREATE TABLE IF NOT EXISTS itens (
            id SERIAL PRIMARY KEY, nome_item VARCHAR(150), descricao TEXT NOT NULL, categoria VARCHAR(50) NOT NULL,
            data_encontrado VARCHAR(20) NOT NULL, local_encontrado VARCHAR(100) NOT NULL, foto_base64 TEXT,
            fotos_json TEXT, status VARCHAR(30) DEFAULT 'DISPONÍVEL', solicitado_por VARCHAR(100), rm_aluno VARCHAR(20), prova_propriedade TEXT
        );''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS entregues (
            id SERIAL PRIMARY KEY, item_id INT NOT NULL, nome_item TEXT NOT NULL, retirado_por VARCHAR(100) NOT NULL,
            rm_retirante VARCHAR(30) NOT NULL, turma_curso VARCHAR(50), data_entrega VARCHAR(30) NOT NULL, funcionario_responsavel VARCHAR(100)
        );''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS mural_perdidos (
            id SERIAL PRIMARY KEY, nome_aluno VARCHAR(100) NOT NULL, rm_aluno VARCHAR(20) NOT NULL, categoria VARCHAR(50) NOT NULL,
            descricao TEXT NOT NULL, data_registro VARCHAR(30) NOT NULL, status VARCHAR(30) DEFAULT 'PROCURANDO', item_encontrado_id INT
        );''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS mensagens_chat (
            id SERIAL PRIMARY KEY, rm_aluno VARCHAR(20) NOT NULL, nome_aluno VARCHAR(100) NOT NULL, remetente VARCHAR(20) NOT NULL, 
            mensagem TEXT NOT NULL, data_envio VARCHAR(30) NOT NULL, lida BOOLEAN DEFAULT FALSE
        );''')
        conn.commit(); cursor.close(); conn.close()
    except Exception as e: print(e)

if DATABASE_URL: init_db()

@app.route('/')
def home():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/login', methods=['POST'])
def login():
    ip = request.remote_addr
    agora = datetime.now()
    if ip in TENTATIVAS_LOGIN and TENTATIVAS_LOGIN[ip]['bloqueado_ate'] and agora < TENTATIVAS_LOGIN[ip]['bloqueado_ate']:
        return jsonify({"success": False, "message": "Muitas tentativas."}), 429
    data = request.json or {}
    email, senha = data.get('email', '').strip().lower(), data.get('senha', '').strip()
    if email == EMAIL_SECRETARIA and check_password_hash(SENHA_SECRETARIA_HASH, senha):
        if ip in TENTATIVAS_LOGIN: TENTATIVAS_LOGIN[ip] = {'erros': 0, 'bloqueado_ate': None}
        token = jwt.encode({"user": "secretaria", "exp": datetime.utcnow() + timedelta(hours=4)}, JWT_SECRET, algorithm="HS256")
        return jsonify({"success": True, "token": token})
    if ip not in TENTATIVAS_LOGIN: TENTATIVAS_LOGIN[ip] = {'erros': 0, 'bloqueado_ate': None}
    TENTATIVAS_LOGIN[ip]['erros'] += 1
    if TENTATIVAS_LOGIN[ip]['erros'] >= MAX_TENTATIVAS: TENTATIVAS_LOGIN[ip]['bloqueado_ate'] = agora + timedelta(minutes=TEMPO_BLOQUEIO_MINUTOS)
    return jsonify({"success": False, "message": "Credenciais inválidas"}), 401

@app.route('/api/categorias', methods=['GET'])
def get_categorias():
    conn = get_db_connection(); cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM categorias ORDER BY id ASC;"); res = cursor.fetchall()
    cursor.close(); conn.close(); return jsonify(res)

@app.route('/api/itens', methods=['GET'])
def get_itens():
    conn = get_db_connection(); cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT id, nome_item as nome, descricao as txt_descricao, categoria, data_encontrado as txt_data, local_encontrado as txt_local, foto_base64 as foto, fotos_json, status, solicitado_por, rm_aluno, prova_propriedade FROM itens ORDER BY id DESC;")
    itens = cursor.fetchall()
    for item in itens:
        fotos = []
        if item.get('fotos_json'):
            try: fotos = json.loads(item['fotos_json'])
            except: fotos = []
        if not fotos and item.get('foto'): fotos = [item['foto']]
        item['fotos'] = fotos
    cursor.close(); conn.close(); return jsonify(itens)

# ==========================================
# ROTAS DO MURAL E SOLICITAÇÕES
# ==========================================
@app.route('/api/mural', methods=['GET'])
def get_mural():
    try:
        conn = get_db_connection(); cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM mural_perdidos ORDER BY id DESC LIMIT 50;")
        res = cursor.fetchall(); cursor.close(); conn.close(); return jsonify(res)
    except: return jsonify([])

@app.route('/api/mural', methods=['POST'])
def publicar_mural():
    data = request.json or {}
    nome, rm, cat, desc = data.get('nome'), data.get('rm'), data.get('categoria'), data.get('descricao')
    if not nome or not rm or not desc: return jsonify({"success": False, "message": "Preencha tudo"}), 400
    try:
        agora = datetime.now().strftime("%d/%m/%Y %H:%M")
        conn = get_db_connection(); cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Garante que o status do mural é PROCURANDO
        cursor.execute("INSERT INTO mural_perdidos (nome_aluno, rm_aluno, categoria, descricao, data_registro, status) VALUES (%s, %s, %s, %s, %s, 'PROCURANDO') RETURNING id;", (nome, rm, cat, desc, agora))
        
        # Procura sugestões imediatas
        termos_relato = extrair_termos(desc); matches = []
        cursor.execute("SELECT * FROM itens WHERE status = 'DISPONÍVEL';")
        for it in cursor.fetchall():
            termos_item = extrair_termos(it['nome_item'] + " " + it['descricao'])
            if len(termos_relato.intersection(termos_item)) >= 1 or (cat != 'OUTROS' and it['categoria'] == cat):
                fotos = json.loads(it['fotos_json']) if it.get('fotos_json') else []
                if not fotos and it.get('foto_base64'): fotos = [it['foto_base64']]
                it['fotos'] = fotos; it['foto'] = fotos[0] if fotos else ''
                matches.append(it)
        
        conn.commit(); cursor.close(); conn.close()
        return jsonify({"success": True, "matches_encontrados": matches[:3]})
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/solicitar', methods=['POST'])
def solicitar_item():
    data = request.json or {}
    item_id, nome, rm = data.get('id'), data.get('nome'), data.get('rm')
    if not item_id or not nome or not rm: return jsonify({"success": False, "message": "Faltam dados"}), 400
    try:
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute("UPDATE itens SET status = 'SOLICITADO', solicitado_por = %s, rm_aluno = %s WHERE id = %s;", (nome, rm, item_id))
        # Se solicitou de verdade, muda o status no mural
        cursor.execute("UPDATE mural_perdidos SET status = 'LOCALIZADO' WHERE rm_aluno = %s AND status = 'PROCURANDO';", (rm,))
        conn.commit(); cursor.close(); conn.close()
        return jsonify({"success": True, "message": "Item solicitado!"})
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/mural/notificacoes/<string:rm>', methods=['GET'])
def notificacoes_mural(rm):
    try:
        conn = get_db_connection(); cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM mural_perdidos WHERE rm_aluno = %s AND status = 'PROCURANDO';", (rm,))
        relatos = cursor.fetchall()
        notificacoes = []
        if relatos:
            cursor.execute("SELECT * FROM itens WHERE status = 'DISPONÍVEL';")
            itens = cursor.fetchall()
            for relato in relatos:
                termos_relato = extrair_termos(relato['descricao'])
                for it in itens:
                    termos_item = extrair_termos(it['nome_item'] + " " + it['descricao'])
                    if len(termos_relato.intersection(termos_item)) >= 1 or (relato['categoria'] != 'OUTROS' and it['categoria'] == relato['categoria']):
                        notificacoes.append(it['id'])
        cursor.close(); conn.close()
        return jsonify(list(set(notificacoes)))
    except: return jsonify([])

@app.route('/api/mural/<int:id>', methods=['DELETE'])
@token_required
def deletar_mural(id):
    try:
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute("DELETE FROM mural_perdidos WHERE id = %s;", (id,))
        conn.commit(); cursor.close(); conn.close()
        return jsonify({"success": True})
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

# ==========================================
# ROTAS DO CHAT
# ==========================================
@app.route('/api/chat/enviar', methods=['POST'])
def enviar_mensagem_chat():
    data = request.json or {}
    rm, nome, remetente, mensagem = str(data.get('rm', '')).strip(), data.get('nome', 'Anônimo').strip(), data.get('remetente', 'ALUNO').upper().strip(), data.get('mensagem', '').strip()
    if not rm or not mensagem: return jsonify({"success": False, "message": "Obrigatório"}), 400
    try:
        conn = get_db_connection(); cursor = conn.cursor()
        agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        cursor.execute("INSERT INTO mensagens_chat (rm_aluno, nome_aluno, remetente, mensagem, data_envio) VALUES (%s, %s, %s, %s, %s);", (rm, nome, remetente, mensagem, agora))
        conn.commit(); cursor.close(); conn.close(); return jsonify({"success": True})
    except Exception as e: return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/chat/mensagens/<string:rm>', methods=['GET'])
def buscar_mensagens_aluno(rm):
    try:
        conn = get_db_connection(); cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT id, rm_aluno, nome_aluno, remetente, mensagem, data_envio, lida FROM mensagens_chat WHERE rm_aluno = %s ORDER BY id ASC;", (rm,))
        msgs = cursor.fetchall()
        if request.args.get('marcar_lida', 'false').lower() == 'true' and msgs:
            outro = 'SECRETARIA' if request.args.get('origem', 'ALUNO').upper() == 'ALUNO' else 'ALUNO'
            cursor.execute("UPDATE mensagens_chat SET lida = TRUE WHERE rm_aluno = %s AND remetente = %s AND lida = FALSE;", (rm, outro))
            conn.commit()
        cursor.close(); conn.close(); return jsonify(msgs)
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/chat/conversas', methods=['GET'])
@token_required
def listar_conversas_secretaria():
    try:
        conn = get_db_connection(); cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT rm_aluno, MAX(nome_aluno) as nome_aluno, MAX(data_envio) as ultima_msg_data, COUNT(CASE WHEN remetente = 'ALUNO' AND lida = FALSE THEN 1 END) as nao_lidas FROM mensagens_chat GROUP BY rm_aluno ORDER BY MAX(id) DESC;")
        res = cursor.fetchall(); cursor.close(); conn.close(); return jsonify(res)
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

# ==========================================
# ROTAS PROTEGIDAS PELA SECRETARIA (JWT)
# ==========================================
@app.route('/api/categorias', methods=['POST'])
@token_required
def add_categoria():
    nome = (request.json.get('nome') or '').strip().upper()
    try:
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute("INSERT INTO categorias (nome) VALUES (%s) ON CONFLICT DO NOTHING;", (nome,))
        conn.commit(); cursor.close(); conn.close(); return jsonify({"success": True})
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/itens', methods=['POST'])
@token_required
def cadastrar_item():
    data = request.json or {}
    nome, descricao, categoria = data.get('nome'), data.get('descricao'), data.get('categoria')
    data_enc, local, status = data.get('data'), data.get('local'), data.get('status', 'DISPONÍVEL')
    urls_nuvem = processar_fotos(data.get('fotos', []))
    try:
        conn = get_db_connection(); cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('''INSERT INTO itens (nome_item, descricao, categoria, data_encontrado, local_encontrado, foto_base64, fotos_json, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;''', (nome, descricao, categoria, data_enc, local, urls_nuvem[0] if urls_nuvem else '', json.dumps(urls_nuvem), status))
        novo_id = cursor.fetchone()['id']; conn.commit(); cursor.close(); conn.close()
        return jsonify({"success": True, "id": novo_id})
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/itens/<int:item_id>', methods=['PUT'])
@token_required
def atualizar_item(item_id):
    data = request.json or {}
    nome, descricao, categoria = data.get('nome'), data.get('descricao'), data.get('categoria')
    data_enc, local, status = data.get('data'), data.get('local'), data.get('status', 'DISPONÍVEL')
    try:
        conn = get_db_connection(); cursor = conn.cursor()
        if descricao and data_enc and local:
            fotos = data.get('fotos')
            if fotos is not None and len(fotos) > 0:
                urls = processar_fotos(fotos)
                cursor.execute("UPDATE itens SET nome_item=%s, descricao=%s, categoria=%s, data_encontrado=%s, local_encontrado=%s, foto_base64=%s, fotos_json=%s, status=%s WHERE id=%s;", (nome, descricao, categoria, data_enc, local, urls[0], json.dumps(urls), status, item_id))
            else:
                cursor.execute("UPDATE itens SET nome_item=%s, descricao=%s, categoria=%s, data_encontrado=%s, local_encontrado=%s, status=%s WHERE id=%s;", (nome, descricao, categoria, data_enc, local, status, item_id))
        else:
            cursor.execute("UPDATE itens SET status = %s WHERE id = %s;", (status, item_id))

        if status.upper() == 'ENTREGUE':
            cursor.execute("DELETE FROM entregues WHERE item_id = %s;", (item_id,))
            cursor.execute("INSERT INTO entregues (item_id, nome_item, retirado_por, rm_retirante, turma_curso, data_entrega, funcionario_responsavel) VALUES (%s, %s, %s, %s, %s, %s, %s);", (item_id, (nome or descricao), data.get('retirado_por', ''), data.get('rm_retirante', ''), data.get('turma_curso', '-'), data.get('data_entrega', data_enc), data.get('funcionario_responsavel', 'Secretaria')))
        conn.commit(); cursor.close(); conn.close()
        return jsonify({"success": True})
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/itens/<int:item_id>/recusar', methods=['PUT'])
@token_required
def recusar_solicitacao(item_id):
    try:
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute("UPDATE itens SET status = 'DISPONÍVEL', solicitado_por = NULL, rm_aluno = NULL, prova_propriedade = NULL WHERE id = %s;", (item_id,))
        conn.commit(); cursor.close(); conn.close(); return jsonify({"success": True})
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/itens/<int:item_id>', methods=['DELETE'])
@token_required
def excluir_item(item_id):
    try:
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute("DELETE FROM entregues WHERE item_id = %s;", (item_id,))
        cursor.execute("DELETE FROM itens WHERE id = %s;", (item_id,))
        conn.commit(); cursor.close(); conn.close(); return jsonify({"success": True})
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/itens/doacoes/concluir', methods=['DELETE'])
@token_required
def concluir_doacoes():
    try:
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute("DELETE FROM itens WHERE UPPER(status) = 'DOAÇÃO FEITA' OR UPPER(status) = 'DOACAO FEITA';")
        rem = cursor.rowcount; conn.commit(); cursor.close(); conn.close()
        return jsonify({"success": True, "message": f"{rem} removidos!"})
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/entregues', methods=['GET'])
@token_required
def get_entregues():
    try:
        conn = get_db_connection(); cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM entregues ORDER BY id DESC;")
        res = cursor.fetchall(); cursor.close(); conn.close(); return jsonify(res)
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/estatisticas', methods=['GET'])
@token_required
def obter_estatisticas():
    try:
        conn = get_db_connection(); cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT COUNT(*) as total FROM itens;"); total_itens = cursor.fetchone()['total']
        cursor.execute("SELECT COUNT(*) as total FROM entregues;"); total_entregues = cursor.fetchone()['total']
        cursor.execute("SELECT COUNT(*) as total FROM itens WHERE status LIKE 'DOAÇÃO%';"); total_doacoes = cursor.fetchone()['total']
        cursor.close(); conn.close()
        return jsonify({"success": True, "total_itens": total_itens, "total_entregues": total_entregues, "total_doacoes": total_doacoes})
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
