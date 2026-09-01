import os
import json
import psycopg2
import requests
import random
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

DATABASE_URL = os.environ.get("DATABASE_URL")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")

codigos_verificacao = {}

def get_db_connection():
    if not DATABASE_URL:
        raise ValueError("A variável de ambiente DATABASE_URL não foi configurada!")
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Tabela principal de Itens
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

        # Tabela de Entregues / Histórico
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

        # NOVA: Tabela de Usuários (Alunos)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(100) NOT NULL,
                rm VARCHAR(20) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')

        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Erro ao inicializar o banco de dados: {e}")

if DATABASE_URL:
    init_db()

def verificar_vencimento_doacoes():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT id, data_encontrado FROM itens WHERE status = 'DISPONÍVEL';")
        itens = cursor.fetchall()
        hoje = datetime.now()
        itens_atualizados = 0

        for item in itens:
            try:
                data_item = datetime.strptime(item['data_encontrado'], "%d/%m/%Y")
                if (hoje - data_item).days >= 90:
                    cursor.execute("UPDATE itens SET status = 'PARA DOAÇÃO' WHERE id = %s", (item['id'],))
                    itens_atualizados += 1
            except ValueError:
                pass 

        if itens_atualizados > 0:
            conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[ERRO CRÍTICO] Falha na automação: {e}")

# =======================================================
# INTEGRAÇÃO RESEND.COM E AUTENTICAÇÃO
# =======================================================
def enviar_email_resend(destinatario, assunto, corpo_html):
    if not RESEND_API_KEY:
        print("[ERRO] RESEND_API_KEY não configurada no Render.")
        return False
    
    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        # ATENÇÃO: Se não tiver domínio próprio verificado na Resend, 
        # mantenha este email padrão do onboarding.
        "from": "Achados e Perdidos ETEC <onboarding@resend.dev>",
        "to": destinatario,
        "subject": assunto,
        "html": corpo_html
    }
    
    try:
        response = requests.post("https://api.resend.com/emails", json=payload, headers=headers)
        if response.status_code in [200, 201, 202]:
            return True
        else:
            print(f"[ERRO RESEND] {response.text}")
            return False
    except Exception as e:
        print(f"[ERRO REQUISIÇÃO RESEND] {e}")
        return False

@app.route('/api/auth/codigo', methods=['POST'])
def gerar_codigo():
    data = request.json
    nome = data.get('nome')
    email = data.get('email')

    if not email or not email.endswith('@aluno.cps.sp.gov.br'):
        return jsonify({"success": False, "message": "E-mail institucional inválido."}), 400

    codigo_gerado = str(random.randint(100000, 999999))
    codigos_verificacao[email] = codigo_gerado

    assunto = "Código de Acesso - Achados e Perdidos ETEC"
    corpo_html = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
        <h2>Olá, {nome}.</h2>
        <p>Seu código de verificação para acessar o sistema de Achados e Perdidos é:</p>
        <h1 style="background: #f4f4f4; padding: 15px; border-radius: 8px; letter-spacing: 5px; display: inline-block;">{codigo_gerado}</h1>
        <p>Se você não solicitou este acesso, desconsidere este e-mail.</p>
    </div>
    """

    enviado = enviar_email_resend(email, assunto, corpo_html)

    if enviado:
        return jsonify({"success": True, "message": "Código enviado para seu e-mail."})
    else:
        return jsonify({"success": False, "message": "Falha na API de e-mail. Contate a secretaria."}), 500

@app.route('/api/auth/validar', methods=['POST'])
def validar_codigo():
    data = request.json
    email = data.get('email')
    codigo_digitado = data.get('codigo')
    nome = data.get('nome') 
    rm = data.get('rm')     

    codigo_salvo = codigos_verificacao.get(email)

    if codigo_salvo and str(codigo_salvo) == str(codigo_digitado):
        del codigos_verificacao[email]
        
        # O código está certo! Agora gravamos ou atualizamos o usuário no Banco de Dados
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT id FROM usuarios WHERE email = %s;", (email,))
            usuario_existe = cursor.fetchone()
            
            if not usuario_existe:
                # Se for a primeira vez acessando, cadastra na tabela
                cursor.execute(
                    "INSERT INTO usuarios (nome, rm, email) VALUES (%s, %s, %s) ON CONFLICT (rm) DO NOTHING;", 
                    (nome, rm, email)
                )
                conn.commit()
                
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"[ERRO BANCO DE DADOS - USUÁRIOS] {e}")

        return jsonify({"success": True, "message": "Login validado com sucesso!"})
    else:
        return jsonify({"success": False, "message": "Código incorreto ou expirado."}), 401

# =======================================================
# ROTAS DO CATÁLOGO E SECRETARIA
# =======================================================
@app.route('/api/itens', methods=['GET'])
def get_itens():
    verificar_vencimento_doacoes() 
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
            data_entrega = data.get('data_entrega', data_enc)
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
    nome = data.get('nome')
    rm = data.get('rm')
    email = data.get('email') 

    if not item_id or not nome or not rm:
        return jsonify({"success": False, "message": "Dados incompletos!"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE itens 
            SET status = 'SOLICITADO', solicitado_por = %s, rm_aluno = %s
            WHERE id = %s AND status = 'DISPONÍVEL';
        ''', (nome, rm, item_id))

        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "message": "O item não está mais disponível para solicitação."}), 400

        conn.commit()
        cursor.close()
        conn.close()

        if email:
            assunto_solicitacao = "Confirmação de Solicitação - Achados e Perdidos ETEC"
            corpo_html = f"<p>Sua solicitação para o item #{item_id} foi registrada com sucesso!<br>Compareça à Secretaria.</p>"
            enviar_email_resend(email, assunto_solicitacao, corpo_html)

        return jsonify({
            "success": True, 
            "message": "Solicitação realizada! Verifique seu e-mail institucional para ver o horário de atendimento."
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
