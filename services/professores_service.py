"""Solicitações e decisões persistidas; nenhum privilégio vem do navegador."""
from psycopg2.extras import RealDictCursor
from database import get_db_connection

def buscar_acesso(email):
    conn = get_db_connection()
    try:
        c = conn.cursor(cursor_factory=RealDictCursor)
        c.execute('SELECT p.* FROM professores_acesso p JOIN alunos a ON a.email = p.email WHERE p.email = %s;', (email,))
        return c.fetchone()
    finally:
        conn.close()

def solicitar_acesso(email):
    conn = get_db_connection()
    try:
        c = conn.cursor(cursor_factory=RealDictCursor)
        c.execute("""INSERT INTO professores_acesso (email, nome)
            SELECT email, nome FROM alunos WHERE email = %s
            ON CONFLICT (email) DO UPDATE SET nome = EXCLUDED.nome,
                status = 'PENDENTE', data_solicitacao = CURRENT_TIMESTAMP,
                data_decisao = NULL, decidido_por = NULL
            WHERE professores_acesso.status IN ('RECUSADO', 'REVOGADO');""", (email,))
        c.execute('SELECT * FROM professores_acesso WHERE email = %s;', (email,))
        result = c.fetchone()
        conn.commit()
        return result
    finally:
        conn.close()

def listar_acessos():
    conn = get_db_connection()
    try:
        c = conn.cursor(cursor_factory=RealDictCursor)
        c.execute('SELECT * FROM professores_acesso ORDER BY data_solicitacao DESC, email;')
        return c.fetchall()
    finally:
        conn.close()

def decidir_acesso(email, acao, responsavel):
    origem, destino = {'APROVAR': ('PENDENTE', 'APROVADO'),
                       'RECUSAR': ('PENDENTE', 'RECUSADO'),
                       'REVOGAR': ('APROVADO', 'REVOGADO')}[acao]
    conn = get_db_connection()
    try:
        c = conn.cursor(cursor_factory=RealDictCursor)
        c.execute("""UPDATE professores_acesso SET status = %s,
                     data_decisao = CURRENT_TIMESTAMP, decidido_por = %s
                     WHERE email = %s AND status = %s RETURNING *;""",
                  (destino, responsavel, email, origem))
        result = c.fetchone()
        conn.commit()
        return result
    finally:
        conn.close()
