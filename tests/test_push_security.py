"""Rotas reais e SQL isolado para cadastro/desvinculação por conta, sem envio externo."""
import base64
import json
import sqlite3
from unittest.mock import MagicMock, patch

import pytest
import server
from services import push_service
from utils.push import SCHEMA_PUSH
from tests.test_student_authorship import Connection as SQLConnection


class Connection(SQLConnection):
    def rollback(self):
        self.connection.rollback()


def subscription(suffix='um'):
    # Ponto público gerador P-256, usado somente como dado de teste.
    point = bytes.fromhex('04'
        '6b17d1f2e12c4247f8bce6e563a440f277037d812deb33a0f4a13945d898c296'
        '4fe342e2fe1a7f9b8ee7eb4a7c0f9e162bce33576b315ececbb6406837bf51f5')
    encode = lambda data: base64.urlsafe_b64encode(data).decode().rstrip('=')
    return {'endpoint': 'https://push.example.org/' + suffix, 'expirationTime': None,
            'keys': {'auth': encode(bytes(range(16))), 'p256dh': encode(point)}}


def auth(email='primeiro@aluno.cps.sp.gov.br', rm='12345', secretaria=False):
    token = (server.gerar_token_secretaria(email) if secretaria else
             server.gerar_token_aluno(email, 'Nome da conta', rm))
    return {'Authorization': 'Bearer ' + token}


@pytest.fixture(params=['unificado', 'modular'])
def env(request):
    db = sqlite3.connect(':memory:')
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys = ON')
    db.executescript('''CREATE TABLE alunos (email TEXT PRIMARY KEY, nome TEXT, rm TEXT);
        CREATE TABLE push_subscriptions (rm_aluno TEXT PRIMARY KEY, subscription_json TEXT);
        INSERT INTO push_subscriptions VALUES ('12345','legado-sem-autoria');''')
    for email, rm in [('primeiro@aluno.cps.sp.gov.br', '12345'),
                     ('segundo@aluno.cps.sp.gov.br', '12345'), ('docente@etec.sp.gov.br', 'PROFESSOR')]:
        db.execute('INSERT INTO alunos VALUES (?,?,?)', (email, 'Nome da conta', rm))
    db.executescript(SCHEMA_PUSH)
    app = server.app
    if request.param == 'modular':
        from flask import Flask
        from blueprints.Push import push_bp
        app = Flask(__name__)
        app.register_blueprint(push_bp)
    app.config['TESTING'] = True
    server.limiter.enabled = False
    with patch.object(push_service, 'get_db_connection', return_value=Connection(db)) as connection, \
         patch('services.professores_service.buscar_acesso', return_value=None):
        yield app.test_client(), db, connection
    db.close()


def test_post_delete_exigem_sessao_valida_antes_do_banco(env):
    client, db, connection = env
    expired = {'Authorization': 'Bearer ' + server.gerar_token_aluno(
        'primeiro@aluno.cps.sp.gov.br', 'Aluno', '12345', dias_validade=-1)}
    for headers in [{}, {'Authorization': 'Bearer forjado'}, expired]:
        for method in ['POST', 'DELETE']:
            for data in [{'subscription': subscription()}, []]:
                response = client.open('/api/push/subscribe', method=method, headers=headers, json=data)
                assert response.status_code == 401
    connection.assert_not_called()


def test_cadastro_ignora_rm_email_e_perfil_enviados_e_preserva_legados(env):
    client, db, connection = env
    body = {'subscription': subscription(), 'rm': '99999', 'email': 'segundo@aluno.cps.sp.gov.br', 'role': 'secretaria'}
    for _ in range(2):
        result = client.post('/api/push/subscribe', headers=auth(), json=body)
        assert result.status_code == 200 and result.json == {'success': True}
        assert 'no-store' in result.headers['Cache-Control']
    rows = db.execute('SELECT * FROM push_dispositivos').fetchall()
    assert len(rows) == 1 and rows[0]['email_aluno'] == 'primeiro@aluno.cps.sp.gov.br'
    assert json.loads(rows[0]['subscription_json']) == subscription()
    assert db.execute('SELECT subscription_json FROM push_subscriptions').fetchone()[0] == 'legado-sem-autoria'
    db.executescript(SCHEMA_PUSH)  # Migração é idempotente e não adota vínculos por RM.
    assert db.execute('SELECT COUNT(*) FROM push_dispositivos').fetchone()[0] == 1


def test_contas_com_mesmo_rm_e_multiplos_dispositivos_nao_se_sobrescrevem(env):
    client, db, connection = env
    for email, suffix in [('primeiro@aluno.cps.sp.gov.br', 'um'),
                          ('primeiro@aluno.cps.sp.gov.br', 'dois'), ('segundo@aluno.cps.sp.gov.br', 'tres')]:
        assert client.post('/api/push/subscribe', headers=auth(email),
                           json={'subscription': subscription(suffix)}).status_code == 200
    rows = db.execute('SELECT email_aluno FROM push_dispositivos').fetchall()
    assert len(rows) == 3
    assert sum(row[0] == 'primeiro@aluno.cps.sp.gov.br' for row in rows) == 2
    # Mesmo sabendo o endpoint, uma conta não exclui a assinatura de outra.
    body = {'endpoint': subscription()['endpoint'], 'email': 'primeiro@aluno.cps.sp.gov.br'}
    assert client.delete('/api/push/subscribe', headers=auth('segundo@aluno.cps.sp.gov.br'), json=body).status_code == 200
    assert db.execute('SELECT COUNT(*) FROM push_dispositivos').fetchone()[0] == 3
    assert client.delete('/api/push/subscribe', headers=auth(), json=body).status_code == 200
    assert db.execute('SELECT COUNT(*) FROM push_dispositivos').fetchone()[0] == 2


def test_dispositivo_compartilhado_muda_para_conta_atual_e_logout_antigo_nao_remove_nova(env):
    client, db, connection = env
    for email in ['primeiro@aluno.cps.sp.gov.br', 'segundo@aluno.cps.sp.gov.br']:
        assert client.post('/api/push/subscribe', headers=auth(email), json={'subscription': subscription()}).status_code == 200
    assert db.execute('SELECT email_aluno FROM push_dispositivos').fetchone()[0] == 'segundo@aluno.cps.sp.gov.br'
    assert client.delete('/api/push/subscribe', headers=auth(), json={'endpoint': subscription()['endpoint']}).status_code == 200
    assert db.execute('SELECT COUNT(*) FROM push_dispositivos').fetchone()[0] == 1


def test_professor_e_rm_pendente_podem_configurar_notificacoes_da_propria_conta(env):
    client, db, connection = env
    for email, rm in [('docente@etec.sp.gov.br', 'PROFESSOR'), ('primeiro@aluno.cps.sp.gov.br', 'PENDENTE')]:
        result = client.post('/api/push/subscribe', headers=auth(email, rm), json={'subscription': subscription(email)})
        assert result.status_code == 200
    assert db.execute('SELECT COUNT(*) FROM push_dispositivos').fetchone()[0] == 2
    result = client.post('/api/push/subscribe', headers=auth(secretaria=True), json={'subscription': subscription()})
    assert result.status_code == 403


@pytest.mark.parametrize('endpoint', ['', None, 1, 'http://push.example.org/x', 'javascript:alert(1)',
    'https://usuario:senha@push.example.org/x', 'https://push.example.org/x#parte',
    'https://push.example.org:999999/x', 'https://push.example.org/x\n', 'https://[invalido/x', 'x' * 4097])
def test_endpoint_invalido_nao_chega_ao_banco(env, endpoint):
    client, db, connection = env
    data = subscription()
    data['endpoint'] = endpoint
    for method, body in [('POST', {'subscription': data}), ('DELETE', {'endpoint': endpoint})]:
        assert client.open('/api/push/subscribe', method=method, headers=auth(), json=body).status_code == 400
    connection.assert_not_called()


@pytest.mark.parametrize('changes', [None, [], 'texto', {}, {'keys': {}}, {'keys': []},
    {'keys': {'p256dh': 'xxx', 'auth': 'xxx'}},
    {'expirationTime': -1}, {'expirationTime': True}, {'expirationTime': 'amanhã'},
    {'expirationTime': float('inf')}, {'expirationTime': 10**100},
    {'keys': {'p256dh': 'x' * 1000, 'auth': 'x' * 24}}])
def test_assinatura_invalida_nao_chega_ao_banco(env, changes):
    client, db, connection = env
    data = subscription()
    if isinstance(changes, dict):
        data.update(changes)
        if not changes:
            data = {}
    else:
        data = changes
    assert client.post('/api/push/subscribe', headers=auth(), json={'subscription': data}).status_code == 400
    connection.assert_not_called()


def test_json_invalido_erro_de_banco_nao_expoe_assinatura_e_chave_publica_e_options_sao_publicos(env):
    client, db, connection = env
    assert client.post('/api/push/subscribe', headers=auth(), json=[]).status_code == 400
    for method in ['POST', 'DELETE']:
        assert client.open('/api/push/subscribe', method=method, headers=auth(), data='x', content_type='application/json').status_code == 400
    assert client.options('/api/push/subscribe').status_code == 200
    assert client.get('/api/push/public-key').status_code == 200
    connection.assert_not_called()
    connection.side_effect = RuntimeError('erro contendo uma chave secreta e endpoint privado')
    result = client.post('/api/push/subscribe', headers=auth(), json={'subscription': subscription()})
    assert result.status_code == 503
    assert 'chave secreta' not in result.get_data(as_text=True)
    assert subscription()['endpoint'] not in result.get_data(as_text=True)


def test_falha_de_gravacao_faz_rollback_e_fecha_conexao():
    connection = MagicMock()
    connection.cursor.return_value.execute.side_effect = RuntimeError('falha simulada')
    with patch.object(push_service, 'get_db_connection', return_value=connection):
        with pytest.raises(RuntimeError):
            push_service.salvar_assinatura('primeiro@aluno.cps.sp.gov.br', subscription())
    connection.rollback.assert_called_once()
    connection.close.assert_called_once()
    connection.cursor.return_value.close.assert_called_once()
