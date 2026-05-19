import streamlit as st
import pandas as pd
import plotly.express as px
from utils.auth import is_logged_in, get_company_name, get_role, get_company_id, is_online
from utils.sidebar import render_sidebar
from utils.api import api_get

if not is_logged_in():
    st.switch_page("app.py")

render_sidebar()
role = get_role()

# ── 색상 함수 ──
def severity_color(val):
    if val == "높음":
        return "background-color: #ffcccc; color: #a32d2d; font-weight: bold"
    elif val == "중간":
        return "background-color: #fff3cc; color: #854f0b; font-weight: bold"
    elif val == "낮음":
        return "background-color: #ccf0d8; color: #085041; font-weight: bold"
    return ""

def danger_color(val):
    if val == "위험":
        return "background-color: #ffcccc; color: #a32d2d; font-weight: bold"
    elif val == "경고":
        return "background-color: #fff3cc; color: #854f0b; font-weight: bold"
    elif val == "안전":
        return "background-color: #ccf0d8; color: #085041; font-weight: bold"
    return ""

def score_color(val):
    if isinstance(val, (int, float)):
        if val < 30:
            return "color: #a32d2d; font-weight: bold"
        elif val < 50:
            return "color: #854f0b; font-weight: bold"
        elif val < 80:
            return "color: #185fa5; font-weight: bold"
        else:
            return "color: #085041; font-weight: bold"
    return ""

def status_color(val):
    if val == "제한":
        return "background-color: #ffcccc; color: #a32d2d; font-weight: bold"
    elif val == "정상":
        return "background-color: #ccf0d8; color: #085041; font-weight: bold"
    return ""

# ═══════════════════════════════════════
#  데이터 로딩 (API 우선 → 더미 폴백)
# ═══════════════════════════════════════

# 더미 데이터
DUMMY_ALERTS = {
    "스카이렌터카": [
        {"세션ID": "SES-0421", "차량번호": "12가 3456", "이벤트": "급제동 감지", "시간": "14:32:05", "심각도": "높음"},
        {"세션ID": "SES-0420", "차량번호": "34나 7890", "이벤트": "보행자 근접", "시간": "14:31:42", "심각도": "높음"},
        {"세션ID": "SES-0419", "차량번호": "56다 1234", "이벤트": "과속 주행",   "시간": "14:30:18", "심각도": "중간"},
        {"세션ID": "SES-0418", "차량번호": "78라 5678", "이벤트": "충돌 위험",   "시간": "14:29:55", "심각도": "높음"},
        {"세션ID": "SES-0417", "차량번호": "90마 9012", "이벤트": "급출발 감지", "시간": "14:28:30", "심각도": "중간"},
    ],
    "제주렌터카": [
        {"세션ID": "SES-0431", "차량번호": "11바 1234", "이벤트": "충돌 위험",   "시간": "14:32:00", "심각도": "높음"},
        {"세션ID": "SES-0430", "차량번호": "22사 5678", "이벤트": "급출발 감지", "시간": "14:30:00", "심각도": "중간"},
        {"세션ID": "SES-0429", "차량번호": "33아 9012", "이벤트": "정상 주행",   "시간": "14:28:00", "심각도": "낮음"},
    ],
}

DUMMY_EVENTS = {
    "스카이렌터카": [
        {"시간": "14:32:05", "운전자": "김철수", "면허번호": "경기-12-345678", "차량번호": "12가 3456", "이벤트": "급제동 – 브레이크 85%",  "점수": 23, "위험도": "위험"},
        {"시간": "14:31:42", "운전자": "이영희", "면허번호": "서울-08-112233", "차량번호": "34나 7890", "이벤트": "보행자 근접 1.2m",        "점수": 31, "위험도": "경고"},
        {"시간": "14:30:18", "운전자": "박민수", "면허번호": "인천-15-667788", "차량번호": "56다 1234", "이벤트": "과속 주행 48km/h",         "점수": 55, "위험도": "경고"},
        {"시간": "14:27:10", "운전자": "강민준", "면허번호": "경기-07-556677", "차량번호": "11바 1234", "이벤트": "정상 주행",               "점수": 88, "위험도": "안전"},
    ],
    "제주렌터카": [
        {"시간": "14:29:55", "운전자": "최지현", "면허번호": "경남-03-990011", "차량번호": "78라 5678", "이벤트": "충돌 위험 경고",           "점수": 22, "위험도": "위험"},
        {"시간": "14:28:30", "운전자": "정우성", "면허번호": "부산-19-223344", "차량번호": "90마 9012", "이벤트": "급출발 가속 3.9m/s²",     "점수": 44, "위험도": "경고"},
        {"시간": "14:27:10", "운전자": "강민준", "면허번호": "경기-07-556677", "차량번호": "11바 1234", "이벤트": "정상 주행",               "점수": 88, "위험도": "안전"},
    ],
}

DUMMY_BLACKLIST = {
    "스카이렌터카": [
        {"순위": 1, "운전자": "김철수", "면허번호": "경기-12-345678", "점수": 23, "상태": "제한"},
        {"순위": 2, "운전자": "이영희", "면허번호": "서울-08-112233", "점수": 31, "상태": "제한"},
        {"순위": 3, "운전자": "박민수", "면허번호": "인천-15-667788", "점수": 38, "상태": "정상"},
    ],
    "제주렌터카": [
        {"순위": 1, "운전자": "최지현", "면허번호": "경남-03-990011", "점수": 22, "상태": "제한"},
        {"순위": 2, "운전자": "정우성", "면허번호": "부산-19-223344", "점수": 29, "상태": "제한"},
    ],
}

DUMMY_REPORTS = {
    "경기-12-345678": {"이름": "김철수", "총점": 23, "총 이벤트": 8, "이벤트 목록": [
        {"시간": "14:32:05", "이벤트": "급제동 – 브레이크 85%",     "감점": -15},
        {"시간": "14:31:18", "이벤트": "급출발 – 가속도 4.1m/s²",   "감점": -15},
        {"시간": "14:30:55", "이벤트": "보행자 근접 1.0m + 급가속", "감점": -10},
        {"시간": "14:29:30", "이벤트": "급제동 – 브레이크 78%",     "감점": -12},
    ]},
    "서울-08-112233": {"이름": "이영희", "총점": 31, "총 이벤트": 5, "이벤트 목록": [
        {"시간": "14:31:42", "이벤트": "보행자 근접 1.2m",           "감점": -10},
        {"시간": "14:30:20", "이벤트": "급제동 – 브레이크 80%",     "감점": -12},
        {"시간": "14:29:10", "이벤트": "급출발 – 가속도 3.5m/s²",   "감점": -15},
    ]},
    "경남-03-990011": {"이름": "최지현", "총점": 22, "총 이벤트": 6, "이벤트 목록": [
        {"시간": "14:29:55", "이벤트": "충돌 위험 경고",             "감점": -15},
        {"시간": "14:28:40", "이벤트": "급제동 – 브레이크 90%",     "감점": -15},
        {"시간": "14:27:20", "이벤트": "급출발 – 가속도 4.5m/s²",   "감점": -15},
    ]},
}

# API에서 데이터 로딩
api_events = api_get("/company/events")
api_blacklist = api_get("/company/blacklist")
api_scores = api_get("/company/scores")
api_reports = api_get("/company/reports")
api_notifications = api_get("/company/notifications")

# ── 업체 선택 ──
companies = ["스카이렌터카", "제주렌터카"]
company_map = {"comp_sky": "스카이렌터카", "comp_jeju": "제주렌터카"}

st.title("🏢 Company Dashboard")

if is_online():
    st.caption("🟢 서버 연결됨")
else:
    st.caption("🟡 오프라인 모드")

if role == "admin":
    # admin은 업체 목록 API에서 가져오기
    api_companies = api_get("/auth/companies")
    if api_companies and isinstance(api_companies, list):
        companies = [c.get("company_name", "") for c in api_companies if c.get("company_name")]

    search_col, drop_col = st.columns([1, 2])
    with search_col:
        company_search = st.text_input("업체 검색", placeholder="업체명 입력...")
    with drop_col:
        filtered = [c for c in companies if not company_search or company_search in c]
        selected_company = st.selectbox("업체 선택", filtered if filtered else companies)
    st.markdown(f"**{selected_company}** 운행 현황")
else:
    selected_company = company_map.get(get_company_id(), "스카이렌터카")
    st.markdown(f"**{get_company_name()}** 운행 현황")

# 데이터 결정 (API 있으면 API, 없으면 더미)
if api_notifications and isinstance(api_notifications, list) and len(api_notifications) > 0:
    alerts = api_notifications
elif api_events and isinstance(api_events, list) and len(api_events) > 0:
    alerts = api_events[:5]
else:
    alerts = DUMMY_ALERTS.get(selected_company, [])

if api_events and isinstance(api_events, list) and len(api_events) > 0:
    events = api_events
else:
    events = DUMMY_EVENTS.get(selected_company, [])

if api_blacklist and isinstance(api_blacklist, list) and len(api_blacklist) > 0:
    blacklist = api_blacklist
else:
    blacklist = DUMMY_BLACKLIST.get(selected_company, [])

blacklist_reports = DUMMY_REPORTS  # 리포트는 더미 유지 (API 추후 연동)

score_data = pd.DataFrame({
    "월": ["1월","2월","3월","4월","5월","6월","7월","8월","9월","10월","11월","12월"],
    "평균점수": [72, 68, 75, 71, 78, 82, 79, 85, 81, 88, 84, 90],
})
distance_data = pd.DataFrame({
    "월": ["1월","2월","3월","4월","5월","6월","7월","8월","9월","10월","11월","12월"],
    "거리(km)": [1200, 1450, 1380, 1620, 1890, 2100, 2350, 2580, 2410, 2700, 2850, 3100],
})
event_stats = pd.DataFrame({
    "이벤트": ["충돌", "주차장 감지", "보행자 감지", "위험"],
    "횟수": [12, 34, 28, 8],
})

st.divider()

# ── 알림 + 블랙리스트 ──
col1, col2 = st.columns(2)

with col1:
    st.subheader("🚨 실시간 위험 알림")
    if alerts:
        alerts_df = pd.DataFrame(alerts)
        if "심각도" in alerts_df.columns:
            styled_alerts = alerts_df.style.map(severity_color, subset=["심각도"])
            st.dataframe(styled_alerts, use_container_width=True, hide_index=True)
        else:
            st.dataframe(alerts_df, use_container_width=True, hide_index=True)
    else:
        st.success("위험 알림이 없습니다.")

with col2:
    st.subheader("🚫 블랙리스트 운전자 관리")
    if blacklist:
        bl_df = pd.DataFrame(blacklist)
        style_cols = []
        if "점수" in bl_df.columns:
            style_cols.append(("점수", score_color))
        if "상태" in bl_df.columns:
            style_cols.append(("상태", status_color))

        styled_bl = bl_df.style
        for col_name, func in style_cols:
            styled_bl = styled_bl.map(func, subset=[col_name])
        st.dataframe(styled_bl, use_container_width=True, hide_index=True)
    else:
        st.success("블랙리스트 운전자가 없습니다.")

    st.markdown("**📄 블랙리스트 리포트 조회**")
    search_query = st.text_input("이름 또는 면허번호 검색", placeholder="예: 김철수 또는 경기-12-345678")
    filtered_reports = {
        k: v for k, v in blacklist_reports.items()
        if not search_query or search_query in v["이름"] or search_query in k
    }
    if filtered_reports:
        selected_license = st.selectbox(
            "운전자 선택",
            options=list(filtered_reports.keys()),
            format_func=lambda x: f"{filtered_reports[x]['이름']} ({x})"
        )
        if st.button("리포트 보기", use_container_width=True):
            st.session_state["show_report"] = selected_license
    else:
        st.warning("검색 결과가 없습니다.")

if st.session_state.get("show_report"):
    license_no = st.session_state["show_report"]
    if license_no in blacklist_reports:
        report = blacklist_reports[license_no]
        with st.expander(f"📋 {report['이름']} ({license_no}) 종합 리포트", expanded=True):
            rc1, rc2 = st.columns(2)
            rc1.metric("최종 점수", f"{report['총점']}점")
            rc2.metric("총 위험 이벤트", f"{report['총 이벤트']}건")
            st.dataframe(pd.DataFrame(report["이벤트 목록"]), use_container_width=True, hide_index=True)
            if st.button("닫기"):
                st.session_state["show_report"] = None
                st.rerun()

st.divider()

# ── 이벤트 로그 ──
st.subheader("📋 스코어 이력 및 이벤트 로그")
st.caption("행을 클릭하면 전·후 영상 클립을 확인할 수 있습니다.")

if events:
    events_df = pd.DataFrame(events)

    style_subsets = {}
    if "위험도" in events_df.columns:
        style_subsets["위험도"] = danger_color
    if "점수" in events_df.columns:
        style_subsets["점수"] = score_color

    styled_events = events_df.style
    for col_name, func in style_subsets.items():
        styled_events = styled_events.map(func, subset=[col_name])

    selected_row = st.dataframe(
        styled_events, use_container_width=True, hide_index=True,
        on_select="rerun", selection_mode="single-row",
    )

    if selected_row and selected_row.selection.rows:
        idx = selected_row.selection.rows[0]
        ev = events[idx]

        with st.expander(f"🎬 전·후 영상 클립 — {ev.get('운전자', 'N/A')} ({ev.get('면허번호', 'N/A')}) | {ev.get('시간', '')}", expanded=True):
            i1, i2, i3, i4 = st.columns(4)
            i1.metric("운전자",   ev.get("운전자", "N/A"))
            i2.metric("면허번호", ev.get("면허번호", "N/A"))
            i3.metric("이벤트",   ev.get("이벤트", "N/A"))
            i4.metric("점수",     f"{ev.get('점수', 'N/A')}점")

            st.divider()

            col_v1, col_v2 = st.columns(2)

            with col_v1:
                st.markdown("**📹 이벤트 전 (30초)**")
                st.markdown(f"""
                <div style='background:#1a1a2e; border-radius:10px; padding:32px 20px;
                            text-align:center; border:1px solid #3a3a5c;'>
                    <div style='font-size:2.5rem;'>▶</div>
                    <div style='color:#8888bb; font-size:0.85rem; margin-top:8px;'>
                        CAM-01 | 이벤트 발생 30초 전
                    </div>
                    <div style='color:#555588; font-size:0.75rem; margin-top:4px;'>
                        {ev.get('시간', '')} | {ev.get('차량번호', '')}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                st.caption("")
                if st.button("▶ 이벤트 전 영상 재생", key="btn_before", use_container_width=True):
                    st.session_state["video_modal"] = {"type": "before", "ev": ev}
                    st.rerun()

            with col_v2:
                st.markdown("**📹 이벤트 후 (30초)**")
                st.markdown(f"""
                <div style='background:#2e1a1a; border-radius:10px; padding:32px 20px;
                            text-align:center; border:1px solid #5c3a3a;'>
                    <div style='font-size:2.5rem;'>▶</div>
                    <div style='color:#bb8888; font-size:0.85rem; margin-top:8px;'>
                        CAM-01 | 이벤트 발생 30초 후
                    </div>
                    <div style='color:#a32d2d; font-size:0.75rem; margin-top:4px;'>
                        ⚠ {ev.get('이벤트', '')} 감지됨
                    </div>
                </div>
                """, unsafe_allow_html=True)
                st.caption("")
                if st.button("▶ 이벤트 후 영상 재생", key="btn_after", use_container_width=True):
                    st.session_state["video_modal"] = {"type": "after", "ev": ev}
                    st.rerun()

# ── 영상 플레이어 ──
if st.session_state.get("video_modal"):
    modal = st.session_state["video_modal"]
    ev    = modal["ev"]
    is_before = modal["type"] == "before"
    clip_label = "이벤트 전 30초" if is_before else "이벤트 후 30초"
    bg_color   = "#0d0d1a" if is_before else "#1a0d0d"
    border_col = "#3a3a5c" if is_before else "#5c3a3a"
    tag_color  = "#8888bb" if is_before else "#bb4444"

    st.divider()
    st.markdown(f"### 🎬 영상 플레이어 — {clip_label}")
    st.markdown(f"**{ev.get('운전자', '')}** ({ev.get('면허번호', '')}) | {ev.get('차량번호', '')} | {ev.get('시간', '')}")

    st.markdown(f"""
    <div style='background:{bg_color}; border-radius:12px; border:1px solid {border_col}; overflow:hidden;'>
        <div style='background:#000; aspect-ratio:16/9; display:flex; flex-direction:column;
                    align-items:center; justify-content:center; gap:10px; min-height:240px;'>
            <div style='font-size:4rem; opacity:0.35;'>📹</div>
            <div style='color:#555; font-size:0.9rem;'>영상 준비 중입니다</div>
            <div style='color:#444; font-size:0.75rem;'>FastAPI 서버 연동 후 실제 영상이 표시됩니다</div>
        </div>
        <div style='padding:10px 16px; display:flex; justify-content:space-between; align-items:center;'>
            <span style='color:{tag_color}; font-size:0.8rem; font-weight:bold;'>● {clip_label}</span>
            <span style='color:#555; font-size:0.8rem;'>CAM-01 | {ev.get('차량번호', '')}</span>
        </div>
        <div style='background:#222; height:4px; margin:0 16px 10px; border-radius:2px;'>
            <div style='background:#534AB7; width:0%; height:100%; border-radius:2px;'></div>
        </div>
        <div style='padding:4px 16px 14px; display:flex; align-items:center; gap:16px;'>
            <span style='color:#aaa; font-size:1.3rem; cursor:pointer;'>⏮</span>
            <span style='background:#534AB7; border-radius:50%; width:34px; height:34px;
                         display:inline-flex; align-items:center; justify-content:center;
                         cursor:pointer; font-size:0.9rem;'>▶</span>
            <span style='color:#aaa; font-size:1.3rem; cursor:pointer;'>⏭</span>
            <span style='color:#555; font-size:0.8rem;'>00:00 / 00:30</span>
            <span style='color:#555; font-size:0.8rem; margin-left:auto;'>속도: 1.0×</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.caption("")
    p1, p2, p3 = st.columns(3)
    p1.metric("이벤트", ev.get("이벤트", "N/A"))
    p2.metric("점수",   f"{ev.get('점수', 'N/A')}점")
    p3.metric("위험도", ev.get("위험도", "N/A"))

    if st.button("✕ 플레이어 닫기", use_container_width=True):
        st.session_state["video_modal"] = None
        st.rerun()

else:
    if not events:
        st.success("위험 이벤트가 없습니다.")

st.divider()

# ── 반납 리포트 ──
st.subheader("📊 반납 리포트")

# API에서 점수 데이터 가져오기
if api_scores and isinstance(api_scores, list) and len(api_scores) > 0:
    score_data = pd.DataFrame(api_scores)

col3, col4, col5 = st.columns(3)
with col3:
    fig1 = px.line(distance_data, x="월", y="거리(km)", title="누적 안전주행 거리",
                   markers=True, color_discrete_sequence=["#534AB7"])
    fig1.update_layout(height=250, margin=dict(t=40, b=20))
    st.plotly_chart(fig1, use_container_width=True)
with col4:
    fig2 = px.bar(score_data, x="월", y="평균점수", title="월별 평균 안전주행 점수",
                  color_discrete_sequence=["#1D9E75"])
    fig2.update_layout(height=250, margin=dict(t=40, b=20))
    st.plotly_chart(fig2, use_container_width=True)
with col5:
    fig3 = px.bar(event_stats, x="이벤트", y="횟수", title="최근 이벤트 통계",
                  color="이벤트", color_discrete_sequence=["#E24B4A","#378ADD","#EF9F27","#BA7517"])
    fig3.update_layout(height=250, margin=dict(t=40, b=20), showlegend=False)
    st.plotly_chart(fig3, use_container_width=True)
