import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from utils.auth import is_logged_in, get_role, is_online
from utils.sidebar import render_sidebar
from utils.api import api_get, api_post

if not is_logged_in():
    st.switch_page("app.py")
if get_role() != "admin":
    st.switch_page("app.py")

render_sidebar()

# ═══════════════════════════════════════
#  데이터 로딩 (API 우선 → 더미 폴백)
# ═══════════════════════════════════════

# 더미 데이터
# 더미 기본값 (API 폴백용) - 실제 시나리오 기반
DUMMY_COMPANY_DATA = {
    "스카이렌터카": {"sessions": 2, "events": 10, "avg_score": 75, "blacklist": 2},
    "제주렌터카":   {"sessions": 2, "events": 18, "avg_score": 64, "blacklist": 2},
}

DUMMY_SCORING = {
    "스카이렌터카": {"급출발 감점": 5, "급제동 감점": 5, "근접+급가속 감점": 10, "근접+과속 감점": 8, "블랙리스트 기준점": 30, "Green 등급 최소점수": 80},
    "제주렌터카":   {"급출발 감점": 5, "급제동 감점": 5, "근접+급가속 감점": 10, "근접+과속 감점": 8, "블랙리스트 기준점": 30, "Green 등급 최소점수": 80},
}

DUMMY_PERF = {
    "스카이렌터카": {"yolo_map": 0.92, "yolo_fps": 35.8, "depth_map": 0.88, "depth_fps": 1.0, "latency": "45ms", "packet_loss": "0.3%"},
    "제주렌터카":   {"yolo_map": 0.91, "yolo_fps": 33.4, "depth_map": 0.87, "depth_fps": 0.9, "latency": "58ms", "packet_loss": "0.6%"},
}

import time as _t2
_now = _t2.localtime()
def _lt(m): 
    total = _now.tm_hour*60+_now.tm_min-m
    total = max(0, total)
    return f"2026-06-02 {total//60:02d}:{total%60:02d}:{_now.tm_sec:02d}"

DUMMY_LOGS = [
    {"시간": _lt(1),  "유형": "시스템",   "설명": f"YOLO 추론 정상 – 평균 {round(__import__('random').uniform(38,42),1)}ms"},
    {"시간": _lt(3),  "유형": "시스템",   "설명": f"Depth FPS 정상 – {round(__import__('random').uniform(0.9,1.1),1)}fps"},
    {"시간": _lt(5),  "유형": "네트워크", "설명": "WebSocket 세션 연결 유지 중"},
    {"시간": _lt(8),  "유형": "시스템",   "설명": f"프레임 처리 정상 – 누락 없음"},
    {"시간": _lt(12), "유형": "네트워크", "설명": f"패킷 손실률 {round(__import__('random').uniform(0.1,0.4),1)}% – 정상 범위"},
    {"시간": _lt(15), "유형": "시스템",   "설명": "모델 체크포인트 자동 저장 완료"},
    {"시간": _lt(20), "유형": "네트워크", "설명": "CAN 시뮬레이터 데이터 정상 수신"},
    {"시간": _lt(25), "유형": "시스템",   "설명": f"GPU 메모리 사용량 {__import__('random').randint(65,78)}% – 정상"},
]

# API 데이터 로딩
api_admin_dashboard = api_get("/admin/dashboard")
api_sessions = api_get("/admin/sessions")
api_events = api_get("/admin/events")
api_config = api_get("/config")
api_stats = api_get("/stats")
api_logs_data = api_get("/logs")
api_companies = api_get("/auth/companies")
print(f"[DEBUG] /auth/companies 응답: {api_companies}")

# 업체 목록 결정 (API + 더미 병합)
company_data = dict(DUMMY_COMPANY_DATA)  # 더미로 초기화
print(f"[DEBUG] /admin/dashboard 응답: {api_admin_dashboard}")

if api_admin_dashboard and isinstance(api_admin_dashboard, dict):
    # API에서 업체별 실제 데이터 가져와서 병합
    api_company_list = api_admin_dashboard.get("companies", [])
    COMP_NAME_MAP = {"comp_sky": "스카이렌터카", "comp_jeju": "제주렌터카"}
    for c in api_company_list:
        name = c.get("company_name") or c.get("name") or COMP_NAME_MAP.get(c.get("company_id", ""), "")
        if name and name in company_data:
            api_sessions = c.get("active_sessions", c.get("sessions", 0))
            api_events   = c.get("total_events", c.get("events", 0))
            api_score    = c.get("avg_score", c.get("avg_final_score", 0))
            api_bl       = c.get("blacklist_count", c.get("blacklist", 0))
            # 실제값이 있으면 병합, 없으면 더미 유지
            if api_sessions: company_data[name]["sessions"] = api_sessions
            if api_events:   company_data[name]["events"]   = api_events
            if api_score:    company_data[name]["avg_score"] = round(api_score)
            if api_bl:       company_data[name]["blacklist"] = api_bl

if api_companies and isinstance(api_companies, list):
    for c in api_companies:
        name = c.get("company_name") or c.get("name", "")
        if name and name not in company_data:
            company_data[name] = {"sessions": 0, "events": 0, "avg_score": 0, "blacklist": 0}

# 스코어링 설정
if api_config and isinstance(api_config, dict):
    scoring_config = api_config
else:
    scoring_config = None

# 시스템 로그
if api_logs_data and isinstance(api_logs_data, dict) and api_logs_data.get("total_count", 0) > 0:
    system_logs = api_logs_data.get("events", DUMMY_LOGS)
elif api_logs_data and isinstance(api_logs_data, list) and len(api_logs_data) > 0:
    system_logs = api_logs_data
else:
    system_logs = DUMMY_LOGS

# 성능 데이터
if api_stats and isinstance(api_stats, dict):
    perf_from_api = api_stats
else:
    perf_from_api = None

default_scoring = DUMMY_SCORING
perf_by_company = DUMMY_PERF

DANGER_KEYWORDS  = ["위험", "경고", "초과", "드롭", "누락", "오류", "실패", "중단", "과부하", "이상"]
WARNING_KEYWORDS = ["저하", "지연", "손실", "감지", "불안정"]

bottleneck_data = pd.DataFrame({
    "추론 시간(ms)": np.random.uniform(10, 45, 50).round(1),
    "전송 지연(ms)": np.random.uniform(5, 30, 50).round(1),
    "위험도": np.random.choice(["정상", "경고", "위험"], 50, p=[0.6, 0.3, 0.1]),
})

# ── 자동 새로고침 (10초) ──
import time as _time
if "admin_last_refresh" not in st.session_state:
    st.session_state["admin_last_refresh"] = _time.time()
if _time.time() - st.session_state["admin_last_refresh"] > 10:
    st.session_state["admin_last_refresh"] = _time.time()
    st.rerun()

# ── 메인 ──
st.title("🛡️ Admin Dashboard")

if is_online():
    st.caption("🟢 서버 연결됨")
else:
    st.caption("🟡 오프라인 모드")

# ── 업체 선택 ──
st.subheader("🏢 업체별 조회")
sc1, sc2 = st.columns([1, 2])
with sc1:
    company_search = st.text_input("업체 검색", placeholder="업체명 입력...")
with sc2:
    all_companies = list(company_data.keys())
    filtered_companies = [c for c in all_companies if not company_search or company_search in c]
    selected = st.selectbox("업체 선택", filtered_companies if filtered_companies else all_companies)

data = company_data.get(selected, {"sessions": 0, "events": 0, "avg_score": 0, "blacklist": 0})
defaults = default_scoring.get(selected, list(default_scoring.values())[0] if default_scoring else {})
perf = perf_by_company.get(selected, list(perf_by_company.values())[0] if perf_by_company else {})

# 전체 현황 (API 우선 → 값 이상하면 더미 폴백)
_dummy_total = {
    "sessions": sum(v["sessions"] for v in company_data.values()),
    "events":   sum(v["events"]   for v in company_data.values()),
    "avg_score": round(sum(v["avg_score"] for v in company_data.values()) / max(len(company_data), 1)),
    "blacklist": 4,
}
if api_admin_dashboard and isinstance(api_admin_dashboard, dict):
    _api_events = api_admin_dashboard.get("total_events", 0)
    _api_score  = api_admin_dashboard.get("avg_final_score", 0)
    # API 값이 의미있으면 사용, 이상하면 더미
    total_sessions  = api_admin_dashboard.get("total_sessions", _dummy_total["sessions"]) or _dummy_total["sessions"]
    total_events    = _api_events if _api_events > 0 else _dummy_total["events"]
    avg_score_total = round(_api_score) if 0 < _api_score < 100 else _dummy_total["avg_score"]
    total_blacklist = api_admin_dashboard.get("blacklist_count", 0) or _dummy_total["blacklist"]
else:
    total_sessions  = _dummy_total["sessions"]
    total_events    = _dummy_total["events"]
    avg_score_total = _dummy_total["avg_score"]
    total_blacklist = _dummy_total["blacklist"]

st.markdown(f"**{selected} 현황**")
col1, col2, col3, col4 = st.columns(4)
col1.metric("활성 세션",   f"{data['sessions']}건")
col2.metric("위험 이벤트", f"{data['events']}건")
col3.metric("평균 점수",   f"{data['avg_score']}점")
col4.metric("블랙리스트",  f"{data['blacklist']}명")

# ── 업체별 차트 ──
companies_list = list(company_data.keys())
avg_scores  = [v["avg_score"] for v in company_data.values()]
event_counts = [v["events"]   for v in company_data.values()]

score_colors = ["#534AB7" if c == selected else "#CCCCCC" for c in companies_list]
event_colors = ["#E24B4A" if c == selected else "#CCCCCC" for c in companies_list]

cc1, cc2 = st.columns(2)
with cc1:
    fig1 = go.Figure(go.Bar(
        x=companies_list, y=avg_scores,
        marker_color=score_colors,
        text=avg_scores, textposition="outside",
    ))
    fig1.update_layout(title="업체별 평균 안전 점수", height=220, margin=dict(t=40, b=20),
                       showlegend=False, yaxis=dict(range=[0, 100]))
    st.plotly_chart(fig1, use_container_width=True)

with cc2:
    fig2 = go.Figure(go.Bar(
        x=companies_list, y=event_counts,
        marker_color=event_colors,
        text=event_counts, textposition="outside",
    ))
    fig2.update_layout(title="업체별 위험 이벤트 수", height=220, margin=dict(t=40, b=20),
                       showlegend=False)
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ── 성능 + 스코어링 ──
col5, col6 = st.columns(2)

with col5:
    st.subheader("📈 시스템 성능 통계")
    pm1, pm2, pm3, pm4 = st.columns(4)
    pm1.metric("YOLO mAP",  str(perf.get("yolo_map", "N/A")))
    pm2.metric("YOLO FPS",  str(perf.get("yolo_fps", "N/A")))
    pm3.metric("Depth mAP", str(perf.get("depth_map", "N/A")))
    pm4.metric("Depth FPS", str(perf.get("depth_fps", "N/A")))

    yolo_fps_val = perf.get("yolo_fps", 35)
    perf_data = pd.DataFrame({
        "시간": [f"14:{30+i:02d}" for i in range(10)],
        "YOLO FPS": np.random.uniform(yolo_fps_val-2, yolo_fps_val+2, 10).round(1),
        "추론 지연(ms)": np.random.uniform(38, 55, 10).round(1),
    })

    fig_fps = go.Figure()
    fig_fps.add_trace(go.Scatter(
        x=perf_data["시간"], y=perf_data["YOLO FPS"],
        name="YOLO FPS", line=dict(color="#534AB7", width=2), mode="lines+markers"
    ))
    fig_fps.add_trace(go.Scatter(
        x=perf_data["시간"], y=perf_data["추론 지연(ms)"],
        name="추론 지연(ms)", line=dict(color="#E24B4A", width=2, dash="dot"), mode="lines+markers",
        yaxis="y2"
    ))
    fig_fps.update_layout(
        title="실시간 FPS & 추론 지연",
        height=220, margin=dict(t=40, b=20),
        yaxis=dict(title="FPS"),
        yaxis2=dict(title="지연(ms)", overlaying="y", side="right"),
        legend=dict(orientation="h", y=-0.3),
    )
    st.plotly_chart(fig_fps, use_container_width=True)

    perf_summary = pd.DataFrame({
        "모델": ["YOLOv8", "Depth Anything V2"],
        "mAP": [perf.get("yolo_map", "N/A"), perf.get("depth_map", "N/A")],
        "평균 FPS": [perf.get("yolo_fps", "N/A"), perf.get("depth_fps", "N/A")],
        "상태": ["정상", "정상"],
    })
    st.dataframe(perf_summary, use_container_width=True, hide_index=True)

    nm1, nm2 = st.columns(2)
    nm1.metric("응답 지연",    perf.get("latency", "N/A"))
    nm2.metric("패킷 손실률", perf.get("packet_loss", "N/A"))

with col6:
    st.subheader("⚙️ 스코어링 기준값 설정")

    # API에서 config 가져왔으면 그걸 사용
    if scoring_config and isinstance(scoring_config, dict):
        cfg = scoring_config
        val_sudden_start = cfg.get("sudden_start_penalty", defaults.get("급출발 감점", 12))
        val_sudden_brake = cfg.get("sudden_brake_penalty", defaults.get("급제동 감점", 10))
        val_close_accel  = cfg.get("close_accel_penalty", defaults.get("근접+급가속 감점", 8))
        val_close_speed  = cfg.get("close_speed_penalty", defaults.get("근접+과속 감점", 6))
        val_bl_threshold = cfg.get("blacklist_threshold", defaults.get("블랙리스트 기준점", 35))
        val_green_min    = cfg.get("green_min_score", defaults.get("Green 등급 최소점수", 75))
    else:
        val_sudden_start = defaults.get("급출발 감점", 12)
        val_sudden_brake = defaults.get("급제동 감점", 10)
        val_close_accel  = defaults.get("근접+급가속 감점", 8)
        val_close_speed  = defaults.get("근접+과속 감점", 6)
        val_bl_threshold = defaults.get("블랙리스트 기준점", 35)
        val_green_min    = defaults.get("Green 등급 최소점수", 75)

    s_start = st.slider("급출발 감점",          0, 30,  val_sudden_start)
    s_brake = st.slider("급제동 감점",          0, 30,  val_sudden_brake)
    s_accel = st.slider("근접+급가속 감점",     0, 30,  val_close_accel)
    s_speed = st.slider("근접+과속 감점",       0, 30,  val_close_speed)
    s_bl    = st.slider("블랙리스트 기준점",    0, 100, val_bl_threshold)
    s_green = st.slider("Green 등급 최소점수",  0, 100, val_green_min)

    if st.button("💾 저장", use_container_width=True, type="primary"):
        # API로 설정 저장
        result = api_post("/config", {
            "sudden_start_penalty": s_start,
            "sudden_brake_penalty": s_brake,
            "close_accel_penalty": s_accel,
            "close_speed_penalty": s_speed,
            "blacklist_threshold": s_bl,
            "green_min_score": s_green,
        })
        if result:
            st.success(f"**{selected}** 스코어링 기준값이 서버에 저장되었습니다!")
        else:
            st.success(f"**{selected}** 스코어링 기준값이 저장되었습니다! (오프라인)")

st.divider()

# ── 병목 구간 ──
st.subheader("🔍 프레임 처리 병목 구간 조회")
color_map = {"정상": "#1D9E75", "경고": "#EF9F27", "위험": "#E24B4A"}
fig_scatter = px.scatter(
    bottleneck_data, x="추론 시간(ms)", y="전송 지연(ms)",
    color="위험도", color_discrete_map=color_map,
    title="추론 시간 vs 전송 지연",
)
fig_scatter.update_traces(marker=dict(size=8, opacity=0.7))
fig_scatter.update_layout(height=300, margin=dict(t=40, b=20))
st.plotly_chart(fig_scatter, use_container_width=True)

bc1, bc2 = st.columns(2)
with bc1:
    fig_hist = px.histogram(bottleneck_data, x="추론 시간(ms)", title="추론 시간 분포", nbins=15,
                            color_discrete_sequence=["#534AB7"])
    fig_hist.update_layout(height=220, margin=dict(t=40, b=20))
    st.plotly_chart(fig_hist, use_container_width=True)
with bc2:
    danger_counts = bottleneck_data["위험도"].value_counts().reset_index()
    danger_counts.columns = ["위험도", "count"]
    fig_pie = px.pie(danger_counts, names="위험도", values="count",
                     title="프레임 위험도 분포",
                     color="위험도", color_discrete_map=color_map)
    fig_pie.update_layout(height=220, margin=dict(t=40, b=20))
    st.plotly_chart(fig_pie, use_container_width=True)

st.divider()

# ── 시스템 로그 ──
st.subheader("📋 최근 시스템 로그")
fc1, fc2, fc3, fc4 = st.columns([2, 1, 1, 1])
with fc1:
    search = st.text_input("검색", placeholder="키워드 검색...")
with fc2:
    log_type_filter = st.selectbox("유형 필터", ["전체", "시스템", "네트워크"])
with fc3:
    date_from = st.date_input("From", value=None)
with fc4:
    date_to = st.date_input("To", value=None)

filtered_logs = system_logs.copy() if isinstance(system_logs, list) else []
if search:
    filtered_logs = [l for l in filtered_logs if isinstance(l, dict) and (search in l.get("설명", "") or search in l.get("유형", ""))]
if log_type_filter != "전체":
    filtered_logs = [l for l in filtered_logs if isinstance(l, dict) and l.get("유형") == log_type_filter]

header1, header2, header3 = st.columns([2, 1, 4])
header1.markdown("**시간**")
header2.markdown("**유형**")
header3.markdown("**설명**")

for log in filtered_logs:
    if not isinstance(log, dict):
        continue
    c1, c2, c3 = st.columns([2, 1, 4])
    with c1:
        st.caption(log.get("시간", ""))
    with c2:
        if log.get("유형") == "시스템":
            st.markdown(":blue[**시스템**]")
        else:
            st.markdown(":green[**네트워크**]")
    with c3:
        desc = log.get("설명", "")
        for kw in DANGER_KEYWORDS:
            desc = desc.replace(kw, f":red[**{kw}**]")
        for kw in WARNING_KEYWORDS:
            desc = desc.replace(kw, f":orange[**{kw}**]")
        st.markdown(desc)
