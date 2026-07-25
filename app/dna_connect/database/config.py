import os

from dotenv import load_dotenv

load_dotenv()


DB_HOST = os.getenv("DB_HOST_CARDS")
DB_PORT = int(os.getenv("DB_PORT_CARDS"))
DB_NAME = os.getenv("DB_NAME_CARDS")
DB_USER = os.getenv("DB_USER_CARDS")
DB_PASSWORD = os.getenv("DB_PASSWORD_CARDS")
DB_SSLMODE = os.getenv("DB_SSLMODE_CARDS", "require")
