"""Indexação da apresentação pública, sem domínio inventado ou dados de contas."""
import json
from html.parser import HTMLParser
from unittest.mock import patch
from xml.etree import ElementTree
import pytest
import server
from utils.seo import DESCRICAO, normalizar_url_publica


class Cabecalho(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.tags = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def valor(self, tag, atributo, valor, campo):
        achados = [attrs[campo] for nome, attrs in self.tags if nome == tag and attrs.get(atributo) == valor]
        assert len(achados) == 1
        return achados[0]


@pytest.fixture
def cliente(monkeypatch):
    monkeypatch.setitem(server.app.config, 'PUBLIC_SITE_URL', '')
    monkeypatch.setattr(server.limiter, 'enabled', False)
    with patch.object(server, 'get_db_connection') as banco:
        yield server.app.test_client(), banco
        banco.assert_not_called()


def test_previa_nao_e_indexada_e_nao_inventa_endereco(cliente):
    c, _ = cliente
    for rota in ['/', '/index.html']:
        with c.get(rota, headers={'Host': 'previa.example.org'}) as res:
            assert res.status_code == 200 and res.mimetype == 'text/html'
            assert res.headers['X-Robots-Tag'] == 'noindex'
            html = res.get_data(as_text=True)
            cabecalho = Cabecalho(html)
            assert cabecalho.valor('meta', 'name', 'robots', 'content') == 'noindex, follow'
            assert cabecalho.valor('meta', 'name', 'description', 'content') == DESCRICAO
            assert not any(tag == 'link' and attrs.get('rel') == 'canonical' for tag, attrs in cabecalho.tags)
            assert 'application/ld+json' not in html and 'previa.example.org' not in html
    with c.get('/robots.txt') as res:
        assert res.status_code == 200 and res.mimetype == 'text/plain'
        assert 'Sitemap:' not in res.get_data(as_text=True)
    with c.get('/sitemap.xml') as res:
        assert res.status_code == 503 and res.headers['X-Robots-Tag'] == 'noindex'
        assert '<loc>' not in res.get_data(as_text=True)


def test_pagina_publica_tem_canonical_e_dados_sem_depender_do_host(cliente, monkeypatch):
    c, _ = cliente
    url = 'https://achados.example.org/'
    monkeypatch.setitem(server.app.config, 'PUBLIC_SITE_URL', url)
    for rota in ['/', '/index.html?busca=segredo&token=nao-publicar']:
        with c.get(rota, headers={'Host': 'outro.example.net', 'X-Forwarded-Host': 'invasor.invalid'}) as res:
            assert res.status_code == 200 and 'X-Robots-Tag' not in res.headers
            html = res.get_data(as_text=True)
            cabecalho = Cabecalho(html)
            assert cabecalho.valor('link', 'rel', 'canonical', 'href') == url
            assert cabecalho.valor('meta', 'name', 'robots', 'content') == 'index, follow'
            assert cabecalho.valor('meta', 'property', 'og:url', 'content') == url
            assert cabecalho.valor('meta', 'property', 'og:image', 'content') == url + 'icon-512.png'
            dados = json.loads(html.split('<script type="application/ld+json">', 1)[1].split('</script>', 1)[0])
            assert dados['@type'] == 'WebSite' and dados['url'] == url and dados['name'] == 'ETEC Achados e Perdidos'
            assert dados['description'] == DESCRICAO
            assert all(x not in html for x in ['outro.example.net', 'invasor.invalid', 'nao-publicar', '<!-- seo-publico -->'])


def test_mapa_lista_so_apresentacao_e_robots_permite_recursos(cliente, monkeypatch):
    c, _ = cliente
    monkeypatch.setitem(server.app.config, 'PUBLIC_SITE_URL', 'https://achados.example.org/')
    with c.get('/sitemap.xml') as res:
        assert res.status_code == 200 and res.mimetype == 'application/xml'
        xml = ElementTree.fromstring(res.data)
        assert [n.text for n in xml.iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')] == ['https://achados.example.org/']
        assert 'no-cache' in res.headers['Cache-Control']
    with c.get('/robots.txt') as res:
        assert res.status_code == 200
        texto = res.get_data(as_text=True)
        assert 'User-agent: *\nAllow: /\n' in texto
        assert 'Disallow:' not in texto  # Robôs precisam ler os noindex e renderizar CSS/JS.
        assert 'Sitemap: https://achados.example.org/sitemap.xml' in texto


@pytest.mark.parametrize('rota', ['/secretaria', '/admin', '/controle_etec_7788.html', '/404.html',
                                '/termos', '/api/auth/verificar', '/nao-existe', '/api/nao-existe', '/config.py'])
def test_areas_pessoais_apis_e_erros_nao_entram_na_busca(cliente, monkeypatch, rota):
    c, _ = cliente
    monkeypatch.setitem(server.app.config, 'PUBLIC_SITE_URL', 'https://achados.example.org/')
    with c.get(rota, headers={'Accept': 'text/html'}) as res:
        assert res.headers['X-Robots-Tag'] == 'noindex'
        if rota.startswith('/api/'):
            assert res.status_code in (401, 404) and 'no-store' in res.headers['Cache-Control']
        if rota == '/config.py':
            assert res.status_code == 404


@pytest.mark.parametrize('valor', ['http://achados.example.org', '//achados.example.org',
    'https://nome:senha@achados.example.org', 'https://achados.example.org/caminho',
    'https://achados.example.org/?codigo=123', 'https://achados.example.org/#token',
    'https://achados.example.org:99999', 'https://localhost', 'https://127.0.0.1',
    'https://[::1]', 'https://achados.example.org\nSitemap: https://invasor.invalid',
    'https://achados.example.org\\invasor', 'https://<script>.example.org'])
def test_configuracao_recusa_endereco_inseguro_ou_temporario(valor):
    with pytest.raises(RuntimeError, match='PUBLIC_SITE_URL'):
        normalizar_url_publica(valor)


def test_configuracao_normaliza_raiz_oficial_e_permite_ambiente_sem_dominio():
    assert normalizar_url_publica('') == ''
    assert normalizar_url_publica(' https://ACHADOS.example.org:443/ ') == 'https://achados.example.org/'
    assert normalizar_url_publica('https://achados.example.org') == 'https://achados.example.org/'
