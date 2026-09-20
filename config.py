"""
Configurações Globais do Sistema ETEC Achados e Perdidos
Centraliza variáveis de ambiente, credenciais, chaves Google OAuth e Push.
"""
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Banco de Dados PostgreSQL em Nuvem
DATABASE_URL = os.environ.get("DATABASE_URL")

# Autenticação e Criptografia
JWT_SECRET = os.environ.get("JWT_SECRET", "@#Etec_Achad0s_2026_Secret_T0ken!)").strip()
EMAIL_SECRETARIA = os.environ.get("ADMIN_EMAIL", "achadoseperdidosetec@gmail.com").strip().lower()
ADMIN_SENHA = os.environ.get("ADMIN_SENHA", "").strip()
ADMIN_SENHA_HASH = os.environ.get("ADMIN_SENHA_HASH", "").strip()

# Domínios Institucionais Permitidos (Centro Paula Souza / ETEC)
DOMINIOS_EMAIL_PERMITIDOS = [
    "@aluno.cps.sp.gov.br",  # Padrão oficial atual de e-mail de alunos
    "@cps.sp.gov.br",        # Servidores e professores do Centro Paula Souza
    "@etec.sp.gov.br"        # Domínio institucional legado/complementar
]

# Google OAuth 2.0 / Single Sign-On (Google Identity Services)
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "").strip()

# Web Push Notifications (VAPID Keys)
VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "BEl62iUYgUivxIkv69yViEuiBIa-Ib9-SkvMeAtA3LFgDZKrxZJjSPO2S-2jT_GL5prEQC43XP0_12N_sample").strip()
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "").strip()
VAPID_CLAIMS_EMAIL = os.environ.get("VAPID_CLAIMS_EMAIL", "mailto:achadoseperdidosetec@gmail.com").strip()

# Armazenamento de Fotos na Nuvem (Cloudinary)
CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET")

# Disparo Transacional de E-mails (Brevo / Sendinblue)
BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "").strip()
SMTP_SENDER = os.environ.get("SMTP_SENDER", "achadoseperdidosetec@gmail.com").strip()

# Porta de Execução do Servidor
PORT = int(os.environ.get("PORT", 5000))
