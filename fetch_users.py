import os
import requests
from auth import get_access_token

def fetch_all_users():
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    base = f"{os.environ['KEYCLOAK_BASE_URL']}/admin/realms/{os.environ['REALM']}/users"

    users, first, page_size = [], 0, 20
    while True:
        resp = requests.get(base, headers=headers, params={"first": first, "max": page_size}, timeout=10)
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        users.extend(batch)
        first += page_size
    return users

def disable_user(user_id):
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = f"{os.environ['KEYCLOAK_BASE_URL']}/admin/realms/{os.environ['REALM']}/users/{user_id}"
    resp = requests.put(url, headers=headers, json={"enabled": False}, timeout=10)
    resp.raise_for_status()
