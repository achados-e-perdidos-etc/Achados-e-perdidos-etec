"""Correspondências aproximadas: avisos deduplicados, sem atribuir propriedade."""
import json
import logging
import os
import threading
from psycopg2.extras import RealDictCursor
from database import get_db_connection
from utils.smart_match import calcular_smart_match
from utils.helpers import extrair_termos
from utils.notificacoes import EVENTOS

_lock=threading.Lock()
_thread=None


def processar(conectar=None,limite=10):
    conectar=conectar or get_db_connection
    quantidade=0
    for _ in range(limite):
        conn=conectar()
        try:
            c=conn.cursor(cursor_factory=RealDictCursor)
            c.execute('SELECT item_id FROM matches_pendentes ORDER BY item_id FOR UPDATE SKIP LOCKED LIMIT 1')
            job=c.fetchone()
            if not job:return quantidade
            c.execute("SELECT *,nome_item AS nome FROM itens WHERE id=%s AND aprovado IS TRUE AND status='DISPONÍVEL'",(job['item_id'],))
            item=c.fetchone()
            if item:
                c.execute("""SELECT m.* FROM mural_perdidos m JOIN alunos a ON a.email=m.email_aluno
                    WHERE m.status='PROCURANDO' AND m.categoria=%s ORDER BY m.id""",(item['categoria'],))
                for relato in c.fetchall():
                    comuns=extrair_termos(relato['descricao']).intersection(extrair_termos((item.get('nome') or '')+' '+(item.get('descricao') or '')))
                    score,_=calcular_smart_match(relato,item)
                    # Categoria/cor isoladas não bastam para disparar alertas.
                    cores={'azul','verde','preto','preta','branco','branca','vermelho','vermelha','rosa','cinza','amarelo','amarela','marrom','roxo','roxa','laranja'}
                    if score<60 or not (comuns-cores):continue
                    c.execute('''INSERT INTO matches_avisados(item_id,relato_id,email) VALUES(%s,%s,%s)
                     ON CONFLICT DO NOTHING RETURNING item_id''',(item['id'],relato['id'],relato['email_aluno']))
                    if not c.fetchone():continue
                    c.execute('INSERT INTO notificacoes(email_aluno,evento,titulo,corpo) VALUES(%s,%s,%s,%s)',
                      (relato['email_aluno'],'match',*EVENTOS['match']))
                    from services.push_delivery import configuracao
                    if configuracao():
                        payload=json.dumps({'title':EVENTOS['match'][0],'body':EVENTOS['match'][1],'url':'/'})
                        c.execute('''INSERT INTO push_entregas(email_aluno,endpoint_hash,subscription_json,payload_json)
                         SELECT email_aluno,endpoint_hash,subscription_json,%s FROM push_dispositivos WHERE email_aluno=%s''',
                         (payload,relato['email_aluno']))
                    quantidade+=1
            c.execute('DELETE FROM matches_pendentes WHERE item_id=%s',(job['item_id'],));conn.commit()
        except Exception:
            conn.rollback();raise
        finally:conn.close()
    return quantidade


def _executar():
    while True:
        try:processar()
        except Exception:logging.getLogger(__name__).warning('Correspondências serão tentadas novamente.')
        threading.Event().wait(60)


def iniciar():
    from flask import current_app
    if current_app.testing or not os.environ.get('DATABASE_URL') or not current_app.config.get('MATCHES_AUTOSTART',True):return
    global _thread
    with _lock:
        if _thread is None or not _thread.is_alive():
            _thread=threading.Thread(target=_executar,name='matches-etec',daemon=True);_thread.start()
