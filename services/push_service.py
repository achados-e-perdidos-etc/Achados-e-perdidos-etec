"""Assinaturas pertencem à conta autenticada, nunca a um RM escolhido pelo cliente."""
import hashlib
import json
from database import get_db_connection


def _gravar(query, params):
    conn = get_db_connection()
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        conn.close()


def salvar_assinatura(email, assinatura):
    endpoint_hash = hashlib.sha256(assinatura['endpoint'].encode('utf-8')).hexdigest()
    # Um dispositivo compartilhado pertence à última conta que o vinculou.
    _gravar('''INSERT INTO push_dispositivos (endpoint_hash, email_aluno, subscription_json)
        VALUES (%s, %s, %s) ON CONFLICT (endpoint_hash) DO UPDATE
        SET email_aluno = EXCLUDED.email_aluno, subscription_json = EXCLUDED.subscription_json,
            atualizado_em = CURRENT_TIMESTAMP;''',
        (endpoint_hash, email, json.dumps(assinatura)))


def remover_assinatura(email, endpoint):
    endpoint_hash = hashlib.sha256(endpoint.encode('utf-8')).hexdigest()
    _gravar('DELETE FROM push_dispositivos WHERE endpoint_hash = %s AND email_aluno = %s;',
            (endpoint_hash, email))
