import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

DATABASE_URL = os.environ.get("DATABASE_URL")

JWT_SECRET = os.environ.get("JWT_SECRET", "").strip()
if len(JWT_SECRET.encode('utf-8')) < 32:
    raise RuntimeError("Configure JWT_SECRET com um segredo aleatório de pelo menos 32 bytes no ambiente.")
EMAIL_SECRETARIA = os.environ.get("ADMIN_EMAIL", "achadoseperdidosetec@gmail.com").strip().lower()
ADMIN_SENHA = os.environ.get("ADMIN_SENHA", "").strip()
ADMIN_SENHA_HASH = os.environ.get("ADMIN_SENHA_HASH", "").strip()

DOMINIOS_EMAIL_PERMITIDOS = [
    "@aluno.cps.sp.gov.br",
    "@cps.sp.gov.br",
    "@etec.sp.gov.br"
]

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "").strip()

VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "").strip()
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "").strip()
VAPID_CLAIMS_EMAIL = os.environ.get("VAPID_CLAIMS_EMAIL", "mailto:achadoseperdidosetec@gmail.com").strip()

CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET")

BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "").strip()
SMTP_SENDER = os.environ.get("SMTP_SENDER", "achadoseperdidosetec@gmail.com").strip()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_AI_API_KEY", "").strip()

PORT = int(os.environ.get("PORT", 5000))

