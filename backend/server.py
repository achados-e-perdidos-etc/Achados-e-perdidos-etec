import os
import json
import re
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime

# Importação do Cloudinary
import cloudinary
import cloudinary.uploader

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

DATABASE_URL = os.environ.get("DATABASE_URL")

# Configuração do Cloudinary usando Variáveis de Ambiente
cloudinary.config( 
  cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME"), 
  api_key = os.environ.get("CLOUDINARY_API_KEY"), 
  api_secret = os.environ.get("CLOUDINARY_API_SECRET"),
  secure = True
)

def get_db_connection():
    if not DATABASE_URL:
        raise ValueError("A variável de ambiente DATABASE_URL não foi configurada!")
    return psycopg2.connect(DATABASE_URL, sslmode='require')

STOPWORDS = {
    'perdi', 'minha', 'meu', 'meus', 'minhas', 'uma', 'um', 'uns', 'umas',
    'no', 'na', 'nos', 'nas', 'em', 'de', 'da', 'do', 'das', 'dos', 'por',
    'para', 'com', 'sem', 'ontem', 'hoje', 'favor', 'ajuda', 'acho', 'que'
}

def extrair_termos(texto):
    if not texto:
        return set()
    palavras = re.findall(r'[a-zA-Z0-9áéíóúãõâêîôûç]+', texto.lower())
    termos = set()
    for p in palavras:
        if len(p) >= 3 and p not in STOPWORDS:
            if p.endswith('zinha') or p.endswith('zinho'):
                p = p[:-5]
            elif p.endswith('inha') or p.endswith('inho'):
                p = p[:-4]
            termos.add(p)
    return termos

def calcular_similaridade(texto1, texto2):
    t1 = extrair_termos(texto1)
    t2 = extrair_termos(texto2)
    if not t1 or not t2:
        return 0
    return len(t1.intersection(t2))

# ==========================================
# MOTOR DE UPLOAD (CLOUDINARY)
# ==========================================
def processar_fotos(fotos_array):
    """
    Recebe um array com Base64 ou URLs.
    Envia o que for Base64 para o Cloudinary e retorna uma lista limpa só com URLs.
    """
    urls_finais = []
    if not fotos_array:
        return urls_finais

    for foto in fotos_array:
        if foto.startswith('http'):
            # Já é uma URL hospedada, mantém intacta
            urls_finais.append(foto)
        else:
            try:
                # É um Base64 novo, faz o upload para a nuvem
                resposta = cloudinary.uploader.upload(foto, folder="etec_achados")
                urls_finais.append(resposta["secure_url"])
            except Exception as e:
                print(f"Erro no upload do Cloudinary: {e}")
    return urls_finais

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categorias (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(50) UNIQUE NOT NULL
            );
        ''')
        
        cursor.execute("SELECT COUNT(*) FROM categorias;")
        if cursor.fetchone()[0] == 0:
            default_cats = ['MOCHILA', 'ROUPAS', 'ACESSÓRIOS', 'ESCOLARES', 'ELETRÔNICOS', 'OUTROS']
            for c in default_cats:
                cursor.execute("INSERT INTO categorias (nome) VALUES (%s) ON CONFLICT DO NOTHING;", (c,))

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS itens (
                id SERIAL PRIMARY KEY,
                nome_item VARCHAR(150),
                descricao TEXT NOT NULL,
                categoria VARCHAR(50) NOT NULL,
                data_encontrado VARCHAR(20) NOT NULL,
                local_encontrado VARCHAR(100) NOT NULL,
                foto_base64 TEXT,
                fotos_json TEXT,
                status VARCHAR(30) DEFAULT 'DISPONÍVEL',
                solicitado_por VARCHAR(100),
                rm_aluno VARCHAR(20),
                prova_propriedade TEXT
            );
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS entregues (
                id SERIAL PRIMARY KEY,
                item_id INT NOT NULL,
                nome_item TEXT NOT NULL,
                retirado_por VARCHAR(100) NOT NULL,
                rm_retirante VARCHAR(30) NOT NULL,
                turma_curso VARCHAR(50),
                data_entrega VARCHAR(30) NOT NULL,
                funcionario_responsavel VARCHAR(100)
            );
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mural_perdidos (
                id SERIAL PRIMARY KEY,
                nome_aluno VARCHAR(100) NOT NULL,
                rm_aluno VARCHAR(20) NOT NULL,
                categoria VARCHAR(50) NOT NULL,
                descricao TEXT NOT NULL,
                data_registro VARCHAR(30) NOT NULL,
                status VARCHAR(30) DEFAULT 'PROCURANDO',
                item_encontrado_id INT
            );
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mensagens_chat (
                id SERIAL PRIMARY KEY,
                rm_aluno VARCHAR(20) NOT NULL,
                nome_aluno VARCHAR(100) NOT NULL,
                remetente VARCHAR(20) NOT NULL, 
                mensagem TEXT NOT NULL,
                data_envio VARCHAR(30) NOT NULL,
                lida BOOLEAN DEFAULT FALSE
            );
        ''')

        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Erro ao inicializar o banco de dados: {e}")

if DATABASE_URL:
    init_db()

@app.route('/')
def home():
    return send_from_directory('../frontend', 'index.html')

@app.route('/api/categorias', methods=['GET'])
def get_categorias():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM categorias ORDER BY id ASC;")
        categorias = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(categorias)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/categorias', methods=['POST'])
def add_categoria():
    data = request.json or {}
    nome = (data.get('nome') or '').strip().upper()
    if not nome: return jsonify({"success": False, "message": "Nome inválido"}), 400
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO categorias (nome) VALUES (%s) ON CONFLICT DO NOTHING;", (nome,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/chat/enviar', methods=['POST'])
def enviar_mensagem_chat():
    data = request.json or {}
    rm, nome, remetente, mensagem = str(data.get('rm', '')).strip(), data.get('nome', 'Anônimo').strip(), data.get('remetente', 'ALUNO').upper().strip(), data.get('mensagem', '').strip()
    if not rm or not mensagem: return jsonify({"success": False, "message": "Obrigatório"}), 400
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        cursor.execute("INSERT INTO mensagens_chat (rm_aluno, nome_aluno, remetente, mensagem, data_envio) VALUES (%s, %s, %s, %s, %s);", (rm, nome, remetente, mensagem, agora))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/chat/mensagens/<string:rm>', methods=['GET'])
def buscar_mensagens_aluno(rm):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT id, rm_aluno, nome_aluno, remetente, mensagem, data_envio, lida FROM mensagens_chat WHERE rm_aluno = %s ORDER BY id ASC;", (rm,))
        msgs = cursor.fetchall()

        marcar_lida, origem = request.args.get('marcar_lida', 'false').lower() == 'true', request.args.get('origem', 'ALUNO').upper()
        if marcar_lida and msgs:
            outro = 'SECRETARIA' if origem == 'ALUNO' else 'ALUNO'
            cursor.execute("UPDATE mensagens_chat SET lida = TRUE WHERE rm_aluno = %s AND remetente = %s AND lida = FALSE;", (rm, outro))
            conn.commit()
        cursor.close()
        conn.close()
        return jsonify(msgs)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/chat/conversas', methods=['GET'])
def listar_conversas_secretaria():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('''
            SELECT rm_aluno, MAX(nome_aluno) as nome_aluno, MAX(data_envio) as ultima_msg_data,
                   COUNT(CASE WHEN remetente = 'ALUNO' AND lida = FALSE THEN 1 END) as nao_lidas
            FROM mensagens_chat GROUP BY rm_aluno ORDER BY MAX(id) DESC;
        ''')
        conversas = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(conversas)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/itens', methods=['GET'])
def get_itens():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT id, nome_item as nome, descricao as txt_descricao, categoria, data_encontrado as txt_data, local_encontrado as txt_local, foto_base64 as foto, fotos_json, status, solicitado_por, rm_aluno, prova_propriedade FROM itens ORDER BY id DESC;")
        itens = cursor.fetchall()
        for item in itens:
            fotos = []
            if item.get('fotos_json'):
                try: fotos = json.loads(item['fotos_json'])
                except: fotos = []
            if not fotos and item.get('foto'): fotos = [item['foto']]
            item['fotos'] = fotos
        cursor.close()
        conn.close()
        return jsonify(itens)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/itens', methods=['POST'])
def cadastrar_item():
    data = request.json or {}
    nome, descricao, categoria = data.get('nome'), data.get('descricao'), data.get('categoria')
    data_enc, local, status = data.get('data'), data.get('local'), data.get('status', 'DISPONÍVEL')
    fotos_base64_brutas = data.get('fotos', [])

    if not nome or not descricao or not data_enc or not local: 
        return jsonify({"success": False, "message": "Preencha todos os campos obrigatórios!"}), 400

    # Processa as imagens mandando para a nuvem
    urls_nuvem = processar_fotos(fotos_base64_brutas)
    
    foto_capa = urls_nuvem[0] if len(urls_nuvem) > 0 else ''
    fotos_json_str = json.dumps(urls_nuvem)

    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('''
            INSERT INTO itens (nome_item, descricao, categoria, data_encontrado, local_encontrado, foto_base64, fotos_json, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
        ''', (nome, descricao, categoria, data_enc, local, foto_capa, fotos_json_str, status))
        novo_id = cursor.fetchone()['id']
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "Objeto salvo com sucesso na nuvem!", "id": novo_id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/entregues', methods=['GET'])
def get_entregues():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM entregues ORDER BY id DESC;")
        entregues = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(entregues)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/estatisticas', methods=['GET'])
def obter_estatisticas():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("SELECT COUNT(*) as total FROM itens;")
        total_itens = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) as total FROM entregues;")
        total_entregues = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) as total FROM itens WHERE status LIKE 'DOAÇÃO%';")
        total_doacoes = cursor.fetchone()['total']

        cursor.close()
        conn.close()

        return jsonify({
            "success": True,
            "total_itens": total_itens,
            "total_entregues": total_entregues,
            "total_doacoes": total_doacoes
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/itens/<int:item_id>', methods=['PUT'])
def atualizar_item(item_id):
    data = request.json or {}
    nome, descricao, categoria = data.get('nome'), data.get('descricao'), data.get('categoria')
    data_enc, local, status = data.get('data'), data.get('local'), data.get('status', 'DISPONÍVEL')
    fotos_recebidas = data.get('fotos')

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if descricao and data_enc and local:
            if fotos_recebidas is not None and len(fotos_recebidas) > 0:
                # Se houver fotos no payload, processa para garantir que tudo seja URL
                urls_nuvem = processar_fotos(fotos_recebidas)
                cursor.execute(
                    "UPDATE itens SET nome_item = %s, descricao = %s, categoria = %s, data_encontrado = %s, local_encontrado = %s, foto_base64 = %s, fotos_json = %s, status = %s WHERE id = %s;", 
                    (nome, descricao, categoria, data_enc, local, urls_nuvem[0], json.dumps(urls_nuvem), status, item_id)
                )
            else:
                cursor.execute(
                    "UPDATE itens SET nome_item = %s, descricao = %s, categoria = %s, data_encontrado = %s, local_encontrado = %s, status = %s WHERE id = %s;", 
                    (nome, descricao, categoria, data_enc, local, status, item_id)
                )
        else:
            # Caso seja apenas uma atualização rápida de status (recusar, aprovar)
            cursor.execute("UPDATE itens SET status = %s WHERE id = %s;", (status, item_id))

        if status.upper() == 'ENTREGUE':
            retirado_por, rm_retirante = data.get('retirado_por', 'Não informado'), data.get('rm_retirante', 'Não informado')
            turma_curso, data_entrega = data.get('turma_curso', '-'), data.get('data_entrega', data_enc or datetime.now().strftime("%d/%m/%Y %H:%M"))
            func_resp = data.get('funcionario_responsavel', 'Secretaria')
            cursor.execute("DELETE FROM entregues WHERE item_id = %s;", (item_id,))
            cursor.execute("INSERT INTO entregues (item_id, nome_item, retirado_por, rm_retirante, turma_curso, data_entrega, funcionario_responsavel) VALUES (%s, %s, %s, %s, %s, %s, %s);", (item_id, (nome or descricao or "Item #" + str(item_id)), retirado_por, rm_retirante, turma_curso, data_entrega, func_resp))

        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": f"Item #{item_id} atualizado!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/itens/<int:item_id>/recusar', methods=['PUT'])
def recusar_solicitacao(item_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE itens SET status = 'DISPONÍVEL', solicitado_por = NULL, rm_aluno = NULL, prova_propriedade = NULL WHERE id = %s;", (item_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "Solicitação recusada."})
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/itens/<int:item_id>', methods=['DELETE'])
def excluir_item(item_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM entregues WHERE item_id = %s;", (item_id,))
        cursor.execute("DELETE FROM itens WHERE id = %s;", (item_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": f"Item #{item_id} excluído!"})
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/itens/doacoes/concluir', methods=['DELETE'])
def concluir_doacoes():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM itens WHERE UPPER(status) = 'DOAÇÃO FEITA' OR UPPER(status) = 'DOACAO FEITA';")
        removidos = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": f"{removidos} item(ns) removidos!"})
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
