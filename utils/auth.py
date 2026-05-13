import streamlit as st
import requests

# ngrok 주소
BASE_URL = "https://unfocusedly-pleurocarpous-gina.ngrok-free.dev"

# 데모용 오프라인 계정 
OFFLINE_ACCOUNTS = {
    "admin":    {"password": "admin123", "role": "admin",   "company_id": None,       "company_name": "시스템 관리자 (데모)"},
    "sky_rental":  {"password": "sky1234",   "role": "company", "company_id": "sky_rental",  "company_name": "스카이렌터카 (데모)"},
    "jeju_rental": {"password": "jeju1234",  "role": "company", "company_id": "jeju_rental", "company_name": "제주렌터카 (데모)"},
    "starrent": {"password": "star123",  "role": "company", "company_id": "starrent", "company_name": "스타렌터카 (데모)"},
    "driver1":  {"password": "driver123","role": "driver",  "company_id": "driver1",  "company_name": "차량 단말 (데모)"},
}

def login(user_id: str, password: str) -> bool:
    account = OFFLINE_ACCOUNTS.get(user_id)
    if account and account["password"] == password:
        st.session_state["user_id"]      = user_id
        st.session_state["role"]         = account["role"]
        st.session_state["company_id"]   = account["company_id"]
        st.session_state["company_name"] = account["company_name"]
        st.session_state["logged_in"]    = True
        return True
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login", 
            json={"username": user_id, "password": password},
            timeout=1 
        )
        
        if response.status_code == 200:
            data = response.json()
            st.session_state["user_id"]      = user_id
            st.session_state["role"]         = data.get("role")
            st.session_state["company_id"]   = data.get("company_id")
            st.session_state["company_name"] = data.get("company_name")
            st.session_state["logged_in"]    = True
            st.success("✨ 서버 연동 로그인 성공!")
            return True
            
    except Exception:
        pass 

    st.error("로그인 정보를 확인해주세요.")
    return False

def logout():
    for key in ["user_id", "role", "company_id", "company_name", "logged_in"]:
        st.session_state.pop(key, None)

def is_logged_in() -> bool:
    return st.session_state.get("logged_in", False)

def get_role() -> str:
    return st.session_state.get("role", "")

def get_company_name() -> str:
    return st.session_state.get("company_name", "")

def get_company_id() -> str:
    return st.session_state.get("company_id", "")