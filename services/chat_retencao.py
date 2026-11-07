"""Retenção de 30 dias, limpeza limitada por lote e coordenação entre workers."""
import logging
import os
import threading
from database import get_db_connection

logger = logging.getLogger(__name__)
FILTRO_RECENTE = "criada_em >= CURRENT_TIMESTAMP - INTERVAL '30 days'"
_lock = threading.Lock()
_thread = None


def limpar_expiradas(conectar=None, limite=500, lotes=20):
    conectar = conectar or get_db_connection
    removidas = 0
    for _ in range(lotes):
        conn = conectar()
        try:
            c = conn.cursor()
            c.execute('SELECT pg_try_advisory_xact_lock(281030001);')
            if not c.fetchone()[0]: return removidas
            c.execute('''DELETE FROM mensagens_chat WHERE id IN
                (SELECT id FROM mensagens_chat WHERE criada_em < CURRENT_TIMESTAMP - INTERVAL '30 days'
                 ORDER BY criada_em,id FOR UPDATE SKIP LOCKED LIMIT %s);''', (limite,))
            quantidade = c.rowcount
            conn.commit()
            removidas += quantidade
            if quantidade < limite: return removidas
        except Exception:
            conn.rollback()
            raise
        finally: conn.close()
    return removidas


def _executar():
    while True:
        atraso = 3600
        try:
            if limpar_expiradas() >= 10000: atraso = 60
            conn = get_db_connection()
            try:
                c=conn.cursor();c.execute("DELETE FROM uploads_fotos WHERE atualizado_em<CURRENT_TIMESTAMP-INTERVAL '24 hours'");conn.commit()
            finally:conn.close()
        except Exception:
            logger.warning('Limpeza do chat temporariamente indisponível; será tentada novamente.')
            atraso = 60
        threading.Event().wait(atraso)


def iniciar():
    """Após inicialização das tabelas, retomada automática no primeiro acesso."""
    from flask import current_app
    if current_app.testing or not current_app.config.get('CHAT_RETENTION_AUTOSTART', True) or not os.environ.get('DATABASE_URL'):
        return
    global _thread
    with _lock:
        if _thread is None or not _thread.is_alive():
            _thread = threading.Thread(target=_executar,daemon=True,name='retencao-chat')
            _thread.start()
