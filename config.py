"""
Configurações Globais do Sistema ETEC Achados e Perdidos
Centraliza variáveis de ambiente, credenciais e constantes institucionais.
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

# Armazenamento de Fotos na Nuvem (Cloudinary)
CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET")

# Disparo Transacional de E-mails (Brevo / Sendinblue)
BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "").strip()
SMTP_SENDER = os.environ.get("SMTP_SENDER", "achadoseperdidosetec@gmail.com").strip()

# Porta de Execução do Servidor
PORT = int(os.environ.get("PORT", 5000))
