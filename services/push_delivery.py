"""Emissor Web Push: fila persistida por dispositivo e envio fora das rotas."""
import base64
import json
import logging
import os
import threading
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from urllib.parse import urlsplit

from psycopg2.extras import RealDictCursor
from database import get_db_connection
from utils.helpers import validar_email_institucional
from utils.push import validar_assinatura, validar_endpoint

logger = logging.getLogger(__name__)
EVENTOS = {
    'chat': ('Nova mensagem da secretaria', 'Abra o portal para ver a resposta da secretaria.'),
    'item': ('Atualização do seu pedido', 'Há uma atualização sobre seu item. Confira no portal.'),
    'match': ('Um objeto pode ter sido encontrado', 'Há um objeto parecido com seu relato. Confira o catálogo.'),
    'teste': ('Notificações ativadas', 'Este é um teste das notificações do ETEC Achados e Perdidos.')
}
_sinal = threading.Event()
_lock = threading.Lock()
_thread = None


@lru_cache(maxsize=4)
def _configurar(privada, publica, contato):
    if not privada or not publica or not contato.startswith('mailto:') or '@' not in contato or any(c.isspace() for c in contato):
        return None
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        if 'BEGIN' in privada:
            chave = serialization.load_pem_private_key(privada.replace('\\n', '\n').encode(), password=None)
        else:
            raw = base64.urlsafe_b64decode(privada + '=' * (-len(privada) % 4))
            chave = ec.derive_private_key(int.from_bytes(raw, 'big'), ec.SECP256R1()) if len(raw) == 32 else serialization.load_der_private_key(raw, password=None)
        if not isinstance(chave, ec.EllipticCurvePrivateKey) or chave.curve.name != 'secp256r1':
            return None
        point = chave.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
        esperada = base64.urlsafe_b64encode(point).decode().rstrip('=')
        if esperada != publica.rstrip('='):
            return None
        return chave, esperada, contato
    except Exception:
        return None


def configuracao():
    return _configurar(os.environ.get('VAPID_PRIVATE_KEY', '').strip(), os.environ.get('VAPID_PUBLIC_KEY', '').strip(),
                       os.environ.get('VAPID_CLAIMS_EMAIL', 'mailto:achadoseperdidosetec@gmail.com').strip())


def chave_publica():
    config = configuracao()
    return config[1] if config else ''


def destino_permitido(endpoint):
    """O emissor não funciona como cliente HTTP para URLs arbitrárias/redirects."""
    validar_endpoint(endpoint)
    host = urlsplit(endpoint).hostname.lower()
    return (host in {'fcm.googleapis.com', 'android.googleapis.com', 'updates.push.services.mozilla.com', 'web.push.apple.com'}
            or host.endswith('.push.services.mozilla.com') or host.endswith('.notify.windows.com'))


def enfileirar(email, evento, *, iniciar=True):
    if evento not in EVENTOS or not validar_email_institucional(email)[0] or not configuracao():
        return 0
    email = email.strip().lower()
    title, body = EVENTOS[evento]
    payload = json.dumps({'title': title, 'body': body, 'url': '/', 'icon': '/icon-192.png'}, ensure_ascii=False)
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute('''INSERT INTO push_entregas (email_aluno, endpoint_hash, subscription_json, payload_json)
            SELECT p.email_aluno, p.endpoint_hash, p.subscription_json, %s FROM push_dispositivos p
            JOIN alunos a ON a.email = p.email_aluno WHERE p.email_aluno = %s;''', (payload, email))
        quantidade = c.rowcount
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    if quantidade and iniciar:
        acordar_worker()
    return quantidade


def notificar(email, evento):
    """Falha de notificação não transforma uma gravação já concluída em erro."""
    try:
        from services.notificacoes_service import registrar
        registrar(email, evento)
    except Exception:
        logger.warning('Não foi possível registrar aviso na central.')
    try:
        return enfileirar(email, evento)
    except Exception:
        logger.warning('Não foi possível enfileirar notificação push.')
        return 0


def notificar_resposta(rm):
    # Não adivinhar destinatário por RM: somente autoria autenticada de mensagem nova.
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''SELECT DISTINCT m.email_aluno FROM mensagens_chat m JOIN alunos a ON a.email = m.email_aluno
            WHERE m.rm_aluno = %s AND m.remetente = 'ALUNO' AND m.email_aluno IS NOT NULL LIMIT 2;''', (rm,))
        rows = c.fetchall()
    except Exception:
        logger.warning('Não foi possível identificar destinatário do chat para push.')
        return 0
    finally:
        if conn: conn.close()
    return notificar(rows[0][0], 'chat') if len(rows) == 1 else 0


def _proxima():
    conn = get_db_connection()
    try:
        c = conn.cursor(cursor_factory=RealDictCursor)
        c.execute('''WITH candidato AS (
            SELECT id FROM push_entregas WHERE proxima_tentativa <= CURRENT_TIMESTAMP
            AND (reservado_ate IS NULL OR reservado_ate < CURRENT_TIMESTAMP)
            ORDER BY id FOR UPDATE SKIP LOCKED LIMIT 1)
            UPDATE push_entregas SET reservado_ate = CURRENT_TIMESTAMP + INTERVAL '90 seconds',
                tentativas = tentativas + 1 WHERE id = (SELECT id FROM candidato) RETURNING *;''')
        row = c.fetchone()
        conn.commit()
        return row
    finally:
        conn.close()


def _assinatura_atual(job):
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute('''SELECT 1 FROM push_dispositivos WHERE endpoint_hash = %s AND email_aluno = %s
            AND subscription_json = %s;''', (job['endpoint_hash'], job['email_aluno'], job['subscription_json']))
        return bool(c.fetchone())
    finally:
        conn.close()


def _concluir(job, resultado):
    conn = get_db_connection()
    try:
        c = conn.cursor()
        if resultado == 'expirada':
            # Não remover assinatura que tenha sido recadastrada/revinculada durante o envio.
            c.execute('''DELETE FROM push_dispositivos WHERE endpoint_hash = %s AND email_aluno = %s
                AND subscription_json = %s;''', (job['endpoint_hash'], job['email_aluno'], job['subscription_json']))
        if resultado != 'repetir' or job['tentativas'] >= 4:
            c.execute('DELETE FROM push_entregas WHERE id = %s AND tentativas = %s;', (job['id'], job['tentativas']))
        else:
            proxima = datetime.now(timezone.utc) + timedelta(seconds=(60, 300, 900)[min(job['tentativas'] - 1, 2)])
            c.execute('UPDATE push_entregas SET proxima_tentativa = %s, reservado_ate = NULL WHERE id = %s AND tentativas = %s;', (proxima, job['id'], job['tentativas']))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def enviar_assinatura(assinatura, payload):
    config = configuracao()
    if not config:
        return 'repetir'
    try:
        assinatura = validar_assinatura(assinatura)
        if not destino_permitido(assinatura['endpoint']):
            return 'descartar'
        if assinatura['expirationTime'] is not None and assinatura['expirationTime'] <= datetime.now(timezone.utc).timestamp() * 1000:
            return 'expirada'
        import requests
        from py_vapid import Vapid
        from pywebpush import webpush, WebPushException
        class SemRedirecionamento(requests.Session):
            def post(self, url, *args, **kwargs):
                kwargs['allow_redirects'] = False
                return super().post(url, *args, **kwargs)
        with SemRedirecionamento() as session:
            try:
                response = webpush(subscription_info=assinatura, data=json.dumps(payload, ensure_ascii=False),
                    vapid_private_key=Vapid(private_key=config[0]), vapid_claims={'sub': config[2]},
                    content_encoding='aes128gcm', ttl=3600, timeout=8, requests_session=session)
                status = response.status_code
            except WebPushException as error:
                status = getattr(error.response, 'status_code', 0)
        if 200 <= status < 300:
            return 'enviada'
        if status in (404, 410):
            return 'expirada'
        if status in (0, 401, 403, 408, 425, 429) or status >= 500:
            return 'repetir'
        return 'descartar'
    except (ValueError, KeyError, TypeError):
        return 'descartar'
    except Exception:
        # Nunca registrar exceções do provedor: podem carregar endpoint e credenciais.
        logger.warning('Falha temporária ao enviar notificação push.')
        return 'repetir'


def processar_pendentes(limite=20):
    if not configuracao():
        return 0
    count = 0
    for _ in range(limite):
        job = _proxima()
        if not job:
            break
        resultado = 'descartar'
        if _assinatura_atual(job):
            try:
                payload = json.loads(job['payload_json'])
                payload['tag'] = 'etec-push-' + str(job['id'])
                resultado = enviar_assinatura(json.loads(job['subscription_json']), payload)
            except (ValueError, TypeError):
                pass
        _concluir(job, resultado)
        count += 1
    return count


def _executar():
    while True:
        _sinal.wait(timeout=30)
        _sinal.clear()
        try:
            if processar_pendentes() == 20:
                _sinal.set()
        except Exception:
            logger.warning('Fila de notificações temporariamente indisponível.')


def acordar_worker():
    global _thread
    with _lock:
        if _thread is None or not _thread.is_alive():
            _thread = threading.Thread(target=_executar, name='etec-webpush', daemon=True)
            _thread.start()
    _sinal.set()


def enfileirar_teste(email):
    """Teste somente da própria conta, com limite atômico de um a cada 30 segundos."""
    if not configuracao():
        return 'desabilitado'
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute('''INSERT INTO push_ultimo_teste (email_aluno) VALUES (%s)
            ON CONFLICT (email_aluno) DO UPDATE SET criado_em = CURRENT_TIMESTAMP
            WHERE push_ultimo_teste.criado_em < CURRENT_TIMESTAMP - INTERVAL '30 seconds'
            RETURNING email_aluno;''', (email,))
        if not c.fetchone():
            conn.rollback()
            return 'limite'
        title, body = EVENTOS['teste']
        payload = json.dumps({'title': title, 'body': body, 'url': '/', 'icon': '/icon-192.png'})
        c.execute('''INSERT INTO push_entregas (email_aluno, endpoint_hash, subscription_json, payload_json)
            SELECT email_aluno, endpoint_hash, subscription_json, %s FROM push_dispositivos WHERE email_aluno = %s;''', (payload, email))
        if not c.rowcount:
            conn.rollback()
            return 'sem_dispositivo'
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    acordar_worker()
    return 'enfileirado'


if __name__ == '__main__':
    if not configuracao():
        raise SystemExit('Configure as chaves VAPID correspondentes e o contato antes de enviar.')
    _sinal.set()
    _executar()


