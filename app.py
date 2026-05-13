import streamlit as st
import pandas as pd
import plotly.express as px
from utils.auth import login, is_logged_in, get_role, get_company_name, get_company_id
from utils.sidebar import render_sidebar

st.set_page_config(
    page_title="IDA — Indoor Detection & Assistance",
    page_icon="🔵",
    layout="wide",
)

# ── 로그인 안 된 경우 ──
if not is_logged_in():
    st.markdown("""
        <style>
        [data-testid="stSidebarNav"] {display: none !important;}
        [data-testid="stSidebar"] {display: none !important;}
        [data-testid="collapsedControl"] {display: none !important;}
        div[data-testid="stVerticalBlock"] { min-width: 320px; }
        </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("## ")
        st.markdown("""
            <div style='text-align:center; margin-bottom:2rem;'>
                <span style='font-size:2rem; font-weight:800; color:#534AB7;'>IDA</span><br>
                <span style='font-size:0.85rem; color:#888;'>Indoor Detection & Assistance</span>
            </div>
        """, unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("#### 로그인")
            user_id  = st.text_input("아이디", placeholder="아이디 입력")
            password = st.text_input("비밀번호", type="password", placeholder="비밀번호 입력")

            if st.button("로그인", use_container_width=True, type="primary"):
                if login(user_id, password):
                    st.rerun()
                else:
                    st.error("아이디 또는 비밀번호가 올바르지 않습니다.")

            st.markdown("---")
            st.markdown("**데모 계정으로 빠른 로그인**")
            if st.button("🛡️ 시스템 관리자", use_container_width=True):
                login("admin", "admin123"); st.rerun()
            if st.button("🏢 스카이렌터카", use_container_width=True):
                login("sky_rental", "sky1234"); st.rerun()
            if st.button("🏢 제주렌터카", use_container_width=True):
                login("jeju_rental", "jeju1234"); st.rerun()
            if st.button("🏢 스타렌터카", use_container_width=True):
                login("starrent", "star123"); st.rerun()
            st.markdown("")
            if st.button("🚗 차량 단말 (12가 3456)", use_container_width=True):
                login("driver1", "driver123"); st.rerun()

    st.stop()

# ═══════════════════════════════════════
#  로그인 된 경우
# ═══════════════════════════════════════
role = get_role()

# ── 드라이버: 사이드바 없이 풀스크린 HUD ──
if role == "driver":
    st.markdown("""
        <style>
        [data-testid="stSidebarNav"] {display: none !important;}
        [data-testid="stSidebar"] {display: none !important;}
        [data-testid="collapsedControl"] {display: none !important;}
        </style>
    """, unsafe_allow_html=True)

    from utils.driver_view import render_driver_dashboard
    render_driver_dashboard()
    st.stop()

# ── 어드민 / 컴패니: 사이드바 있는 일반 대시보드 ──
render_sidebar()
company_name = get_company_name()

# ── 어드민 홈 ──
if role == "admin":
    st.title("🛡️ IDA 관리자 홈")
    st.markdown("플랫폼 전체 현황을 확인하세요.")
    st.divider()

    company_data = {
        "스카이렌터카": {"sessions": 5,  "events": 18, "avg_score": 68, "blacklist": 1},
        "제주렌터카":   {"sessions": 4,  "events": 21, "avg_score": 74, "blacklist": 2},
        "스타렌터카":   {"sessions": 3,  "events": 8,  "avg_score": 81, "blacklist": 0},
    }

    total_sessions  = sum(v["sessions"]  for v in company_data.values())
    total_events    = sum(v["events"]    for v in company_data.values())
    avg_score_total = round(sum(v["avg_score"] for v in company_data.values()) / len(company_data))
    total_blacklist = sum(v["blacklist"] for v in company_data.values())

    # 전체 현황
    st.subheader("📊 전체 현황")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("등록 업체 수", "3개")
    c2.metric("전체 활성 세션", f"{total_sessions}건")
    c3.metric("오늘 위험 이벤트", f"{total_events}건", delta="-5건", delta_color="inverse")
    c4.metric("전체 평균 점수", f"{avg_score_total}점")
    c5.metric("전체 블랙리스트", f"{total_blacklist}명")

    st.divider()

    # 업체별 비교 차트
    st.subheader("🏢 업체별 현황 비교")
    chart_col1, chart_col2 = st.columns(2)

    df_company = pd.DataFrame({
        "업체": list(company_data.keys()),
        "평균점수": [v["avg_score"] for v in company_data.values()],
        "위험이벤트": [v["events"] for v in company_data.values()],
        "블랙리스트": [v["blacklist"] for v in company_data.values()],
    })

    with chart_col1:
        fig1 = px.bar(df_company, x="업체", y="평균점수", title="업체별 평균 안전 점수",
                      color="평균점수", color_continuous_scale=["#E24B4A","#EF9F27","#1D9E75"])
        fig1.update_layout(height=250, margin=dict(t=40, b=20))
        st.plotly_chart(fig1, use_container_width=True)

    with chart_col2:
        fig2 = px.bar(df_company, x="업체", y="위험이벤트", title="업체별 위험 이벤트 수",
                      color="위험이벤트", color_continuous_scale=["#1D9E75","#EF9F27","#E24B4A"])
        fig2.update_layout(height=250, margin=dict(t=40, b=20))
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # 시스템 상태
    st.subheader("⚙️ 시스템 상태")
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("YOLO FPS",    "35.8", delta="+1.2")
    s2.metric("Depth FPS",   "1.0")
    s3.metric("응답 지연",   "45ms", delta="-5ms")
    s4.metric("패킷 손실률", "0.3%")

# ── 컴패니 홈 ──
else:
    company_map = {"sky_rental": "스카이렌터카", "jeju_rental": "제주렌터카", "starrent": "스타렌터카"}
    company_id = get_company_id()
    my_company = company_map.get(company_id, "스카이렌터카")

    my_data = {
        "스카이렌터카": {"sessions": 5, "events": 18, "avg_score": 68},
        "제주렌터카":   {"sessions": 4, "events": 21, "avg_score": 74},
        "스타렌터카":   {"sessions": 3, "events": 8,  "avg_score": 81},
    }[my_company]

    recent_alerts = {
        "스카이렌터카": [
            {"차량번호": "12가 3456", "이벤트": "급제동 감지",  "시간": "14:32:05", "심각도": "높음"},
            {"차량번호": "34나 7890", "이벤트": "보행자 근접",  "시간": "14:31:42", "심각도": "높음"},
            {"차량번호": "56다 1234", "이벤트": "과속 주행",    "시간": "14:30:18", "심각도": "중간"},
        ],
        "제주렌터카": [
            {"차량번호": "78라 5678", "이벤트": "충돌 위험",    "시간": "14:29:55", "심각도": "높음"},
            {"차량번호": "90마 9012", "이벤트": "급출발 감지",  "시간": "14:28:30", "심각도": "중간"},
            {"차량번호": "11바 1234", "이벤트": "정상 주행",    "시간": "14:27:10", "심각도": "낮음"},
        ],
        "스타렌터카": [
            {"차량번호": "22사 5678", "이벤트": "주차장 진입",  "시간": "14:27:10", "심각도": "낮음"},
            {"차량번호": "33아 9012", "이벤트": "정상 주행",    "시간": "14:26:00", "심각도": "낮음"},
            {"차량번호": "44자 3456", "이벤트": "정상 주행",    "시간": "14:25:00", "심각도": "낮음"},
        ],
    }[my_company]

    score_trend = pd.DataFrame({
        "월": ["1월","2월","3월","4월","5월","6월","7월","8월","9월","10월","11월","12월"],
        "평균점수": [72, 68, 75, 71, 78, 82, 79, 85, 81, 88, 84, 90],
    })

    st.title(f"🏢 {company_name} 홈")
    st.divider()

    # 자사 현황
    st.subheader("📊 오늘 운행 현황")
    m1, m2, m3 = st.columns(3)
    m1.metric("활성 세션",    f"{my_data['sessions']}건")
    m2.metric("위험 이벤트",  f"{my_data['events']}건",    delta=f"-3건", delta_color="inverse")
    m3.metric("평균 안전 점수", f"{my_data['avg_score']}점", delta="+2점")

    st.divider()

    # 최근 알림 TOP3 + 점수 추이
    al_col, sc_col = st.columns(2)

    with al_col:
        st.subheader("🚨 최근 위험 알림 TOP 3")
        severity_colors = {"높음": "🔴", "중간": "🟡", "낮음": "🟢"}
        for a in recent_alerts:
            icon = severity_colors.get(a["심각도"], "⚪")
            st.markdown(f"{icon} **{a['차량번호']}** — {a['이벤트']} `{a['시간']}`")

    with sc_col:
        st.subheader("📈 이번 달 안전 점수 추이")
        fig_trend = px.line(score_trend, x="월", y="평균점수", markers=True,
                            color_discrete_sequence=["#534AB7"])
        fig_trend.update_layout(height=250, margin=dict(t=20, b=20))
        st.plotly_chart(fig_trend, use_container_width=True)
