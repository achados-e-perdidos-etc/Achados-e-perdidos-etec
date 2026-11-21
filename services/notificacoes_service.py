from database import get_db_connection
from utils.notificacoes import EVENTOS
from utils.helpers import validar_email_institucional


def registrar(email, evento):
    if evento not in EVENTOS or not validar_email_institucional(email)[0]:
        return
    conn = get_db_connection()
    try:
        with conn.cursor() as c:
            c.execute('''INSERT INTO notificacoes (email_aluno,evento,titulo,corpo)
                SELECT email,%s,%s,%s FROM alunos WHERE email=%s;''',
                (evento, *EVENTOS[evento], email.strip().lower()))
        conn.commit()
    finally:
        conn.close()
