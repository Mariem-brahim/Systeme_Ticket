import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY        = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

    DB_HOST           = os.environ.get('DB_HOST',     'localhost')
    DB_USER           = os.environ.get('DB_USER',     'root')
    DB_PASSWORD       = os.environ.get('DB_PASSWORD', '')
    DB_NAME           = os.environ.get('DB_NAME',     'gestion_tickets')

    SMTP_SERVER       = os.environ.get('SMTP_SERVER',   'smtp.gmail.com')
    SMTP_PORT         = int(os.environ.get('SMTP_PORT', 587))
    SMTP_USER         = os.environ.get('SMTP_USER',     '')
    SMTP_PASSWORD     = os.environ.get('SMTP_PASSWORD', '')

    WTF_CSRF_ENABLED    = True
    WTF_CSRF_TIME_LIMIT = 3600
