import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    if not DATABASE_URL:
        raise ValueError("A variável de ambiente DATABASE_URL não foi configurada!")
    return psycopg2.connect(DATABASE_URL, sslmode='require')

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
                status VARCHAR(30) DEFAULT 'GUARDADO',
                solicitado_por VARCHAR(100),
                rm_aluno VARCHAR(20)
            );
        ''')
        conn.commit()
        cursor.close()
        conn.close()
        print("Tabela inicializada no Neon PostgreSQL!")
    except Exception as e:
        print(f"Erro ao inicializar o banco de dados: {e}")

if DATABASE_URL:
    init_db()

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "banco": "Neon PostgreSQL",
        "mensagem": "API Achados e Perdidos ETEC Ativa"
    })

@app.route('/api/itens', methods=['GET'])
def get_itens():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT id, descricao as txt_descricao, categoria, data_encontrado as txt_data, local_encontrado as txt_local, foto_base64 as foto, status, solicitado_por, rm_aluno FROM itens ORDER BY id DESC;")
        itens = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(itens)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/itens', methods=['POST'])
def cadastrar_item():
    data = request.json
    descricao = data.get('descricao')
    categoria = data.get('categoria')
    data_enc = data.get('data')
    local = data.get('local')
    foto = data.get('foto', '')
    status = data.get('status', 'GUARDADO')

    if not descricao or not data_enc or not local:
        return jsonify({"success": False, "message": "Preencha todos os campos obrigatórios!"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO itens (descricao, categoria, data_encontrado, local_encontrado, foto_base64, status)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;
        ''', (descricao, categoria, data_enc, local, foto, status))
        novo_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "Objeto salvo com sucesso!", "id": novo_id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/itens/<int:item_id>', methods=['PUT'])
def atualizar_item(item_id):
    data = request.json
    descricao = data.get('descricao')
    categoria = data.get('categoria')
    data_enc = data.get('data')
    local = data.get('local')
    foto = data.get('foto')
    status = data.get('status', 'GUARDADO')

    if not descricao or not data_enc or not local:
        return jsonify({"success": False, "message": "Preencha todos os campos obrigatórios!"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if foto:
            cursor.execute('''
                UPDATE itens
                SET descricao = %s, categoria = %s, data_encontrado = %s, local_encontrado = %s, foto_base64 = %s, status = %s
                WHERE id = %s;
            ''', (descricao, categoria, data_enc, local, foto, status, item_id))
        else:
            cursor.execute('''
                UPDATE itens
                SET descricao = %s, categoria = %s, data_encontrado = %s, local_encontrado = %s, status = %s
                WHERE id = %s;
            ''', (descricao, categoria, data_enc, local, status, item_id))

        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": f"Item #{item_id} atualizado com sucesso!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/itens/<int:item_id>', methods=['DELETE'])
def excluir_item(item_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM itens WHERE id = %s;", (item_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": f"Item #{item_id} excluído com sucesso!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/solicitar', methods=['POST'])
def solicitar_item():
    data = request.json
    item_id = data.get('id')
    nome_aluno = data.get('nome')
    rm_aluno = data.get('rm')
    
    if not item_id or not nome_aluno or not rm_aluno:
        return jsonify({"success": False, "message": "Dados incompletos do aluno!"}), 400
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("SELECT status FROM itens WHERE id = %s;", (item_id,))
        item = cursor.fetchone()

        if not item:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "message": "Item não encontrado!"}), 404

        status_atual = (item['status'] or 'GUARDADO').upper()
        if status_atual in ['SOLICITADO', 'ENTREGUE']:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "message": "Este item não está disponível para solicitação!"}), 400

        cursor.execute('''
            UPDATE itens 
            SET status = 'SOLICITADO', solicitado_por = %s, rm_aluno = %s
            WHERE id = %s;
        ''', (nome_aluno, rm_aluno, item_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "Solicitação registrada! Compareça à secretaria para retirada."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
