import os

from dotenv import load_dotenv

load_dotenv()


BREVO_API_KEY = os.getenv("BREVO_API_KEY")
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "DNA Connect")
EMAIL_FROM_ADDRESS = os.getenv("EMAIL_FROM_ADDRESS", "contato@denianfernandes.com")
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8000").rstrip("/")

# Domínio usado só para o link público do cartão (QR Code/NFC/cartão de
# visita digital) — separado de APP_BASE_URL (login, e-mail de
# verificação, redefinição de senha) para permitir um subdomínio
# dedicado (ex: card.dominio.com) sem afetar os links transacionais.
# Sem CARD_BASE_URL configurada, cai para APP_BASE_URL — comportamento
# atual preservado até essa variável ser definida explicitamente.
CARD_BASE_URL = os.getenv("CARD_BASE_URL", APP_BASE_URL).rstrip("/")

EMAIL_VERIFICATION_EXPIRATION_HOURS = int(
    os.getenv("EMAIL_VERIFICATION_EXPIRATION_HOURS", "24")
)

EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS = int(
    os.getenv("EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS", "60")
)

PASSWORD_RESET_EXPIRATION_HOURS = int(
    os.getenv("PASSWORD_RESET_EXPIRATION_HOURS", "1")
)
