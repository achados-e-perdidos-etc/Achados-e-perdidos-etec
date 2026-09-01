import os
import json
import random
import time
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import resend
from datetime import datetime

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

DATABASE_URL = os.environ.get("DATABASE_URL")

# Dicionário em memória para guardar códigos OTP temporários
codigos_otp = {}

def get_db_connection():
    if not DATABASE_URL:
        raise ValueError("A variável de ambiente DATABASE_URL não foi configurada!")
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Tabela principal de itens
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

        # Tabela de entregues
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

        # TABELA DE USUÁRIOS/ALUNOS CADASTRADOS
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(100) NOT NULL,
                rm VARCHAR(20) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                data_cadastro VARCHAR(30) NOT NULL,
                ultimo_login VARCHAR(30) NOT NULL
            );
        ''')

        conn.commit()
        cursor.close()
        conn.close()
        print("Tabelas inicializadas com sucesso no Neon PostgreSQL!")
    except Exception as e:
        print(f"Erro ao inicializar o banco de dados: {e}")

if DATABASE_URL:
    init_db()

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

# --- LOGIN E REGISTRO DE USUÁRIOS ---

@app.route('/api/login/enviar-codigo', methods=['POST'])
def enviar_codigo_email():
    data = request.json
    email = (data.get('email') or '').strip().lower()
    nome = (data.get('nome') or '').strip()
    rm = (data.get('rm') or '').strip()

    if not email or not nome or not rm:
        return jsonify({"success": False, "message": "Preencha Nome, RM e E-mail!"}), 400

    codigo = str(random.randint(100000, 999999))
    
    codigos_otp[email] = {
        "codigo": codigo,
        "expira": time.time() + 600,
        "nome": nome,
        "rm": rm
    }

    try:
        if not RESEND_API_KEY:
            print(f"[TESTE SEM KEY] Código para {email}: {codigo}")
            return jsonify({"success": True, "message": f"Modo teste! Seu código é: {codigo}"})

        params = {
            "from": "ETEC Achados <onboarding@resend.dev>",
            "to": [email],
            "subject": "🔑 Seu Código de Acesso - Achados e Perdidos ETEC",
            "html": f"""
                <div style="font-family: Arial, sans-serif; padding: 20px; background-color: #0d1117; color: #ffffff; border-radius: 10px;">
                    <h2 style="color: #f87171;">ETEC Profº José Ignácio Azevedo Filho</h2>
                    <p>Olá, <strong>{nome}</strong>!</p>
                    <p>Seu código de verificação para acessar o portal de Achados e Perdidos é:</p>
                    <div style="background-color: #161b22; border: 1px solid #30363d; padding: 15px; text-align: center; border-radius: 8px; margin: 20px 0;">
                        <span style="font-size: 32px; font-weight: bold; letter-spacing: 5px; color: #38bdf8;">{codigo}</span>
                    </div>
                    <p style="font-size: 12px; color: #8b949e;">Este código expira em 10 minutos. Se você não solicitou este acesso, ignore este e-mail.</p>
                </div>
            """
        }
        resend.Emails.send(params)
        return jsonify({"success": True, "message": "Código enviado para o seu e-mail com sucesso!"})
    except Exception as e:
        print(f"Erro no Resend: {e}")
        return jsonify({"success": False, "message": f"Erro ao enviar e-mail: {str(e)}"}), 500

@app.route('/api/login/verificar-codigo', methods=['POST'])
def verificar_codigo_email():
    data = request.json
    email = (data.get('email') or '').strip().lower()
    codigo_digitado = (data.get('codigo') or '').strip()

    otp_info = codigos_otp.get(email)

    if not otp_info:
        return jsonify({"success": False, "message": "Nenhum código solicitado para este e-mail!"}), 400

    if time.time() > otp_info["expira"]:
        del codigos_otp[email]
        return jsonify({"success": False, "message": "Código expirado! Solicite um novo código."}), 400

    if otp_info["codigo"] == codigo_digitado:
        nome_aluno = otp_info["nome"]
        rm_aluno = otp_info["rm"]
        agora = datetime.now().strftime("%d/%m/%Y %H:%M")

        # SALVA / ATUALIZA NA TABELA 'USUARIOS' DO BANCO DE DADOS
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO usuarios (nome, rm, email, data_cadastro, ultimo_login)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (rm) DO UPDATE 
                SET nome = EXCLUDED.nome, email = EXCLUDED.email, ultimo_login = EXCLUDED.ultimo_login;
            ''', (nome_aluno, rm_aluno, email, agora, agora))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Erro ao registrar usuário no banco: {e}")

        usuario = {
            "nome": nome_aluno,
            "rm": rm_aluno,
            "email": email
        }
        del codigos_otp[email]
        return jsonify({"success": True, "message": "Login realizado com sucesso!", "usuario": usuario})

    return jsonify({"success": False, "message": "Código de verificação incorreto!"}), 400

# --- DEMAIS ROTAS DA API ---

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

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO itens (descricao, categoria, data_encontrado, local_encontrado, foto_base64, fotos_json, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id;
        ''', (descricao, categoria, data_enc, local, foto_capa, fotos_json_str, status))
        novo_id = cursor.fetchone()[0]

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
            data_entrega = data.get('data_entrega', data_enc or '-')
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

        status_atual = (item['status'] or 'DISPONÍVEL').upper()
        if status_atual in ['SOLICITADO', 'ENTREGUE', 'PARA DOAÇÃO', 'DOAÇÃO FEITA']:
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
