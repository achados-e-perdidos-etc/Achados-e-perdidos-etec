"""Formato das assinaturas e armazenamento separado dos vínculos legados por RM."""
import base64
import math
import re
from urllib.parse import urlsplit


SCHEMA_PUSH = '''CREATE TABLE IF NOT EXISTS push_dispositivos (
    endpoint_hash VARCHAR(64) PRIMARY KEY,
    email_aluno VARCHAR(150) NOT NULL REFERENCES alunos(email) ON DELETE CASCADE,
    subscription_json TEXT NOT NULL,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);'''


def validar_endpoint(endpoint):
    if (not isinstance(endpoint, str) or not 1 <= len(endpoint) <= 4096
            or re.search(r'[\x00-\x20\x7f]', endpoint)):
        raise ValueError('Endereço de notificação inválido.')
    try:
        parsed = urlsplit(endpoint)
        if (parsed.scheme != 'https' or not parsed.hostname or parsed.username is not None
                or parsed.password is not None or parsed.fragment or parsed.port not in (None, 443)):
            raise ValueError
    except ValueError:
        raise ValueError('O endereço de notificação deve usar HTTPS, sem credenciais ou fragmento.') from None
    return endpoint


def _chave(valor, tamanho):
    if (not isinstance(valor, str) or len(valor) > 128
            or not re.fullmatch(r'[A-Za-z0-9_-]+={0,2}', valor)):
        raise ValueError('Chaves de notificação inválidas.')
    try:
        decoded = base64.b64decode(valor + '=' * (-len(valor) % 4), altchars=b'-_', validate=True)
    except ValueError:
        raise ValueError('Chaves de notificação inválidas.') from None
    if len(decoded) != tamanho or (tamanho == 65 and decoded[0] != 4):
        raise ValueError('Chaves de notificação inválidas.')
    return valor


def validar_assinatura(data):
    if not isinstance(data, dict) or not isinstance(data.get('keys'), dict):
        raise ValueError('Envie uma assinatura de notificação válida.')
    expiration = data.get('expirationTime')
    if expiration is not None and (type(expiration) not in (int, float)
                                  or expiration < 0 or expiration > 2**53 - 1
                                  or not math.isfinite(expiration)):
        raise ValueError('Validade da assinatura inválida.')
    return {
        'endpoint': validar_endpoint(data.get('endpoint')),
        'expirationTime': expiration,
        'keys': {'p256dh': _chave(data['keys'].get('p256dh'), 65),
                 'auth': _chave(data['keys'].get('auth'), 16)}
    }

SCHEMA_ENTREGAS_PUSH = '''CREATE TABLE IF NOT EXISTS push_entregas (
    id BIGSERIAL PRIMARY KEY,
    email_aluno VARCHAR(150) NOT NULL REFERENCES alunos(email) ON DELETE CASCADE,
    endpoint_hash VARCHAR(64) NOT NULL,
    subscription_json TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    tentativas INTEGER NOT NULL DEFAULT 0,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    proxima_tentativa TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reservado_ate TIMESTAMPTZ
);'''

INDICE_ENTREGAS_PUSH = 'CREATE INDEX IF NOT EXISTS push_entregas_agenda ON push_entregas (proxima_tentativa, id);'

SCHEMA_EMAIL_CHAT = '''ALTER TABLE mensagens_chat ADD COLUMN IF NOT EXISTS email_aluno VARCHAR(150);
CREATE INDEX IF NOT EXISTS mensagens_conta_id ON mensagens_chat(email_aluno,id);'''

SCHEMA_LIMITE_PUSH = '''CREATE TABLE IF NOT EXISTS push_ultimo_teste (
    email_aluno VARCHAR(150) PRIMARY KEY REFERENCES alunos(email) ON DELETE CASCADE,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);'''
