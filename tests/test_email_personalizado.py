"""Entrega do código com HTML/texto, sem disparar e-mails reais."""
from html.parser import HTMLParser
from unittest.mock import Mock
import pytest
import requests
import server
from services import email_service


PORTAL = 'https://etec-achados.up.railway.app/'


class Elementos(HTMLParser):
    def __init__(self, html):
        super().__init__(); self.tags = []; self.codigo = []; self.no_codigo = False
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))
        if tag == 'p' and dict(attrs).get('class') == 'email-code':
            self.no_codigo = True

    def handle_endtag(self, tag):
        if tag == 'p': self.no_codigo = False

    def handle_data(self, valor):
        if self.no_codigo: self.codigo.append(valor)


@pytest.fixture
def provedor(monkeypatch):
    monkeypatch.setattr(email_service, 'BREVO_API_KEY', 'chave-ficticia-do-teste')
    monkeypatch.setattr(email_service, 'SMTP_SENDER', 'portal@example.org')
    monkeypatch.setattr(email_service, 'PUBLIC_SITE_URL', PORTAL)
    post = Mock(return_value=Mock(status_code=201))
    monkeypatch.setattr(email_service.requests, 'post', post)
    return post


@pytest.mark.parametrize('finalidade,esperado', [('cadastro', 'tela de cadastro'), ('recuperacao', 'tela de recuperação')])
def test_envio_identifica_finalidade_com_html_e_texto_e_codigo_copiavel(provedor, finalidade, esperado):
    assert email_service.enviar_confirmacao('aluno.teste@aluno.cps.sp.gov.br', '123456', finalidade)
    provedor.assert_called_once()
    args, kwargs = provedor.call_args
    assert args == ('https://api.brevo.com/v3/smtp/email',)
    assert kwargs['timeout'] == (5, 15) and kwargs['allow_redirects'] is False
    dados = kwargs['json']
    assert dados['to'] == [{'email': 'aluno.teste@aluno.cps.sp.gov.br'}]
    assert dados['sender'] == {'name': 'ETEC Achados e Perdidos', 'email': 'portal@example.org'}
    assert 'ETEC Achados' in dados['subject'] and '123456' not in dados['subject']
    assert esperado in dados['htmlContent'] and esperado in dados['textContent']
    assert '123456' in dados['textContent'] and '10 minutos' in dados['textContent']
    parser = Elementos(dados['htmlContent'])
    assert parser.codigo == ['123456']  # Sem espaços ou caixas separando os seis dígitos.
    assert not any(tag in ('script', 'iframe') for tag, _ in parser.tags)
    assert [a['src'] for tag, a in parser.tags if tag == 'img'] == [PORTAL + 'logo.png']
    assert [a['href'] for tag, a in parser.tags if tag == 'a'] == [PORTAL]
    assert 'data:image' not in dados['htmlContent'] and 'cid:' not in dados['htmlContent']
    assert len(dados['htmlContent'].encode()) < 20000


@pytest.mark.parametrize('status', [200, 202])
def test_respostas_aceitas_pelo_provedor_continuam_confirmando_envio(provedor, status):
    provedor.return_value.status_code = status
    assert email_service.enviar_confirmacao('aluno@example.org', '123456', 'cadastro')


@pytest.mark.parametrize('status', [400, 401, 429, 500])
def test_recusa_do_provedor_nao_simula_sucesso(provedor, status):
    provedor.return_value.status_code = status
    assert not email_service.enviar_confirmacao('aluno@example.org', '123456', 'cadastro')


@pytest.mark.parametrize('erro', [requests.Timeout, requests.ConnectionError])
def test_erro_de_rede_nao_repete_automaticamente_o_email(provedor, erro):
    provedor.side_effect = erro('Falha simulada')
    assert not email_service.enviar_confirmacao('aluno@example.org', '123456', 'recuperacao')
    provedor.assert_called_once()


def test_sem_chave_nao_tenta_enviar(provedor, monkeypatch):
    monkeypatch.setattr(email_service, 'BREVO_API_KEY', '')
    assert not email_service.enviar_confirmacao('aluno@example.org', '123456', 'cadastro')
    provedor.assert_not_called()


def test_template_escapa_valores_e_nao_coloca_codigo_em_links(provedor):
    corpo = email_service.conteudo_confirmacao('<img src=x onerror=alert(1)>', 'cadastro')['htmlContent']
    assert '&lt;img src=x onerror=alert(1)&gt;' in corpo
    assert [a['src'] for tag, a in Elementos(corpo).tags if tag == 'img'] == [PORTAL + 'logo.png']


def test_sem_endereco_publico_preserva_texto_sem_imagem_ou_link_quebrado(provedor, monkeypatch):
    monkeypatch.setattr(email_service, 'PUBLIC_SITE_URL', '')
    corpo = email_service.conteudo_confirmacao('123456', 'cadastro')
    assert not any(tag in ('img', 'a') for tag, _ in Elementos(corpo['htmlContent']).tags)
    assert 'ETEC ACHADOS' in corpo['htmlContent'] and '123456' in corpo['textContent']
    assert 'localhost' not in corpo['htmlContent'] and 'cid:' not in corpo['htmlContent']


def test_apenas_logo_publica_pode_aparecer_no_webmail_e_template_nao_e_servido(monkeypatch):
    monkeypatch.setattr(server.limiter, 'enabled', False)
    c = server.app.test_client()
    with c.get('/logo.png') as res:
        assert res.status_code == 200 and res.mimetype == 'image/png'
        assert res.headers['Cross-Origin-Resource-Policy'] == 'cross-origin'
        etag = res.headers['ETag']
    with c.get('/logo.png', headers={'If-None-Match': etag}) as res:
        assert res.status_code == 304 and res.headers['Cross-Origin-Resource-Policy'] == 'cross-origin'
    with c.get('/logo_secretaria.png') as res:
        assert res.headers['Cross-Origin-Resource-Policy'] == 'same-origin'
    assert c.get('/templates/email_codigo.html').status_code == 404
