import requests
import time
from config import GIGACHAT_AUTH, GIGACHAT_SCOPE, GIGACHAT_TOKEN_URL, GIGACHAT_API_URL

class GigaChatAPI:
    def __init__(self):
        self.token = None
        self.token_expiry = 0

    def get_access_token(self):
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
            'RqUID': '23917d1f-efb8-4806-b484-9fd31fcbf6ea',
            'Authorization': f'Basic {GIGACHAT_AUTH}'
        }
        data = {'scope': GIGACHAT_SCOPE}
        response = requests.post(GIGACHAT_TOKEN_URL, headers=headers, data=data, verify=False)
        if response.status_code == 200:
            resp_json = response.json()
            self.token = resp_json['access_token']
            self.token_expiry = time.time() + resp_json.get('expires_in', 3600) - 60
            return self.token
        else:
            raise Exception(f'Failed to get access token: {response.text}')

    def ensure_token(self):
        if not self.token or time.time() > self.token_expiry:
            self.get_access_token()
        return self.token

    def ask_gigachat(self, messages, model="GigaChat-2-Max", stream=False, update_interval=0):
        self.ensure_token()
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.token}'
        }
        data = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "update_interval": update_interval
        }
        response = requests.post(GIGACHAT_API_URL, headers=headers, json=data, verify=False)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f'GigaChat API error: {response.status_code} {response.text}')

gigachat_api = GigaChatAPI() 