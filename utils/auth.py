import streamlit as st
import requests

# ── 백엔드 서버 주소 ──
BASE_URL = "https://unfocusedly-pleurocarpous-gina.ngrok-free.dev"

# 데모용 오프라인 계정
OFFLINE_ACCOUNTS = {
    "admin":       {"password": "password123", "role": "admin",   "company_id": None,          "company_name": "시스템 관리자"},
    "sky_rental":  {"password": "sky1234",     "role": "company", "company_id": "comp_sky",    "company_name": "스카이렌터카"},
    "jeju_rental": {"password": "jeju1234",    "role": "company", "company_id": "comp_jeju",   "company_name": "제주렌터카"},
    "driver1":     {"password": "driver123",   "role": "driver",  "company_id": "driver1",     "company_name": "차량 단말"},
}

def login(user_id: str, password: str) -> bool:
    # 1) 백엔드 서버 로그인 시도
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"username": user_id, "password": password},
            timeout=3
        )
        if response.status_code == 200:
            data = response.json()
            st.session_state["user_id"]      = user_id
            st.session_state["role"]         = data.get("role")
            st.session_state["company_id"]   = data.get("company_id")
            st.session_state["company_name"] = data.get("company_name")
            st.session_state["token"]        = data.get("token")  # ← 토큰 저장!
            st.session_state["logged_in"]    = True
            st.session_state["online"]       = True
            return True
    except Exception:
        pass

    # 2) 서버 안 되면 오프라인 데모 계정으로 폴백
    account = OFFLINE_ACCOUNTS.get(user_id)
    if account and account["password"] == password:
        st.session_state["user_id"]      = user_id
        st.session_state["role"]         = account["role"]
        st.session_state["company_id"]   = account["company_id"]
        st.session_state["company_name"] = account["company_name"]
        st.session_state["token"]        = None
        st.session_state["logged_in"]    = True
        st.session_state["online"]       = False
        return True

    return False

def logout():
    for key in ["user_id", "role", "company_id", "company_name", "logged_in", "token", "online"]:
        st.session_state.pop(key, None)

def is_logged_in() -> bool:
    return st.session_state.get("logged_in", False)

def get_role() -> str:
    return st.session_state.get("role", "")

def get_company_name() -> str:
    return st.session_state.get("company_name", "")

def get_company_id() -> str:
    return st.session_state.get("company_id", "")

def get_token() -> str:
    return st.session_state.get("token", "")

def is_online() -> bool:
    return st.session_state.get("online", False)
