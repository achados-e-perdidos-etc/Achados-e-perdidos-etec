"""
Serviço Transacional de Disparo de E-mails
Integração com API REST da Brevo (Sendinblue).
"""
import requests
from threading import Thread
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from config import BASE_DIR, BREVO_API_KEY, SMTP_SENDER, PUBLIC_SITE_URL


_templates = Environment(loader=FileSystemLoader(BASE_DIR + '/templates'),
    autoescape=select_autoescape(['html']), undefined=StrictUndefined)


def conteudo_confirmacao(codigo, finalidade):
    """HTML e alternativa em texto; o código permanece um único trecho copiável."""
    textos = {
        'cadastro': {
            'assunto': 'Confirme seu e-mail | ETEC Achados',
            'etiqueta': 'UM NOVO REENCONTRO COMEÇA AQUI',
            'titulo': 'Confirme seu e-mail.',
            'introducao': 'Falta só confirmar que este e-mail institucional é seu. Use o código abaixo na tela de cadastro para continuar.',
            'instrucao': 'Volte à tela de cadastro e informe o código para criar sua conta.',
            'previa': 'Seu código para criar uma conta no ETEC Achados e Perdidos. Válido por 10 minutos.',
        },
        'recuperacao': {
            'assunto': 'Recupere seu acesso | ETEC Achados',
            'etiqueta': 'SEU PORTAL ESTÁ LOGO ALI',
            'titulo': 'Vamos recuperar seu acesso.',
            'introducao': 'Recebemos um pedido para redefinir sua senha. Use o código abaixo na tela de recuperação para escolher uma nova senha.',
            'instrucao': 'Volte à tela de recuperação e informe o código para definir sua nova senha.',
            'previa': 'Seu código para recuperar o acesso ao ETEC Achados e Perdidos. Válido por 10 minutos.',
        },
    }[finalidade]
    portal = PUBLIC_SITE_URL
    html = _templates.get_template('email_codigo.html').render(
        **textos, codigo=codigo, portal_url=portal, logo_url=portal + 'logo.png' if portal else '')
    texto = ('ETEC ACHADOS E PERDIDOS\n\n' + textos['titulo'] + '\n' + textos['introducao']
        + '\n\nSeu código de confirmação: ' + str(codigo) + '\nVálido por 10 minutos.\n\n'
        + textos['instrucao'] + '\n\nNão compartilhe este código. Se você não fez este pedido, ignore este e-mail.'
        + '\n\nAchados, cuidados, devolvidos.' + ('\nPortal: ' + portal if portal else ''))
    return {'subject': textos['assunto'], 'htmlContent': html, 'textContent': texto}

def enviar_confirmacao(destinatario,codigo,finalidade):
    """Só confirma o pedido de código se o provedor aceitar o e-mail."""
    if not BREVO_API_KEY:return False
    try:
        resposta=requests.post('https://api.brevo.com/v3/smtp/email',headers={'api-key':BREVO_API_KEY,'Content-Type':'application/json'},
          json={'sender':{'name':'ETEC Achados e Perdidos','email':SMTP_SENDER},'to':[{'email':destinatario}],
          **conteudo_confirmacao(codigo,finalidade)},timeout=(5,15),allow_redirects=False)
        return resposta.status_code in (200,201,202)
    except requests.RequestException:return False

def enviar_email_api_async(destinatario, assunto, html_content):
    """
    Executa a requisição HTTP para a API Brevo v3.
    """
    if not BREVO_API_KEY or not destinatario:
        return
    try:
        payload = {
            "sender": {"name": "Achados e Perdidos ETEC", "email": SMTP_SENDER},
            "to": [{"email": destinatario}],
            "subject": assunto,
            "htmlContent": html_content
        }
        headers = {
            "accept": "application/json",
            "api-key": BREVO_API_KEY,
            "content-type": "application/json"
        }
        requests.post("https://api.brevo.com/v3/smtp/email", json=payload, headers=headers, timeout=10)
    except Exception as e:
        print(f"[Brevo] Falha ao enviar e-mail para {destinatario}: {e}")

def disparar_email(destinatario, assunto, html_content):
    """
    Dispara o e-mail em background através de uma thread independente
    para não travar a resposta da requisição HTTP.
    """
    Thread(target=enviar_email_api_async, args=(destinatario, assunto, html_content)).start()
