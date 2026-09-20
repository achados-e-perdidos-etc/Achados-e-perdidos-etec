"""
Camada de Acesso a Dados (PostgreSQL)
Conexão resiliente, inicialização de esquemas e rotinas de manutenção.
"""
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from config import DATABASE_URL
from utils.helpers import calcular_dias_passados

ULTIMA_VERIFICACAO_DOACOES = None

def get_db_connection():
    """
    Retorna uma nova conexão ativa com o banco PostgreSQL.
    """
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL não configurada no ambiente.")
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def verificar_e_atualizar_itens_doacao(forcar=False):
    """
    Regra de Negócio (Art. 1.233 do Código Civil e Deliberações ETEC):
    Itens em custódia por 90 dias ou mais sem reivindicação são alterados
    automaticamente para o status 'PARA DOAÇÃO'.
    Possui limitação de taxa (máximo uma execução por hora em chamadas normais).
    """
    global ULTIMA_VERIFICACAO_DOACOES
    agora = datetime.now()
    if not forcar and ULTIMA_VERIFICACAO_DOACOES and (agora - ULTIMA_VERIFICACAO_DOACOES).total_seconds() < 3600:
        return
    ULTIMA_VERIFICACAO_DOACOES = agora

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT id, data_encontrado FROM itens WHERE UPPER(status) = 'DISPONÍVEL';")
        itens = cursor.fetchall()
        ids_para_doacao = []
        for item in itens:
            dias = calcular_dias_passados(item.get('data_encontrado'))
            if dias >= 90:
                ids_para_doacao.append(item['id'])
        
        if ids_para_doacao:
            cursor.execute("UPDATE itens SET status = 'PARA DOAÇÃO' WHERE id = ANY(%s);", (ids_para_doacao,))
            conn.commit()
            print(f"[Doações 90 Dias] {len(ids_para_doacao)} item(ns) atualizado(s) para 'PARA DOAÇÃO'.")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[Doações 90 Dias] Aviso ao verificar itens de doação: {e}")
        if conn:
            conn.close()

def init_db():
    """
    Inicializa todas as tabelas e colunas necessárias no PostgreSQL,
    incluindo migrações idempotentes e categorias padrão.
    """
    if not DATABASE_URL:
        print("[DB Init] DATABASE_URL não definida. Pulando inicialização automática.")
        return

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Categorias de Itens
        cursor.execute('CREATE TABLE IF NOT EXISTS categorias (id SERIAL PRIMARY KEY, nome VARCHAR(50) UNIQUE NOT NULL);')

        # Itens Catalogados
        cursor.execute('''CREATE TABLE IF NOT EXISTS itens (
            id SERIAL PRIMARY KEY, 
            nome_item VARCHAR(150), 
            descricao TEXT NOT NULL, 
            categoria VARCHAR(50) NOT NULL, 
            data_encontrado VARCHAR(20) NOT NULL, 
            local_encontrado VARCHAR(100) NOT NULL, 
            foto TEXT, 
            fotos_json TEXT, 
            status VARCHAR(30) DEFAULT 'DISPONÍVEL', 
            solicitado_por VARCHAR(100), 
            rm_aluno VARCHAR(20), 
            email_solicitante VARCHAR(150), 
            aprovado BOOLEAN DEFAULT TRUE, 
            cadastrado_por_aluno BOOLEAN DEFAULT FALSE
        );''')

        # Migrações seguras
        colunas_migracao = [
            ("nome_item", "VARCHAR(150)"),
            ("foto", "TEXT"),
            ("fotos_json", "TEXT"),
            ("status", "VARCHAR(30) DEFAULT 'DISPONÍVEL'"),
            ("solicitado_por", "VARCHAR(100)"),
            ("rm_aluno", "VARCHAR(20)"),
            ("email_solicitante", "VARCHAR(150)"),
            ("aprovado", "BOOLEAN DEFAULT TRUE"),
            ("cadastrado_por_aluno", "BOOLEAN DEFAULT FALSE")
        ]
        for col_nome, col_tipo in colunas_migracao:
            try:
                cursor.execute(f"ALTER TABLE itens ADD COLUMN IF NOT EXISTS {col_nome} {col_tipo};")
                conn.commit()
            except Exception:
                conn.rollback()

        try:
            cursor.execute("UPDATE itens SET aprovado = TRUE WHERE aprovado IS NULL;")
            conn.commit()
        except Exception:
            conn.rollback()

        try:
            cursor.execute("SELECT setval(pg_get_serial_sequence('itens', 'id'), COALESCE((SELECT MAX(id) FROM itens), 1));")
            conn.commit()
        except Exception:
            conn.rollback()

        # Histórico de Entregas e Comprovantes
        cursor.execute('''CREATE TABLE IF NOT EXISTS entregues (
            id SERIAL PRIMARY KEY, 
            item_id INT NOT NULL, 
            nome_item TEXT NOT NULL, 
            retirado_por VARCHAR(100) NOT NULL, 
            rm_retirante VARCHAR(30) NOT NULL, 
            turma_curso VARCHAR(50), 
            data_entrega VARCHAR(30) NOT NULL, 
            funcionario_responsavel VARCHAR(100)
        );''')

        # Mural de Relatos de Perda dos Alunos
        cursor.execute('''CREATE TABLE IF NOT EXISTS mural_perdidos (
            id SERIAL PRIMARY KEY, 
            nome_aluno VARCHAR(100) NOT NULL, 
            rm_aluno VARCHAR(20) NOT NULL, 
            email_aluno VARCHAR(150), 
            categoria VARCHAR(50) NOT NULL, 
            descricao TEXT NOT NULL, 
            data_registro VARCHAR(30) NOT NULL, 
            status VARCHAR(30) DEFAULT 'PROCURANDO'
        );''')

        # Mensagens do Chat Multi-Aluno
        cursor.execute('''CREATE TABLE IF NOT EXISTS mensagens_chat (
            id SERIAL PRIMARY KEY, 
            rm_aluno VARCHAR(20) NOT NULL, 
            nome_aluno VARCHAR(100) NOT NULL, 
            remetente VARCHAR(20) NOT NULL, 
            mensagem TEXT NOT NULL, 
            data_envio VARCHAR(30) NOT NULL, 
            lida BOOLEAN DEFAULT FALSE
        );''')

        # Contas de Alunos
        cursor.execute('''CREATE TABLE IF NOT EXISTS alunos (
            email VARCHAR(150) PRIMARY KEY, 
            nome VARCHAR(100) NOT NULL, 
            rm VARCHAR(20) NOT NULL, 
            senha_hash TEXT NOT NULL
        );''')

        # Códigos Temporários de Verificação (2FA / Redefinição)
        cursor.execute('''CREATE TABLE IF NOT EXISTS codigos_auth (
            email VARCHAR(150) PRIMARY KEY, 
            codigo VARCHAR(6) NOT NULL, 
            expiracao TIMESTAMP NOT NULL
        );''')

        # Assinaturas Push
        cursor.execute('''CREATE TABLE IF NOT EXISTS push_subscriptions (
            id SERIAL PRIMARY KEY, 
            rm_aluno VARCHAR(20) UNIQUE NOT NULL, 
            subscription_json TEXT NOT NULL
        );''')

        # Seed de Categorias Básicas
        cursor.execute("SELECT COUNT(*) FROM categorias;")
        if cursor.fetchone()[0] == 0:
            for c in ['MOCHILA', 'ROUPAS', 'ACESSÓRIOS', 'ESCOLARES', 'ELETRÔNICOS', 'OUTROS']:
                cursor.execute("INSERT INTO categorias (nome) VALUES (%s) ON CONFLICT DO NOTHING;", (c,))

        conn.commit()
        cursor.close()
        conn.close()
        verificar_e_atualizar_itens_doacao(forcar=True)
        print("[DB Init] Banco de dados inicializado com sucesso.")
    except Exception as e:
        print(f"[DB Init] Erro na inicialização: {e}")
