import os

from dotenv import load_dotenv

load_dotenv()


BREVO_API_KEY = os.getenv("BREVO_API_KEY")
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "DNA Connect")
EMAIL_FROM_ADDRESS = os.getenv("EMAIL_FROM_ADDRESS", "contato@denianfernandes.com")
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8000").rstrip("/")

EMAIL_VERIFICATION_EXPIRATION_HOURS = int(
    os.getenv("EMAIL_VERIFICATION_EXPIRATION_HOURS", "24")
)

EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS = int(
    os.getenv("EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS", "60")
)
