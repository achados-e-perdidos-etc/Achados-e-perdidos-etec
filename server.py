import os
import sqlite3
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Tentar obter a URL do Banco PostgreSQL do Neon.tech (Nuvem)
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    """Conecta ao PostgreSQL na nuvem se disponível, senão usa SQLite local."""
    if DATABASE_URL:
        import psycopg2
        # O psycopg2 prefere 'postgres://' ou 'postgresql://'
        url = DATABASE_URL.replace("postgres://", "postgresql://")
        conn = psycopg2.connect(url)
        return conn, "postgres"
    else:
        conn = sqlite3.connect("achados_e_perdidos.db")
        return conn, "sqlite"

def init_db():
    conn, db_type = get_db_connection()
    cursor = conn.cursor()
    
    if db_type == "postgres":
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS itens (
                id SERIAL PRIMARY KEY,
                descricao TEXT NOT NULL,
                categoria TEXT NOT NULL,
                data_encontrado TEXT NOT NULL,
                local_encontrado TEXT NOT NULL,
                foto_base64 TEXT,
                status VARCHAR(50) DEFAULT 'Disponível',
                solicitado_por TEXT,
                rm_aluno TEXT
            );
        ''')
    else:
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
            );
        ''')
        
    conn.commit()
    cursor.close()
    conn.close()

init_db()

@app.route('/')
def home():
    conn_type = "PostgreSQL (Nuvem Permanente)" if DATABASE_URL else "SQLite (Local)"
    return jsonify({
        "status": "API Achados e Perdidos ETEC Funcionando!",
        "banco_de_dados": conn_type,
        "versao": "3.0"
    })

# Rota para buscar todos os itens
@app.route('/api/itens', methods=['GET'])
def get_itens():
    conn, db_type = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, descricao, categoria, data_encontrado, local_encontrado, foto_base64, status, solicitado_por, rm_aluno FROM itens ORDER BY id DESC;")
    rows = cursor.fetchall()
    cursor.close()
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

    conn, db_type = get_db_connection()
    cursor = conn.cursor()
    
    placeholder = "%s" if db_type == "postgres" else "?"
    query = f'''
        INSERT INTO itens (descricao, categoria, data_encontrado, local_encontrado, foto_base64)
        VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
    '''
    cursor.execute(query, (descricao, categoria, data_enc, local, foto))
    conn.commit()
    cursor.close()
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

    conn, db_type = get_db_connection()
    cursor = conn.cursor()
    placeholder = "%s" if db_type == "postgres" else "?"

    if foto:
        query = f'''
            UPDATE itens 
            SET descricao = {placeholder}, categoria = {placeholder}, data_encontrado = {placeholder}, local_encontrado = {placeholder}, foto_base64 = {placeholder}, status = {placeholder}
            WHERE id = {placeholder}
        '''
        cursor.execute(query, (descricao, categoria, data_enc, local, foto, status, item_id))
    else:
        query = f'''
            UPDATE itens 
            SET descricao = {placeholder}, categoria = {placeholder}, data_encontrado = {placeholder}, local_encontrado = {placeholder}, status = {placeholder}
            WHERE id = {placeholder}
        '''
        cursor.execute(query, (descricao, categoria, data_enc, local, status, item_id))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"success": True, "message": "Item atualizado com sucesso!"})

# Rota para EXCLUIR item (DELETE)
@app.route('/api/itens/<int:item_id>', methods=['DELETE'])
def excluir_item(item_id):
    conn, db_type = get_db_connection()
    cursor = conn.cursor()
    placeholder = "%s" if db_type == "postgres" else "?"
    cursor.execute(f"DELETE FROM itens WHERE id = {placeholder}", (item_id,))
    conn.commit()
    cursor.close()
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
        
    conn, db_type = get_db_connection()
    cursor = conn.cursor()
    placeholder = "%s" if db_type == "postgres" else "?"
    query = f'''
        UPDATE itens 
        SET status = 'Solicitado', solicitado_por = {placeholder}, rm_aluno = {placeholder}
        WHERE id = {placeholder}
    '''
    cursor.execute(query, (nome_aluno, rm_aluno, item_id))
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({"success": True, "message": "Solicitação registrada! Compareça à secretaria para retirada."})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)