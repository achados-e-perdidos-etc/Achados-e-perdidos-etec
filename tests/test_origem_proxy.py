"""Origem HTTPS pública com conexão HTTP interna, sem liberar sites estranhos."""
from unittest.mock import Mock
from flask import Flask, jsonify
import pytest
from utils.http_security import instalar


PUBLICA = 'https://etec-achados.up.railway.app'


def aplicativo(monkeypatch, *, publica='', railway='', cors=''):
    monkeypatch.setenv('CORS_ORIGINS', cors)
    monkeypatch.setenv('RAILWAY_PUBLIC_DOMAIN', railway)
    app = Flask(__name__)
    app.config['PUBLIC_SITE_URL'] = publica
    instalar(app)
    executar = Mock()

    @app.route('/api/teste', methods=['POST', 'OPTIONS'])
    def operacao():
        executar()
        return jsonify(success=True)

    return app.test_client(), executar


@pytest.mark.parametrize('opcoes', [
    {'publica': PUBLICA + '/'},
    {'railway': 'etec-achados.up.railway.app'},
    {'cors': PUBLICA},
])
def test_https_publico_passa_pelo_proxy_e_recebe_cors_exato(monkeypatch, opcoes):
    cliente, executar = aplicativo(monkeypatch, **opcoes)
    headers = {'Origin': PUBLICA, 'Access-Control-Request-Method': 'POST',
               'Access-Control-Request-Headers': 'content-type'}
    # O Host público é preservado, mas a conexão do proxy com Flask é HTTP.
    base = 'http://etec-achados.up.railway.app'
    preflight = cliente.options('/api/teste', base_url=base, headers=headers)
    assert preflight.status_code == 200 and preflight.headers['Access-Control-Allow-Origin'] == PUBLICA
    executar.assert_not_called()
    resposta = cliente.post('/api/teste', base_url=base, headers={'Origin': PUBLICA}, json={})
    assert resposta.status_code == 200 and resposta.headers['Access-Control-Allow-Origin'] == PUBLICA
    assert 'no-store' in resposta.headers['Cache-Control']
    assert 'Access-Control-Allow-Credentials' not in resposta.headers
    executar.assert_called_once()


@pytest.mark.parametrize('origem', ['https://invasor.invalid', 'null', '*',
    PUBLICA + '.invasor.invalid', 'https://outro.up.railway.app', PUBLICA + ':444',
    PUBLICA + '/caminho', 'https://nome@etec-achados.up.railway.app'])
def test_origem_publica_nao_autoriza_outros_sites_nem_headers_de_proxy_falsos(monkeypatch, origem):
    cliente, executar = aplicativo(monkeypatch, publica=PUBLICA + '/', railway='etec-achados.up.railway.app')
    headers = {'Origin': origem, 'X-Forwarded-Proto': 'https',
               'X-Forwarded-Host': 'invasor.invalid', 'Forwarded': 'host=invasor.invalid;proto=https'}
    for metodo in ['OPTIONS', 'POST']:
        resposta = cliente.open('/api/teste', method=metodo, base_url='http://etec-achados.up.railway.app', headers=headers, json={})
        assert resposta.status_code == 403 and 'Access-Control-Allow-Origin' not in resposta.headers
    executar.assert_not_called()


def test_apenas_headers_de_proxy_nao_liberam_https_sem_configuracao(monkeypatch):
    cliente, executar = aplicativo(monkeypatch)
    resposta = cliente.options('/api/teste', base_url='http://etec-achados.up.railway.app',
        headers={'Origin': PUBLICA, 'X-Forwarded-Proto': 'https', 'X-Forwarded-Host': 'etec-achados.up.railway.app'})
    assert resposta.status_code == 403 and 'Access-Control-Allow-Origin' not in resposta.headers
    executar.assert_not_called()


def test_dominio_railway_nao_ativa_indexacao_automaticamente(monkeypatch):
    cliente, _ = aplicativo(monkeypatch, railway='etec-achados.up.railway.app')
    resposta = cliente.post('/api/teste', base_url='http://etec-achados.up.railway.app', headers={'Origin': PUBLICA}, json={})
    assert resposta.status_code == 200 and resposta.headers['X-Robots-Tag'] == 'noindex'


def test_origins_adicionais_e_cliente_nativo_continuam_permitidos(monkeypatch):
    cliente, executar = aplicativo(monkeypatch, publica=PUBLICA + '/', cors='https://outro.example.org')
    for headers in [{'Origin': 'https://outro.example.org'}, {}]:
        assert cliente.post('/api/teste', base_url='http://etec-achados.up.railway.app', headers=headers, json={}).status_code == 200
    assert executar.call_count == 2


@pytest.mark.parametrize('railway', ['https://etec-achados.up.railway.app', 'etec-achados.up.railway.app/caminho',
    '*.railway.app', 'nome@etec-achados.up.railway.app'])
def test_dominio_do_provedor_malformado_falha_na_inicializacao(monkeypatch, railway):
    with pytest.raises(RuntimeError, match='RAILWAY_PUBLIC_DOMAIN'):
        aplicativo(monkeypatch, railway=railway)
