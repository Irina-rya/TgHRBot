import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8052800269:AAGEzAih78uAqze6xgPGqFlr8r8SDacCIYE')
GIGACHAT_AUTH = os.getenv('GIGACHAT_AUTH', 'ZjY1NDdlOTEtZDBjNC00OWM5LTliZmEtZTY3YzU4YTcxZTZmOmY2YWU1ZGNiLTI5MGMtNDQyNy1hMjAzLThkMDVkNTUyMzIyMQ==')
HR_TELEGRAM_ID = os.getenv('HR_TELEGRAM_ID', '524032239')

GIGACHAT_SCOPE = 'GIGACHAT_API_PERS'
GIGACHAT_TOKEN_URL = 'https://ngw.devices.sberbank.ru:9443/api/v2/oauth'
GIGACHAT_API_URL = 'https://gigachat.devices.sberbank.ru/api/v1/chat/completions' 