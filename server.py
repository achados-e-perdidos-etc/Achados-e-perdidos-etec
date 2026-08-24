import os
import sqlite3
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DB_NAME = "achados_e_perdidos.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS itens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao TEXT NOT NULL,
            categoria TEXT NOT NULL,
            data_encontrado TEXT NOT NULL,
            local_encontrado TEXT NOT NULL,
            foto_base64 TEXT,
            status TEXT DEFAULT 'Disponível',
            solicitado_por TEXT,
            rm_aluno TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return jsonify({"status": "API Achados e Perdidos ETEC Funcionando!", "versao": "2.0"})

# Rota para buscar todos os itens
@app.route('/api/itens', methods=['GET'])
def get_itens():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, descricao, categoria, data_encontrado, local_encontrado, foto_base64, status, solicitado_por, rm_aluno FROM itens ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    
    itens = []
    for row in rows:
        itens.append({
            "id": row[0],
            "txt_descricao": row[1],
            "categoria": row[2],
            "txt_data": row[3],
            "txt_local": row[4],
            "foto": row[5] or "",
            "status": row[6],
            "solicitado_por": row[7] or "",
            "rm_aluno": row[8] or ""
        })
    return jsonify(itens)

# Rota para cadastrar item (POST)
@app.route('/api/itens', methods=['POST'])
def cadastrar_item():
    data = request.json
    descricao = data.get('descricao')
    categoria = data.get('categoria')
    data_enc = data.get('data')
    local = data.get('local')
    foto = data.get('foto', '')

    if not descricao or not data_enc or not local:
        return jsonify({"success": False, "message": "Preencha todos os campos obrigatórios!"}), 400

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO itens (descricao, categoria, data_encontrado, local_encontrado, foto_base64)
        VALUES (?, ?, ?, ?, ?)
    ''', (descricao, categoria, data_enc, local, foto))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "Objeto cadastrado com sucesso!"})

# Rota para EDITAR item existente (PUT)
@app.route('/api/itens/<int:item_id>', methods=['PUT'])
def editar_item(item_id):
    data = request.json
    descricao = data.get('descricao')
    categoria = data.get('categoria')
    data_enc = data.get('data')
    local = data.get('local')
    foto = data.get('foto')
    status = data.get('status', 'Disponível')

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    if foto:
        cursor.execute('''
            UPDATE itens 
            SET descricao = ?, categoria = ?, data_encontrado = ?, local_encontrado = ?, foto_base64 = ?, status = ?
            WHERE id = ?
        ''', (descricao, categoria, data_enc, local, foto, status, item_id))
    else:
        cursor.execute('''
            UPDATE itens 
            SET descricao = ?, categoria = ?, data_encontrado = ?, local_encontrado = ?, status = ?
            WHERE id = ?
        ''', (descricao, categoria, data_enc, local, status, item_id))

    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "Item atualizado com sucesso!"})

# Rota para EXCLUIR item (DELETE)
@app.route('/api/itens/<int:item_id>', methods=['DELETE'])
def excluir_item(item_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM itens WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "Item excluído com sucesso!"})

# Rota para o Aluno solicitar coleta
@app.route('/api/solicitar', methods=['POST'])
def solicitar_item():
    data = request.json
    item_id = data.get('id')
    nome_aluno = data.get('nome')
    rm_aluno = data.get('rm')
    
    if not item_id or not nome_aluno or not rm_aluno:
        return jsonify({"success": False, "message": "Dados incompletos do aluno!"}), 400
        
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE itens 
        SET status = 'Solicitado', solicitado_por = ?, rm_aluno = ?
        WHERE id = ?
    ''', (nome_aluno, rm_aluno, item_id))
    conn.commit()
    conn.close()
    
    return jsonify({"success": True, "message": "Solicitação registrada! Compareça à secretaria para retirada."})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)