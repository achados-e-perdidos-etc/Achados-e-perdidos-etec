import os
import json
import re
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

DATABASE_URL = os.environ.get("DATABASE_URL")

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

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
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
        cursor.execute('ALTER TABLE itens ADD COLUMN IF NOT EXISTS fotos_json TEXT;')
        cursor.execute('ALTER TABLE itens ADD COLUMN IF NOT EXISTS solicitado_por VARCHAR(100);')
        cursor.execute('ALTER TABLE itens ADD COLUMN IF NOT EXISTS rm_aluno VARCHAR(20);')

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

        # TABELA DE MENSAGENS DO CHAT
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mensagens_chat (
                id SERIAL PRIMARY KEY,
                rm_aluno VARCHAR(20) NOT NULL,
                nome_aluno VARCHAR(100) NOT NULL,
                remetente VARCHAR(20) NOT NULL, -- 'ALUNO' ou 'SECRETARIA'
                mensagem TEXT NOT NULL,
                data_envio VARCHAR(30) NOT NULL,
                lida BOOLEAN DEFAULT FALSE
            );
        ''')

        cursor.execute('DROP TABLE IF EXISTS usuarios CASCADE;')

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

# ==========================================
# ROTAS DO CHAT (WEB <-> SECRETARIA DESKTOP)
# ==========================================

@app.route('/api/chat/enviar', methods=['POST'])
def enviar_mensagem_chat():
    data = request.json or {}
    rm = str(data.get('rm') or '').strip()
    nome = (data.get('nome') or 'Anônimo').strip()
    remetente = (data.get('remetente') or 'ALUNO').upper().strip()
    mensagem = (data.get('mensagem') or '').strip()

    if not rm or not mensagem:
        return jsonify({"success": False, "message": "RM e Mensagem são obrigatórios!"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        cursor.execute('''
            INSERT INTO mensagens_chat (rm_aluno, nome_aluno, remetente, mensagem, data_envio)
            VALUES (%s, %s, %s, %s, %s);
        ''', (rm, nome, remetente, mensagem, agora))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "Mensagem enviada com sucesso!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/chat/mensagens/<string:rm>', methods=['GET'])
def buscar_mensagens_aluno(rm):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('''
            SELECT id, rm_aluno, nome_aluno, remetente, mensagem, data_envio, lida 
            FROM mensagens_chat 
            WHERE rm_aluno = %s 
            ORDER BY id ASC;
        ''', (rm,))
        msgs = cursor.fetchall()

        # Marca mensagens recebidas como lidas se solicitado
        marcar_lida = request.args.get('marcar_lida', 'false').lower() == 'true'
        origem = request.args.get('origem', 'ALUNO').upper()
        if marcar_lida and msgs:
            outro_remetente = 'SECRETARIA' if origem == 'ALUNO' else 'ALUNO'
            cursor.execute('''
                UPDATE mensagens_chat 
                SET lida = TRUE 
                WHERE rm_aluno = %s AND remetente = %s AND lida = FALSE;
            ''', (rm, outro_remetente))
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
            SELECT 
                rm_aluno, 
                MAX(nome_aluno) as nome_aluno, 
                MAX(data_envio) as ultima_msg_data,
                COUNT(CASE WHEN remetente = 'ALUNO' AND lida = FALSE THEN 1 END) as nao_lidas
            FROM mensagens_chat
            GROUP BY rm_aluno
            ORDER BY MAX(id) DESC;
        ''')
        conversas = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(conversas)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ==========================================
# ROTAS DO SISTEMA PRINCIPAL
# ==========================================

@app.route('/api/itens', methods=['GET'])
def get_itens():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT id, descricao as txt_descricao, categoria, data_encontrado as txt_data, local_encontrado as txt_local, foto_base64 as foto, fotos_json, status, solicitado_por, rm_aluno FROM itens ORDER BY id DESC;")
        itens = cursor.fetchall()
        
        for item in itens:
            fotos = []
            if item.get('fotos_json'):
                try:
                    fotos = json.loads(item['fotos_json'])
                except:
                    fotos = []
            if not fotos and item.get('foto'):
                fotos = [item['foto']]
            item['fotos'] = fotos
            
        cursor.close()
        conn.close()
        return jsonify(itens)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/itens', methods=['POST'])
def cadastrar_item():
    data = request.json or {}
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

    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('''
            INSERT INTO itens (descricao, categoria, data_encontrado, local_encontrado, foto_base64, fotos_json, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id;
        ''', (descricao, categoria, data_enc, local, foto_capa, fotos_json_str, status))
        novo_id = cursor.fetchone()['id']

        cursor.execute("SELECT id, descricao, categoria FROM mural_perdidos WHERE status = 'PROCURANDO';")
        pedidos = cursor.fetchall()

        for p in pedidos:
            mesma_cat = (categoria or '').upper() == (p.get('categoria') or '').upper()
            sim = calcular_similaridade(descricao, p.get('descricao', ''))
            if mesma_cat or sim >= 2:
                cursor.execute('''
                    UPDATE mural_perdidos 
                    SET status = 'LOCALIZADO', item_encontrado_id = %s 
                    WHERE id = %s;
                ''', (novo_id, p['id']))

        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "Objeto salvo com sucesso!", "id": novo_id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/mural', methods=['GET'])
def listar_mural():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM mural_perdidos ORDER BY id DESC;")
        avisos = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(avisos)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/mural', methods=['POST'])
def cadastrar_aviso_mural():
    data = request.json or {}
    nome = (data.get('nome') or '').strip()
    rm = str(data.get('rm') or '').strip()
    categoria = (data.get('categoria') or 'OUTROS').strip()
    descricao = (data.get('descricao') or '').strip()

    if not nome or not rm or not descricao:
        return jsonify({"success": False, "message": "Preencha Nome, RM e Descrição do que perdeu!"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute('''
            SELECT id, descricao as txt_descricao, categoria, data_encontrado as txt_data, local_encontrado as txt_local, foto_base64 as foto, fotos_json, status 
            FROM itens 
            WHERE status = 'DISPONÍVEL';
        ''')
        disponiveis = cursor.fetchall()

        matches = []
        for item in disponiveis:
            sim = calcular_similaridade(descricao, item['txt_descricao'])
            cat_match = categoria != 'OUTROS' and item['categoria'].upper() == categoria.upper()
            if sim >= 1 or cat_match:
                fotos = []
                if item.get('fotos_json'):
                    try:
                        fotos = json.loads(item['fotos_json'])
                    except:
                        fotos = []
                if not fotos and item.get('foto'):
                    fotos = [item['foto']]
                item['fotos'] = fotos
                matches.append(item)

        status_inicial = 'LOCALIZADO' if matches else 'PROCURANDO'
        item_vinculado = matches[0]['id'] if matches else None

        cursor.execute('''
            INSERT INTO mural_perdidos (nome_aluno, rm_aluno, categoria, descricao, data_registro, status, item_encontrado_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id;
        ''', (nome, rm, categoria, descricao, datetime.now().strftime("%d/%m/%Y %H:%M"), status_inicial, item_vinculado))
        
        aviso_id = cursor.fetchone()['id']
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "success": True,
            "aviso_id": aviso_id,
            "matches_encontrados": matches,
            "message": "Aviso registrado no Mural com sucesso!"
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"Erro interno: {str(e)}"}), 500

@app.route('/api/mural/notificacoes/<string:rm>', methods=['GET'])
def checar_notificacoes(rm):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('''
            SELECT m.id as mural_id, m.descricao as pedido_aluno, i.id as item_id, i.descricao as item_nome, i.local_encontrado
            FROM mural_perdidos m
            JOIN itens i ON m.item_encontrado_id = i.id
            WHERE m.rm_aluno = %s AND m.status = 'LOCALIZADO' AND i.status = 'DISPONÍVEL';
        ''', (rm,))
        notificacoes = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(notificacoes)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/solicitar', methods=['POST'])
def solicitar_item():
    data = request.json or {}
    item_id = data.get('id')
    nome = (data.get('nome') or '').strip()
    rm = str(data.get('rm') or '').strip()

    if not item_id or not nome or not rm:
        return jsonify({"success": False, "message": "Nome e RM são obrigatórios!"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("SELECT id, status FROM itens WHERE id = %s;", (item_id,))
        item = cursor.fetchone()

        if not item:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "message": "Item não encontrado no banco de dados."}), 404

        status_atual = (item['status'] or 'DISPONÍVEL').upper()
        if status_atual != 'DISPONÍVEL':
            cursor.close()
            conn.close()
            return jsonify({"success": False, "message": f"Este item não está disponível (Status: {status_atual})."}), 400

        cursor.execute('''
            UPDATE itens 
            SET status = 'SOLICITADO', solicitado_por = %s, rm_aluno = %s
            WHERE id = %s;
        ''', (nome, rm, item_id))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            "success": True, 
            "message": "Solicitação realizada com sucesso! Compareça à secretaria da ETEC para retirar o item."
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"Erro interno: {str(e)}"}), 500

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
                foto_capa = fotos[0]
                fotos_json_str = json.dumps(fotos)
                cursor.execute('''
                    UPDATE itens
                    SET descricao = %s, categoria = %s, data_encontrado = %s, local_encontrado = %s, foto_base64 = %s, fotos_json = %s, status = %s
                    WHERE id = %s;
                ''', (descricao, categoria, data_enc, local, foto_capa, fotos_json_str, status, item_id))
            else:
                cursor.execute('''
                    UPDATE itens
                    SET descricao = %s, categoria = %s, data_encontrado = %s, local_encontrado = %s, status = %s
                    WHERE id = %s;
                ''', (descricao, categoria, data_enc, local, status, item_id))
        else:
            cursor.execute("UPDATE itens SET status = %s WHERE id = %s;", (status, item_id))

        if status.upper() == 'ENTREGUE':
            retirado_por = data.get('retirado_por', 'Não informado')
            rm_retirante = data.get('rm_retirante', 'Não informado')
            turma_curso = data.get('turma_curso', '-')
            data_entrega = data.get('data_entrega', data_enc or datetime.now().strftime("%d/%m/%Y %H:%M"))
            func_resp = data.get('funcionario_responsavel', 'Secretaria')
            
            cursor.execute("DELETE FROM entregues WHERE item_id = %s;", (item_id,))
            cursor.execute('''
                INSERT INTO entregues (item_id, nome_item, retirado_por, rm_retirante, turma_curso, data_entrega, funcionario_responsavel)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
            ''', (item_id, descricao or "Item #" + str(item_id), retirado_por, rm_retirante, turma_curso, data_entrega, func_resp))

        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": f"Item #{item_id} atualizado com sucesso!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/itens/<int:item_id>/recusar', methods=['PUT'])
def recusar_solicitacao(item_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE itens 
            SET status = 'DISPONÍVEL', solicitado_por = NULL, rm_aluno = NULL
            WHERE id = %s;
        ''', (item_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "Solicitação recusada com sucesso!"})
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
        return jsonify({"success": True, "message": f"Item #{item_id} excluído com sucesso!"})
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
        return jsonify({"success": True, "message": f"{removidos} item(ns) doado(s) removidos com sucesso!", "removidos": removidos})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
