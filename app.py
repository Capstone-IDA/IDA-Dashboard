import streamlit as st
import pandas as pd
import plotly.express as px
from utils.auth import login, is_logged_in, get_role, get_company_name, get_company_id, is_online
from utils.sidebar import render_sidebar
from utils.api import api_get

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
                login("admin", "password123"); st.rerun()
            if st.button("🏢 스카이렌터카", use_container_width=True):
                login("sky_rental", "sky1234"); st.rerun()
            if st.button("🏢 제주렌터카", use_container_width=True):
                login("jeju_rental", "jeju1234"); st.rerun()
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

# 서버 연결 상태 표시
if is_online():
    st.caption("🟢 서버 연결됨")
else:
    st.caption("🟡 오프라인 모드 (더미 데이터)")

# ── 어드민 홈 ──
if role == "admin":
    st.title("🛡️ IDA 관리자 홈")
    st.markdown("플랫폼 전체 현황을 확인하세요.")
    st.divider()

    # API에서 데이터 가져오기
    admin_data = api_get("/admin/dashboard")

    if admin_data and isinstance(admin_data, dict):
        total_sessions  = admin_data.get("total_sessions", 0)
        total_events    = admin_data.get("total_events", 0)
        avg_score_total = admin_data.get("avg_final_score", 0)
        total_blacklist = admin_data.get("blacklist_count", 0)
        company_count   = admin_data.get("company_count", 3)
    else:
        # 더미 데이터 폴백
        total_sessions  = 12
        total_events    = 47
        avg_score_total = 74
        total_blacklist = 3
        company_count   = 3

    # 전체 현황
    st.subheader("📊 전체 현황")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("등록 업체 수", f"{company_count}개")
    c2.metric("전체 활성 세션", f"{total_sessions}건")
    c3.metric("오늘 위험 이벤트", f"{total_events}건", delta="-5건", delta_color="inverse")
    c4.metric("전체 평균 점수", f"{avg_score_total}점")
    c5.metric("전체 블랙리스트", f"{total_blacklist}명")

    st.divider()

    # 업체별 비교 차트 (API에서 업체 목록 가져오기)
    companies_data = api_get("/auth/companies")

    if companies_data and isinstance(companies_data, list) and len(companies_data) > 0:
        company_names = [c.get("company_name", "unknown") for c in companies_data]
        # 각 업체별 데이터는 추가 API 호출이 필요할 수 있음
    else:
        company_names = ["스카이렌터카", "제주렌터카", "스타렌터카"]

    company_chart_data = {
        "스카이렌터카": {"sessions": 5,  "events": 18, "avg_score": 68, "blacklist": 1},
        "제주렌터카":   {"sessions": 4,  "events": 21, "avg_score": 74, "blacklist": 2},
        "스타렌터카":   {"sessions": 3,  "events": 8,  "avg_score": 81, "blacklist": 0},
    }

    st.subheader("🏢 업체별 현황 비교")
    chart_col1, chart_col2 = st.columns(2)

    df_company = pd.DataFrame({
        "업체": list(company_chart_data.keys()),
        "평균점수": [v["avg_score"] for v in company_chart_data.values()],
        "위험이벤트": [v["events"] for v in company_chart_data.values()],
        "블랙리스트": [v["blacklist"] for v in company_chart_data.values()],
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
    health = api_get("/health")
    s1, s2, s3, s4 = st.columns(4)
    if health:
        s1.metric("YOLO FPS",    f"{health.get('yolo_fps', 'N/A')}")
        s2.metric("Depth FPS",   f"{health.get('depth_fps', 'N/A')}")
        s3.metric("응답 지연",   f"{health.get('latency_ms', 'N/A')}ms")
        s4.metric("상태",        health.get("status", "N/A"))
    else:
        s1.metric("YOLO FPS",    "35.8", delta="+1.2")
        s2.metric("Depth FPS",   "1.0")
        s3.metric("응답 지연",   "45ms", delta="-5ms")
        s4.metric("패킷 손실률", "0.3%")

# ── 컴패니 홈 ──
else:
    st.title(f"🏢 {company_name} 홈")
    st.divider()

    # API에서 대시보드 데이터 가져오기
    dashboard = api_get("/company/dashboard")

    if dashboard and isinstance(dashboard, dict) and dashboard.get("total_sessions", 0) > 0:
        sessions  = dashboard.get("active_sessions", 0)
        events    = dashboard.get("total_events", 0)
        avg_score = dashboard.get("avg_final_score", 0)
    else:
        # 더미 데이터 폴백
        company_map = {"comp_sky": "스카이렌터카", "comp_jeju": "제주렌터카", "starrent": "스타렌터카"}
        company_id = get_company_id()
        my_company = company_map.get(company_id, "스카이렌터카")
        dummy = {
            "스카이렌터카": {"sessions": 5, "events": 18, "avg_score": 68},
            "제주렌터카":   {"sessions": 4, "events": 21, "avg_score": 74},
            "스타렌터카":   {"sessions": 3, "events": 8,  "avg_score": 81},
        }
        d = dummy.get(my_company, {"sessions": 0, "events": 0, "avg_score": 0})
        sessions  = d["sessions"]
        events    = d["events"]
        avg_score = d["avg_score"]

    # 자사 현황
    st.subheader("📊 오늘 운행 현황")
    m1, m2, m3 = st.columns(3)
    m1.metric("활성 세션",      f"{sessions}건")
    m2.metric("위험 이벤트",    f"{events}건",    delta=f"-3건", delta_color="inverse")
    m3.metric("평균 안전 점수", f"{avg_score}점",  delta="+2점")

    st.divider()

    # 최근 이벤트 (API에서 가져오기)
    events_data = api_get("/company/events")

    al_col, sc_col = st.columns(2)

    with al_col:
        st.subheader("🚨 최근 위험 알림 TOP 3")
        if events_data and isinstance(events_data, list) and len(events_data) > 0:
            severity_colors = {"high": "🔴", "medium": "🟡", "low": "🟢"}
            for ev in events_data[:3]:
                icon = severity_colors.get(ev.get("severity", ""), "⚪")
                st.markdown(f"{icon} **{ev.get('event_type', '')}** — {ev.get('description', '')} `{ev.get('timestamp', '')[:8]}`")
        else:
            # 더미 데이터
            alerts = [
                {"icon": "🔴", "car": "12가 3456", "event": "급제동 감지",  "time": "14:32:05"},
                {"icon": "🔴", "car": "34나 7890", "event": "보행자 근접",  "time": "14:31:42"},
                {"icon": "🟡", "car": "56다 1234", "event": "과속 주행",    "time": "14:30:18"},
            ]
            for a in alerts:
                st.markdown(f"{a['icon']} **{a['car']}** — {a['event']} `{a['time']}`")

    with sc_col:
        st.subheader("📈 이번 달 안전 점수 추이")
        # 점수 타임라인 API
        scores_data = api_get("/company/scores")

        if scores_data and isinstance(scores_data, list) and len(scores_data) > 0:
            df_scores = pd.DataFrame(scores_data)
            fig_trend = px.line(df_scores, x=df_scores.columns[0], y=df_scores.columns[1],
                                markers=True, color_discrete_sequence=["#534AB7"])
        else:
            score_trend = pd.DataFrame({
                "월": ["1월","2월","3월","4월","5월","6월","7월","8월","9월","10월","11월","12월"],
                "평균점수": [72, 68, 75, 71, 78, 82, 79, 85, 81, 88, 84, 90],
            })
            fig_trend = px.line(score_trend, x="월", y="평균점수", markers=True,
                                color_discrete_sequence=["#534AB7"])

        fig_trend.update_layout(height=250, margin=dict(t=20, b=20))
        st.plotly_chart(fig_trend, use_container_width=True)
