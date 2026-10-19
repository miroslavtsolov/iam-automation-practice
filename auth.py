import os
import requests
from dotenv import load_dotenv

load_dotenv()

def get_access_token():
    url = f"{os.environ['KEYCLOAK_BASE_URL']}/realms/{os.environ['REALM']}/protocol/openid-connect/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": os.environ["CLIENT_ID"],
        "client_secret": os.environ["CLIENT_SECRET"],
    }
    resp = requests.post(url, data=data, timeout=10)
    resp.raise_for_status()
    return resp.json()["access_token"]
