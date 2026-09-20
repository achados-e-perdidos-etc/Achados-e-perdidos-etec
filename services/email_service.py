"""
Serviço Transacional de Disparo de E-mails
Integração com API REST da Brevo (Sendinblue).
"""
import requests
from threading import Thread
from config import BREVO_API_KEY, SMTP_SENDER

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
