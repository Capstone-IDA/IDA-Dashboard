import streamlit as st
from utils.auth import get_role, get_company_name, logout

HIDE_MENU_CSS = """
<style>
[data-testid="stSidebarNav"] {display: none !important;}
[data-testid="stSidebarNavItems"] {display: none !important;}
div[class*="st-emotion-cache"] > ul {display: none !important;}
</style>
"""

def render_sidebar():
    role = get_role()
    company_name = get_company_name()

    with st.sidebar:
        st.markdown(HIDE_MENU_CSS, unsafe_allow_html=True)

        st.markdown(f"### 🔵 IDA")
        st.markdown(f"**{company_name}**")
        st.markdown(f"`{'관리자' if role == 'admin' else '렌터카 업체'}`")
        st.divider()

        st.page_link("app.py",           label="홈",                icon="🏠")
        st.page_link("pages/company.py", label="Company Dashboard", icon="🏢")
        st.page_link("pages/manage.py",  label="업체 관리",          icon="📋")
        if role == "admin":
            st.page_link("pages/admin.py", label="Admin Dashboard", icon="🛡️")

        # 로그아웃 버튼을 하단에 배치
        st.markdown("<div style='flex:1'></div>", unsafe_allow_html=True)
        for _ in range(8):
            st.write("")
        st.divider()
        if st.button("로그아웃", use_container_width=True):
            logout()
            st.rerun()
