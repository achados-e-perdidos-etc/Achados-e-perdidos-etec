import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Obtém a URL de Conexão do Neon PostgreSQL a partir das variáveis de ambiente
# Formato padrão Neon: postgresql://usuario:senha@ep-xyz.us-east-2.aws.neon.tech/neondb?sslmode=require
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    if not DATABASE_URL:
        raise ValueError("A variável de ambiente DATABASE_URL não foi configurada!")
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    return conn

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
                status VARCHAR(30) DEFAULT 'Disponível',
                solicitado_por VARCHAR(100),
                rm_aluno VARCHAR(20)
            );
        ''')
        conn.commit()
        cursor.close()
        conn.close()
        print("Tabela inicializada com sucesso no Neon PostgreSQL!")
    except Exception as e:
        print(f"Erro ao inicializar o banco de dados Neon: {e}")

# Executa criação da tabela ao iniciar
if DATABASE_URL:
    init_db()

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "banco": "Neon PostgreSQL",
        "mensagem": "API Achados e Perdidos ETEC Ativa"
    })

# Rota para listar todos os itens salvos no Neon
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

# Rota para cadastrar novo objeto (Secretaria)
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

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO itens (descricao, categoria, data_encontrado, local_encontrado, foto_base64)
            VALUES (%s, %s, %s, %s, %s) RETURNING id;
        ''', (descricao, categoria, data_enc, local, foto))
        novo_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "Objeto salvo no Neon PostgreSQL com sucesso!", "id": novo_id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Rota para solicitar retirada do item (Aluno Web)
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
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE itens 
            SET status = 'Solicitado', solicitado_por = %s, rm_aluno = %s
            WHERE id = %s;
        ''', (nome_aluno, rm_aluno, item_id))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "message": "Solicitação gravada no banco! Compareça à secretaria para retirada."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)