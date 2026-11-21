"""Política HTTP comum, sem confiar em cabeçalhos de proxy enviados pelo visitante."""
import os
from urllib.parse import urlsplit
from flask import request,jsonify
from utils.seo import normalizar_url_publica


def instalar(app):
    origens={x.strip().rstrip('/') for x in os.environ.get('CORS_ORIGINS','').split(',') if x.strip()}
    # O proxy encerra o HTTPS antes do Flask. Use somente os endereços
    # configurados pelo operador/provedor, sem confiar em X-Forwarded-*.
    publica = app.config.get('PUBLIC_SITE_URL', '')
    if publica:
        origens.add(normalizar_url_publica(publica).rstrip('/'))
    dominio_railway = os.environ.get('RAILWAY_PUBLIC_DOMAIN', '').strip()
    if dominio_railway:
        try:
            origens.add(normalizar_url_publica('https://' + dominio_railway).rstrip('/'))
        except RuntimeError:
            raise RuntimeError('RAILWAY_PUBLIC_DOMAIN deve conter somente o domínio público do serviço, sem protocolo ou caminho.') from None
    for origem in origens:
        p=urlsplit(origem)
        if p.scheme not in ('https','http') or not p.netloc or p.path or p.query or p.fragment or p.username:raise RuntimeError('CORS_ORIGINS deve conter origens completas, sem caminho.')
    @app.before_request
    def proteger_requisicao():
        if not request.path.startswith('/api/'):return
        if request.path.startswith('/api/auth/') or request.path in ('/api/login','/api/ia/comparar-semantica'):
            request.max_content_length=16*1024
        origem=request.headers.get('Origin')
        if origem and origem!=request.host_url.rstrip('/') and origem not in origens:
            return jsonify(success=False,message='Origem não autorizada.'),403
        if request.method=='OPTIONS':
            resposta=jsonify(success=True)
            resposta.headers['Access-Control-Allow-Methods']='GET, POST, PUT, DELETE, OPTIONS'
            resposta.headers['Access-Control-Allow-Headers']='Content-Type, Authorization, x-access-token, Idempotency-Key, X-Upload-Offset'
            resposta.headers['Access-Control-Max-Age']='600'
            return resposta
        if request.endpoint in ('env_cod','cad_aluno','log_aluno','red_senha','log_sec','rota_ia_sem') and request.is_json and request.get_data(cache=True):
            if not isinstance(request.get_json(silent=True),dict):return jsonify(success=False,message='Envie um objeto JSON válido.'),400
    @app.after_request
    def proteger_resposta(resposta):
        resposta.headers.update({'X-Content-Type-Options':'nosniff','Referrer-Policy':'same-origin','X-Frame-Options':'DENY',
          'Permissions-Policy':'camera=(self), microphone=(), geolocation=(), payment=(), usb=()',
          'Cross-Origin-Opener-Policy':'same-origin','Cross-Origin-Resource-Policy':'same-origin'})
        # A logo é pública e também aparece no HTML dos e-mails transacionais.
        if request.path == '/logo.png' and resposta.status_code in (200, 304):
            resposta.headers['Cross-Origin-Resource-Policy'] = 'cross-origin'
        # Handlers HTML legados ainda usam scripts/estilos inline. Não habilitar unsafe-eval.
        resposta.headers['Content-Security-Policy']="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https://res.cloudinary.com; font-src 'self'; connect-src 'self' "+' '.join(sorted(origens))+"; media-src 'self' blob:; worker-src 'self' blob:; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
        if request.is_secure:resposta.headers['Strict-Transport-Security']='max-age=31536000'
        # Só a apresentação pública entra nas buscas. No ambiente sem domínio,
        # também impede a indexação da prévia; não substitui a autenticação.
        if (not app.config.get('PUBLIC_SITE_URL') or resposta.status_code >= 400
                or (request.path not in ('/', '/index.html')
                    and (request.path.startswith('/api/') or resposta.mimetype == 'text/html'))):
            resposta.headers['X-Robots-Tag'] = 'noindex'
        if request.path.startswith('/api/'):
            resposta.headers['Cache-Control']='private, no-store'
            resposta.headers['Vary']='Origin, Authorization, x-access-token'
            origem=request.headers.get('Origin')
            if origem and (origem==request.host_url.rstrip('/') or origem in origens):resposta.headers['Access-Control-Allow-Origin']=origem
        return resposta
