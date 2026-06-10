import streamlit as st
import requests

# ── 백엔드 서버 주소 (ngrok 또는 localhost) ──
#BASE_URL = "https://blast-london-istanbul-kitty.trycloudflare.com"
BASE_URL = "https://blast-london-istanbul-kitty.trycloudflare.com"
#BASE_URL = "http://localhost:8000"

# 데모용 오프라인 계정 (서버 완전 미연결 시에만 사용)
OFFLINE_ACCOUNTS = {
    "admin":       {"password": "admin1234",   "role": "admin",   "company_id": None,          "company_name": "시스템 관리자"},
    "sky_rental":  {"password": "sky1234",     "role": "company", "company_id": "comp_sky",    "company_name": "스카이렌터카"},
    "jeju_rental": {"password": "jeju1234",    "role": "company", "company_id": "comp_jeju",   "company_name": "제주렌터카"},
    # 드라이버 계정 (시나리오별)
    "driver1":     {"password": "driver123",   "role": "driver",  "company_id": "comp_sky",    "company_name": "스카이렌터카"},  # 12가 3456 · 시나리오 1
    "driver2":     {"password": "driver123",   "role": "driver",  "company_id": "comp_sky",    "company_name": "스카이렌터카"},  # 34나 7890 · 시나리오 2
    "driver3":     {"password": "driver123",   "role": "driver",  "company_id": "comp_jeju",   "company_name": "제주렌터카"},    # 11바 1234 · 시나리오 3
    "driver4":     {"password": "driver123",   "role": "driver",  "company_id": "comp_jeju",   "company_name": "제주렌터카"},    # 22사 5678 · 시나리오 4
}

def login(user_id: str, password: str) -> bool:
    # driver는 프론트 전용 역할 → 백엔드 로그인 불필요 (오프라인 계정에서 처리)
    if user_id.startswith("driver"):
        account = OFFLINE_ACCOUNTS.get(user_id)
        if account and account["password"] == password:
            st.session_state["user_id"]      = user_id
            st.session_state["role"]         = "driver"
            st.session_state["company_id"]   = account["company_id"]
            st.session_state["company_name"] = account["company_name"]
            st.session_state["token"]        = None
            st.session_state["logged_in"]    = True
            st.session_state["online"]       = False
            return True
        return False

    # 1) 백엔드 서버 로그인 시도
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"username": user_id, "password": password},
            headers={"ngrok-skip-browser-warning": "true"},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            role = data.get("role", "")
            token = data.get("token", "")

            st.session_state["user_id"]      = user_id
            st.session_state["role"]         = role
            st.session_state["company_id"]   = data.get("company_id") or None
            st.session_state["company_name"] = data.get("company_name") or ("시스템 관리자" if role == "admin" else "")
            st.session_state["token"]        = token if token else None
            st.session_state["logged_in"]    = True
            st.session_state["online"]       = True
            return True
        else:
            return False
    except requests.exceptions.ConnectionError:
        pass
    except requests.exceptions.Timeout:
        pass
    except Exception:
        pass

    # 2) 서버 완전 미연결 시에만 오프라인 데모 계정
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
    return st.session_state.get("company_id", "") or ""

def get_token() -> str:
    return st.session_state.get("token", "")

def is_online() -> bool:
    return st.session_state.get("online", False)
