import streamlit as st

ACCOUNTS = {
    "admin":    {"password": "admin123", "role": "admin",   "company_id": None,       "company_name": "시스템 관리자"},
    "skyrent":  {"password": "sky123",   "role": "company", "company_id": "skyrent",  "company_name": "스카이렌터카"},
    "jejurent": {"password": "jeju123",  "role": "company", "company_id": "jejurent", "company_name": "제주렌터카"},
    "starrent": {"password": "star123",  "role": "company", "company_id": "starrent", "company_name": "스타렌터카"},
    "driver1":  {"password": "driver123","role": "driver",  "company_id": "driver1",  "company_name": "차량 단말"},
}

def login(user_id: str, password: str) -> bool:
    account = ACCOUNTS.get(user_id)
    if account and account["password"] == password:
        st.session_state["user_id"]      = user_id
        st.session_state["role"]         = account["role"]
        st.session_state["company_id"]   = account["company_id"]
        st.session_state["company_name"] = account["company_name"]
        st.session_state["logged_in"]    = True
        return True
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
