import requests
import streamlit as st

# BASE_URL
BASE_URL = "https://unfocusedly-pleurocarpous-gina.ngrok-free.dev"

def _headers():
    """인증 헤더 생성"""
    token = st.session_state.get("token", "")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}

def api_get(endpoint: str, params: dict = None):
    """
    GET 요청. 성공 시 JSON 반환, 실패 시 None.
    """
    try:
        resp = requests.get(
            f"{BASE_URL}{endpoint}",
            headers=_headers(),
            params=params,
            timeout=5
        )
        if resp.status_code == 200:
            return resp.json()
        else:
            return None
    except Exception:
        return None

def api_post(endpoint: str, json_data: dict = None):
    """
    POST 요청. 성공 시 JSON 반환, 실패 시 None.
    """
    try:
        resp = requests.post(
            f"{BASE_URL}{endpoint}",
            headers=_headers(),
            json=json_data,
            timeout=5
        )
        if resp.status_code == 200:
            return resp.json()
        else:
            return None
    except Exception:
        return None

def is_server_online():
    """서버 연결 상태 확인"""
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=2)
        return resp.status_code == 200
    except Exception:
        return False
