"""Metadados públicos sem usar Host ou cabeçalhos de proxy como endereço oficial."""
import ipaddress
import json
import re
from html import escape
from urllib.parse import urlsplit


NOME_SITE = 'ETEC Achados e Perdidos'
DESCRICAO = ('Procure objetos perdidos e encontrados na ETEC. Alunos e professores '
             'podem registrar pertences e solicitar a retirada com a secretaria.')


def normalizar_url_publica(valor):
    if not valor or not valor.strip():
        return ''
    mensagem = 'PUBLIC_SITE_URL deve ser um endereço HTTPS público, sem caminho, credenciais, consulta ou fragmento.'
    try:
        valor = valor.strip()
        if len(valor) > 2048 or any(c.isspace() or c in '\\<>"\'' for c in valor):
            raise ValueError
        partes = urlsplit(valor)
        if (partes.scheme != 'https' or not partes.hostname or partes.username is not None
                or partes.password is not None or partes.path not in ('', '/')
                or partes.query or partes.fragment or '?' in valor or '#' in valor):
            raise ValueError
        host = partes.hostname.encode('idna').decode('ascii').lower().rstrip('.')
        try:
            endereco = ipaddress.ip_address(host)
        except ValueError:
            if (len(host) > 253 or '.' not in host or host.endswith(('.localhost', '.local'))
                    or any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', p) for p in host.split('.'))):
                raise ValueError
        else:
            if not endereco.is_global:
                raise ValueError
            if endereco.version == 6:
                host = '[' + host + ']'
        porta = partes.port
        return 'https://' + host + (':' + str(porta) if porta and porta != 443 else '') + '/'
    except (ValueError, UnicodeError):
        raise RuntimeError(mensagem) from None


def metadados_publicos(url):
    if not url:
        return '<meta name="robots" content="noindex, follow">'
    dados = {'@context': 'https://schema.org', '@type': 'WebSite', '@id': url + '#website',
             'name': NOME_SITE, 'alternateName': 'ETEC Achados', 'url': url,
             'description': DESCRICAO, 'inLanguage': 'pt-BR'}
    estruturados = json.dumps(dados, ensure_ascii=False).replace('<', '\\u003c')
    return '\n'.join([
        '<meta name="robots" content="index, follow">',
        '<link rel="canonical" href="' + escape(url, quote=True) + '">',
        '<meta property="og:url" content="' + escape(url, quote=True) + '">',
        '<meta property="og:image" content="' + escape(url + 'icon-512.png', quote=True) + '">',
        '<meta property="og:image:alt" content="Logo do ETEC Achados e Perdidos">',
        '<script type="application/ld+json">' + estruturados + '</script>',
    ])


def mapa_site(url):
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            '<url><loc>' + escape(url) + '</loc></url></urlset>\n')
