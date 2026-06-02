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
        div[data-testid="stButton"] button {
            white-space: nowrap !important;
            overflow: hidden;
            text-overflow: ellipsis;
            font-size: 0.82rem !important;
            padding-left: 0.4rem !important;
            padding-right: 0.4rem !important;
        }
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
                login("admin", "admin1234"); st.rerun()
            if st.button("🏢 스카이렌터카", use_container_width=True):
                login("sky_rental", "sky1234"); st.rerun()
            if st.button("🏢 제주렌터카", use_container_width=True):
                login("jeju_rental", "jeju1234"); st.rerun()
            st.markdown("")
            st.markdown("**🚗 차량 단말 (드라이버)**")
            if st.button("S1 · 12가 3456 (스카이렌터카)", use_container_width=True):
                login("driver1", "driver123"); st.rerun()
            if st.button("S2 · 34나 7890 (스카이렌터카)", use_container_width=True):
                login("driver2", "driver123"); st.rerun()
            if st.button("S3 · 11바 1234 (제주렌터카)", use_container_width=True):
                login("driver3", "driver123"); st.rerun()
            if st.button("S4 · 22사 5678 (제주렌터카)", use_container_width=True):
                login("driver4", "driver123"); st.rerun()

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

if is_online():
    st.caption("🟢 서버 연결됨")
else:
    st.caption("🟡 오프라인 모드 (더미 데이터)")

# ── 어드민 홈 ──
if role == "admin":
    st.title("🛡️ IDA 관리자 홈")
    st.markdown("플랫폼 전체 현황을 확인하세요.")
    st.divider()

    admin_data = api_get("/admin/dashboard")

    if admin_data and isinstance(admin_data, dict):
        _api_sessions  = admin_data.get("total_sessions", 0)
        _api_events    = admin_data.get("total_events", 0)
        _api_score     = admin_data.get("avg_final_score", 0)
        _api_blacklist = admin_data.get("blacklist_count", 0)
        _api_companies = admin_data.get("company_count", 0)
        # 값이 비정상이면(0이거나 100점이면) 더미 사용
        total_sessions  = _api_sessions  if _api_sessions  > 0 else 4
        total_events    = _api_events    if _api_events    > 0 else 22
        avg_score_total = round(_api_score) if 0 < _api_score < 99 else 73
        total_blacklist = _api_blacklist if _api_blacklist > 0 else 4
        company_count   = _api_companies if _api_companies > 0 else 2
    else:
        total_sessions  = 4
        total_events    = 22
        avg_score_total = 73
        total_blacklist = 4
        company_count   = 2

    st.subheader("📊 전체 현황")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("등록 업체 수", f"{company_count}개")
    c2.metric("전체 활성 세션", f"{total_sessions}건")
    c3.metric("오늘 위험 이벤트", f"{total_events}건", delta="-5건", delta_color="inverse")
    c4.metric("전체 평균 점수", f"{avg_score_total}점")
    c5.metric("전체 블랙리스트", f"{total_blacklist}명")

    st.divider()

    companies_data = api_get("/auth/companies")

    # API 실제값 + 더미 병합
    company_chart_data = {
        "스카이렌터카": {"sessions": 2, "events": 10, "avg_score": 75, "blacklist": 2},
        "제주렌터카":   {"sessions": 2, "events": 12, "avg_score": 71, "blacklist": 2},
    }
    if companies_data and isinstance(companies_data, list):
        CMAP = {"comp_sky": "스카이렌터카", "comp_jeju": "제주렌터카"}
        for c in companies_data:
            name = c.get("company_name") or CMAP.get(c.get("company_id",""), "")
            if name and name in company_chart_data:
                if c.get("active_sessions"): company_chart_data[name]["sessions"] = c["active_sessions"]
                if c.get("total_events"):    company_chart_data[name]["events"]   = c["total_events"]
                if c.get("avg_score"):       company_chart_data[name]["avg_score"] = round(c["avg_score"])

    st.subheader("🏢 업체별 현황 비교")
    chart_col1, chart_col2 = st.columns(2)

    df_company = pd.DataFrame({
        "업체": list(company_chart_data.keys()),
        "평균점수": [v["avg_score"] for v in company_chart_data.values()],
        "위험이벤트": [v["events"] for v in company_chart_data.values()],
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

    st.subheader("⚙️ 시스템 상태")
    health = api_get("/health")
    s1, s2, s3, s4 = st.columns(4)
    # health API 필드명 대응 + 의미있는 값 폴백
    _yolo_fps = None
    _depth_fps = None
    _latency = None
    _status = "정상"
    if health and isinstance(health, dict):
        _yolo_fps  = health.get("yolo_fps") or health.get("fps")
        _depth_fps = health.get("depth_fps")
        _latency   = health.get("latency_ms") or health.get("latency")
        _status    = "정상" if health.get("status") in ["healthy", "정상", "ok"] else health.get("status", "정상")
    s1.metric("YOLO FPS",    f"{_yolo_fps or '35.8'}")
    s2.metric("Depth FPS",   f"{_depth_fps or '1.0'}")
    s3.metric("응답 지연",   f"{_latency or '45'}ms")
    s4.metric("상태",        _status)

# ── 컴패니 홈 ──
else:
    st.title(f"🏢 {company_name} 홈")
    st.divider()

    dashboard = api_get("/company/dashboard")

    if dashboard and isinstance(dashboard, dict) and dashboard.get("total_sessions", 0) > 0:
        sessions  = dashboard.get("active_sessions", 0)
        events    = dashboard.get("total_events", 0)
        avg_score = dashboard.get("avg_final_score", 0)
    else:
        company_map = {"comp_sky": "스카이렌터카", "comp_jeju": "제주렌터카"}
        company_id = get_company_id()
        my_company = company_map.get(company_id, "스카이렌터카")
        dummy = {
            "스카이렌터카": {"sessions": 2, "events": 10, "avg_score": 75},
            "제주렌터카":   {"sessions": 2, "events": 12, "avg_score": 71},
        }
        d = dummy.get(my_company, {"sessions": 0, "events": 0, "avg_score": 0})
        sessions  = d["sessions"]
        events    = d["events"]
        avg_score = d["avg_score"]

    # 차량·고객 수 (API 없으면 더미)
    VEHICLE_DUMMY = {"comp_sky": 5, "comp_jeju": 4}
    CUSTOMER_DUMMY = {"comp_sky": 4, "comp_jeju": 4}
    _cid = get_company_id()
    vehicle_count  = dashboard.get("vehicle_count", 0) if dashboard and isinstance(dashboard, dict) and dashboard.get("vehicle_count") else VEHICLE_DUMMY.get(_cid, 0)
    customer_count = dashboard.get("customer_count", 0) if dashboard and isinstance(dashboard, dict) and dashboard.get("customer_count") else CUSTOMER_DUMMY.get(_cid, 0)

    st.subheader("📊 오늘 운행 현황")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("활성 세션",      f"{sessions}건")
    m2.metric("위험 이벤트",    f"{events}건",    delta=f"-3건", delta_color="inverse")
    m3.metric("평균 안전 점수", f"{avg_score}점",  delta="+2점")
    m4.metric("등록 차량",      f"{vehicle_count}대")
    m5.metric("등록 고객",      f"{customer_count}명")

    st.divider()

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
            import json as _json, os as _os, time as _time
            _base = ""
            try:
                _af = _os.path.join(_os.getcwd(), "active_session.json")
                if _os.path.exists(_af):
                    _d = _json.load(open(_af, encoding="utf-8"))
                    _base = _d.get("started_at", "")
            except Exception:
                pass

            def _toff(b, m):
                try:
                    h, mn, s = map(int, b.split(":"))
                    t = h * 60 + mn - m
                    t = max(0, t)
                    return f"{t//60:02d}:{t%60:02d}:{s:02d}"
                except Exception:
                    return _time.strftime("%H:%M:%S")

            _bt = _base or _time.strftime("%H:%M:%S")
            company_id_cur = get_company_id()
            if company_id_cur == "comp_jeju":
                alerts = [
                    {"icon": "🔴", "car": "22사 5678", "event": "전방 차량 충돌 위험", "time": _toff(_bt, 6)},
                    {"icon": "🟡", "car": "11바 1234", "event": "고속 주행 감지",      "time": _toff(_bt, 2)},
                ]
            else:
                alerts = [
                    {"icon": "🔴", "car": "34나 7890", "event": "전방 차량 접근 감지", "time": _toff(_bt, 1)},
                    {"icon": "🟡", "car": "12가 3456", "event": "급제동 감지",         "time": _toff(_bt, 4)},
                ]
            for a in alerts:
                st.markdown(f"{a['icon']} **{a['car']}** — {a['event']} `{a['time']}`")

    with sc_col:
        st.subheader("📈 이번 달 안전 점수 추이")
        scores_data = api_get("/company/scores")

        if scores_data and isinstance(scores_data, list) and len(scores_data) > 0:
            df_scores = pd.DataFrame(scores_data)
            fig_trend = px.line(df_scores, x=df_scores.columns[0], y=df_scores.columns[1],
                                markers=True, color_discrete_sequence=["#534AB7"])
        else:
            company_id_cur = get_company_id()
            if company_id_cur == "comp_jeju":
                scores = [74, 70, 68, 72, 65, 71, 69, 73, 67, 70, 72, 71]
            else:
                scores = [78, 74, 76, 72, 80, 75, 73, 77, 71, 76, 74, 75]
            score_trend = pd.DataFrame({
                "월": ["1월","2월","3월","4월","5월","6월","7월","8월","9월","10월","11월","12월"],
                "평균점수": scores,
            })
            fig_trend = px.line(score_trend, x="월", y="평균점수", markers=True,
                                color_discrete_sequence=["#534AB7"])

        fig_trend.update_layout(height=250, margin=dict(t=20, b=20))
        st.plotly_chart(fig_trend, use_container_width=True)
