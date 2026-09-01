import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

DATABASE_URL = os.environ.get("DATABASE_URL")

# --- LÓGICA DE INTELIGÊNCIA (MATCHING) ---
def extrair_palavras_chave(texto):
    stop_words = {'o', 'a', 'os', 'as', 'um', 'uma', 'uns', 'umas', 'de', 'do', 'da', 'dos', 'das', 'em', 'no', 'na', 'nos', 'nas', 'por', 'para', 'com', 'meu', 'minha', 'meus', 'minhas', 'perdi', 'ontem', 'hoje', 'escola', 'etec', 'laboratorio', 'sala', 'pátio', 'patio', 'cantina', 'frente', 'atras'}
    # Remove pontuações e divide as palavras
    palavras = texto.lower().replace(',', '').replace('.', '').split()
    # Filtra palavras pequenas e stop words
    return set([p for p in palavras if p not in stop_words and len(p) > 2])

def verificar_match(desc1, desc2):
    kw1 = extrair_palavras_chave(desc1)
    kw2 = extrair_palavras_chave(desc2)
    # Se houver pelo menos 1 palavra-chave igual e relevante, consideramos um "Match"
    return len(kw1.intersection(kw2)) > 0

def get_db_connection():
    if not DATABASE_URL:
        raise ValueError("A variável de ambiente DATABASE_URL não foi configurada!")
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # TABELA DE ITENS
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS itens (
                id SERIAL PRIMARY KEY,
                descricao TEXT NOT NULL,
                categoria VARCHAR(50) NOT NULL,
                data_encontrado VARCHAR(20) NOT NULL,
                local_encontrado VARCHAR(100) NOT NULL,
                foto_base64 TEXT,
                fotos_json TEXT,
                status VARCHAR(30) DEFAULT 'DISPONÍVEL',
                solicitado_por VARCHAR(100),
                rm_aluno VARCHAR(20)
            );
        ''')

        # TABELA DE ENTREGUES
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

        # TABELA DE USUÁRIOS
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(100) NOT NULL,
                rm VARCHAR(20) UNIQUE NOT NULL,
                data_cadastro VARCHAR(30) NOT NULL,
                ultimo_login VARCHAR(30) NOT NULL
            );
        ''')

        # TABELA DE MURAL DE AVISOS (PROCURO ALGO)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS avisos (
                id SERIAL PRIMARY KEY,
                rm_aluno VARCHAR(20) NOT NULL,
                nome_aluno VARCHAR(100) NOT NULL,
                descricao TEXT NOT NULL,
                categoria VARCHAR(50) NOT NULL,
                data_aviso VARCHAR(30) NOT NULL,
                status VARCHAR(30) DEFAULT 'BUSCANDO'
            );
        ''')

        # TABELA DE NOTIFICAÇÕES (PARA O ALUNO)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notificacoes (
                id SERIAL PRIMARY KEY,
                rm_aluno VARCHAR(20) NOT NULL,
                titulo VARCHAR(100) NOT NULL,
                mensagem TEXT NOT NULL,
                lida BOOLEAN DEFAULT FALSE,
                data_criacao VARCHAR(30) NOT NULL
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
    return send_from_directory('.', 'index.html')

# --- ROTAS DE IDENTIFICAÇÃO (SEM SENHA) ---
@app.route('/api/usuario/identificar', methods=['POST'])
def identificar_usuario():
    data = request.json
    nome = (data.get('nome') or '').strip()
    rm = (data.get('rm') or '').strip()
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")

    if not nome or not rm:
        return jsonify({"success": False, "message": "Preencha Nome e RM!"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO usuarios (nome, rm, data_cadastro, ultimo_login)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (rm) DO UPDATE 
            SET nome = EXCLUDED.nome, ultimo_login = EXCLUDED.ultimo_login;
        ''', (nome, rm, agora, agora))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "usuario": {"nome": nome, "rm": rm}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# --- ROTAS DO MURAL E NOTIFICAÇÕES ---
@app.route('/api/avisos', methods=['GET'])
def get_avisos():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM avisos ORDER BY id DESC;")
        avisos = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(avisos)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/avisos', methods=['POST'])
def cadastrar_aviso():
    data = request.json
    nome = data.get('nome')
    rm = data.get('rm')
    descricao = data.get('descricao')
    categoria = data.get('categoria')
    agora = datetime.now().strftime("%d/%m/%Y")

    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # 1. Salva o aviso no banco
        cursor.execute('''
            INSERT INTO avisos (rm_aluno, nome_aluno, descricao, categoria, data_aviso)
            VALUES (%s, %s, %s, %s, %s) RETURNING id;
        ''', (rm, nome, descricao, categoria, agora))
        
        # 2. MATCH IMEDIATO: Verifica se a secretaria já tem um item parecido!
        cursor.execute("SELECT * FROM itens WHERE status = 'DISPONÍVEL' AND categoria = %s;", (categoria,))
        itens_disponiveis = cursor.fetchall()
        
        matches = []
        for item in itens_disponiveis:
            if verificar_match(descricao, item['descricao']):
                # Ajusta fotos para o frontend
                item['fotos'] = json.loads(item['fotos_json']) if item.get('fotos_json') else ([item['foto_base64']] if item.get('foto_base64') else [])
                matches.append(item)

        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "Aviso publicado no mural!", "matches_encontrados": matches})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/avisos/<int:aviso_id>', methods=['DELETE'])
def excluir_aviso(aviso_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM avisos WHERE id = %s;", (aviso_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/notificacoes/<string:rm>', methods=['GET'])
def get_notificacoes(rm):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM notificacoes WHERE rm_aluno = %s AND lida = FALSE ORDER BY id DESC;", (rm,))
        notificacoes = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(notificacoes)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/notificacoes/<int:id_notificacao>/ler', methods=['PUT'])
def ler_notificacao(id_notificacao):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE notificacoes SET lida = TRUE WHERE id = %s;", (id_notificacao,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# --- ROTAS DE ITENS (CATÁLOGO) ---
@app.route('/api/itens', methods=['GET'])
def get_itens():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT id, descricao as txt_descricao, categoria, data_encontrado as txt_data, local_encontrado as txt_local, foto_base64 as foto, fotos_json, status, solicitado_por, rm_aluno FROM itens ORDER BY id DESC;")
        itens = cursor.fetchall()
        for item in itens:
            fotos = json.loads(item['fotos_json']) if item.get('fotos_json') else []
            if not fotos and item.get('foto'): fotos = [item['foto']]
            item['fotos'] = fotos
        cursor.close()
        conn.close()
        return jsonify(itens)
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

@app.route('/api/itens', methods=['POST'])
def cadastrar_item():
    data = request.json
    descricao = data.get('descricao')
    categoria = data.get('categoria')
    data_enc = data.get('data')
    local = data.get('local')
    fotos = data.get('fotos', [])
    status = data.get('status', 'DISPONÍVEL')

    if not descricao or not data_enc or not local:
        return jsonify({"success": False, "message": "Preencha todos os campos obrigatórios!"}), 400

    foto_capa = fotos[0] if len(fotos) > 0 else ''
    fotos_json_str = json.dumps(fotos)
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")

    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('''
            INSERT INTO itens (descricao, categoria, data_encontrado, local_encontrado, foto_base64, fotos_json, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id;
        ''', (descricao, categoria, data_enc, local, foto_capa, fotos_json_str, status))
        novo_id = cursor.fetchone()['id']

        # MATCH REVERSO: Avisar alunos que estão procurando algo parecido!
        if status == 'DISPONÍVEL':
            cursor.execute("SELECT * FROM avisos WHERE status = 'BUSCANDO' AND categoria = %s;", (categoria,))
            avisos = cursor.fetchall()
            for aviso in avisos:
                if verificar_match(descricao, aviso['descricao']):
                    cursor.execute('''
                        INSERT INTO notificacoes (rm_aluno, titulo, mensagem, data_criacao)
                        VALUES (%s, %s, %s, %s);
                    ''', (aviso['rm_aluno'], "Encontramos algo parecido!", f"A secretaria acabou de cadastrar um item parecido com o seu aviso: '{descricao}'. Verifique o catálogo!", agora))

        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "Objeto salvo com sucesso!", "id": novo_id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/itens/localizar/<int:item_id>', methods=['GET'])
def localizar_item(item_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT id, descricao as txt_descricao, categoria, data_encontrado as txt_data, local_encontrado as txt_local, status, solicitado_por, rm_aluno FROM itens WHERE id = %s;", (item_id,))
        item = cursor.fetchone()

        if not item:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "message": "Item não encontrado!"}), 404

        if (item['status'] or '').upper() == 'ENTREGUE':
            cursor.execute("SELECT retirado_por, rm_retirante, turma_curso, data_entrega, funcionario_responsavel FROM entregues WHERE item_id = %s ORDER BY id DESC LIMIT 1;", (item_id,))
            dados_entrega = cursor.fetchone()
            if dados_entrega:
                item['entrega'] = dados_entrega

        cursor.close()
        conn.close()
        return jsonify({"success": True, "item": item})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/itens/<int:item_id>', methods=['PUT'])
def atualizar_item(item_id):
    data = request.json
    descricao = data.get('descricao')
    categoria = data.get('categoria')
    data_enc = data.get('data')
    local = data.get('local')
    fotos = data.get('fotos')
    status = data.get('status', 'DISPONÍVEL')

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if descricao and data_enc and local:
            if fotos is not None and len(fotos) > 0:
                cursor.execute('UPDATE itens SET descricao = %s, categoria = %s, data_encontrado = %s, local_encontrado = %s, foto_base64 = %s, fotos_json = %s, status = %s WHERE id = %s;', (descricao, categoria, data_enc, local, fotos[0], json.dumps(fotos), status, item_id))
            else:
                cursor.execute('UPDATE itens SET descricao = %s, categoria = %s, data_encontrado = %s, local_encontrado = %s, status = %s WHERE id = %s;', (descricao, categoria, data_enc, local, status, item_id))
        else:
            cursor.execute("UPDATE itens SET status = %s WHERE id = %s;", (status, item_id))

        if status.upper() == 'ENTREGUE':
            cursor.execute("DELETE FROM entregues WHERE item_id = %s;", (item_id,))
            cursor.execute('''
                INSERT INTO entregues (item_id, nome_item, retirado_por, rm_retirante, turma_curso, data_entrega, funcionario_responsavel)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
            ''', (item_id, descricao or "Item", data.get('retirado_por', ''), data.get('rm_retirante', ''), data.get('turma_curso', '-'), data.get('data_entrega', data_enc), data.get('funcionario_responsavel', 'Secretaria')))

        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/itens/<int:item_id>/recusar', methods=['PUT'])
def recusar_solicitacao(item_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE itens SET status = 'DISPONÍVEL', solicitado_por = NULL, rm_aluno = NULL WHERE id = %s;", (item_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

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
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

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
        return jsonify({"success": True, "removidos": removidos})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/solicitar', methods=['POST'])
def solicitar_item():
    data = request.json
    item_id = data.get('id')
    nome_aluno = data.get('nome')
    rm_aluno = data.get('rm')
    
    if not item_id or not nome_aluno or not rm_aluno:
        return jsonify({"success": False, "message": "Dados incompletos!"}), 400
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("UPDATE itens SET status = 'SOLICITADO', solicitado_por = %s, rm_aluno = %s WHERE id = %s AND status = 'DISPONÍVEL';", (nome_aluno, rm_aluno, item_id))
        
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "message": "O item não está mais disponível para solicitação."}), 400

        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "Solicitação registrada! Compareça à secretaria para retirada."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
