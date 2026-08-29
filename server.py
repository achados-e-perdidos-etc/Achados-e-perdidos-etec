import os
import psycopg2
import json
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
        # Garante a tabela básica
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS itens (
                id SERIAL PRIMARY KEY,
                descricao TEXT NOT NULL,
                categoria VARCHAR(50) NOT NULL,
                data_encontrado VARCHAR(20) NOT NULL,
                local_encontrado VARCHAR(100) NOT NULL,
                fotos_json TEXT,
                status VARCHAR(30) DEFAULT 'DISPONÍVEL',
                solicitado_por VARCHAR(100),
                rm_aluno VARCHAR(20)
            );
        ''')
        # Tenta adicionar a coluna fotos_json caso a tabela antiga já exista
        cursor.execute("ALTER TABLE itens ADD COLUMN IF NOT EXISTS fotos_json TEXT;")
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Erro ao inicializar banco: {e}")

if DATABASE_URL:
    init_db()

@app.route('/api/itens', methods=['GET'])
def get_itens():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT id, descricao as txt_descricao, categoria, data_encontrado as txt_data, 
                   local_encontrado as txt_local, fotos_json as fotos, status, 
                   solicitado_por, rm_aluno 
            FROM itens ORDER BY id DESC;
        """)
        itens = cursor.fetchall()
        
        # Converte a string JSON de volta para Lista nos retornos
        for item in itens:
            if item['fotos']:
                try:
                    item['fotos'] = json.loads(item['fotos'])
                except:
                    item['fotos'] = [item['fotos']]
            else:
                item['fotos'] = []
                
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
    fotos = data.get('fotos', [])
    status = data.get('status', 'DISPONÍVEL')

    if not descricao or not data_enc or not local:
        return jsonify({"success": False, "message": "Preencha todos os campos!"}), 400

    fotos_json = json.dumps(fotos)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO itens (descricao, categoria, data_encontrado, local_encontrado, fotos_json, status)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;
        ''', (descricao, categoria, data_enc, local, fotos_json, status))
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
    fotos = data.get('fotos')
    status = data.get('status', 'DISPONÍVEL')

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if fotos is not None and len(fotos) > 0:
            fotos_json = json.dumps(fotos)
            cursor.execute('''
                UPDATE itens
                SET descricao = %s, categoria = %s, data_encontrado = %s, local_encontrado = %s, fotos_json = %s, status = %s
                WHERE id = %s;
            ''', (descricao, categoria, data_enc, local, fotos_json, status, item_id))
        else:
            cursor.execute('''
                UPDATE itens
                SET descricao = %s, categoria = %s, data_encontrado = %s, local_encontrado = %s, status = %s
                WHERE id = %s;
            ''', (descricao, categoria, data_enc, local, status, item_id))

        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": f"Item #{item_id} atualizado!"})
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
        return jsonify({"success": True, "message": "Item removido!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/itens/doacoes/concluir', methods=['DELETE'])
def concluir_doacoes():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM itens WHERE UPPER(status) IN ('DOAÇÃO FEITA', 'DOACAO FEITA');")
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
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT status FROM itens WHERE id = %s;", (item_id,))
        item = cursor.fetchone()

        if not item or (item['status'] or '').upper() != 'DISPONÍVEL':
            cursor.close()
            conn.close()
            return jsonify({"success": False, "message": "Item indisponível!"}), 400

        cursor.execute('''
            UPDATE itens SET status = 'SOLICITADO', solicitado_por = %s, rm_aluno = %s WHERE id = %s;
        ''', (nome_aluno, rm_aluno, item_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "Solicitação registrada!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
