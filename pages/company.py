import streamlit as st
import pandas as pd
import plotly.express as px
import time
import json
import os as _os
from utils.auth import is_logged_in, get_company_name, get_role, get_company_id, is_online
from utils.sidebar import render_sidebar
from utils.api import api_get

if not is_logged_in():
    st.switch_page("app.py")

render_sidebar()
role = get_role()

# ── 자동 새로고침 (5초) ──
if "last_refresh" not in st.session_state:
    st.session_state["last_refresh"] = time.time()
if time.time() - st.session_state["last_refresh"] > 5:
    st.session_state["last_refresh"] = time.time()
    st.rerun()

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
    elif val == "관찰 중":
        return "background-color: #fff3cc; color: #854f0b; font-weight: bold"
    return ""

def time_offset(base_time_str: str, offset_minutes: int) -> str:
    try:
        h, m, s = map(int, base_time_str.split(":"))
        total = h * 60 + m - offset_minutes
        total = max(0, total)
        return f"{total // 60:02d}:{total % 60:02d}:{s:02d}"
    except Exception:
        return base_time_str

# ── active_session.json 파일에서 읽기 ──
active_session_data = {}
active_driver = None
try:
    active_file = _os.path.join(_os.getcwd(), "active_session.json")
    if _os.path.exists(active_file):
        with open(active_file, encoding="utf-8") as _f:
            active_session_data = json.load(_f)
        active_driver = active_session_data.get("user_id")
except Exception:
    pass

# ── 블랙리스트 상태 관리 (session_state) ──
if "blacklist_status" not in st.session_state:
    st.session_state["blacklist_status"] = {
        "서울-22-334455": "제한",
        "경기-09-778899": "관찰 중",
        "부산-14-223344": "제한",
    }
if "blacklist_data" not in st.session_state:
    st.session_state["blacklist_data"] = {
        "스카이렌터카": [
            {"순위": 1, "운전자": "홍길동", "면허번호": "서울-22-334455", "점수": 18, "상태": "제한"},
            {"순위": 2, "운전자": "이민재", "면허번호": "경기-09-778899", "점수": 29, "상태": "관찰 중"},
        ],
        "제주렌터카": [
            {"순위": 1, "운전자": "강동원", "면허번호": "부산-14-223344", "점수": 21, "상태": "제한"},
            {"순위": 2, "운전자": "박서준", "면허번호": "제주-07-112233", "점수": 34, "상태": "관찰 중"},
        ],
    }

# ── 시나리오 정보 ──
SCENARIO_INFO = {
    "driver1": {"차량번호": "12가 3456", "운전자": "김철수", "면허번호": "경기-12-345678", "company": "comp_sky"},
    "driver2": {"차량번호": "34나 7890", "운전자": "이영희", "면허번호": "서울-08-112233", "company": "comp_sky"},
    "driver3": {"차량번호": "11바 1234", "운전자": "박민수", "면허번호": "인천-15-667788", "company": "comp_jeju"},
    "driver4": {"차량번호": "22사 5678", "운전자": "최지현", "면허번호": "경남-03-990011", "company": "comp_jeju"},
}
company_map = {"comp_sky": "스카이렌터카", "comp_jeju": "제주렌터카"}

# ── 시간 기준 (active_session.json started_at 기준) ──
_base_t = active_session_data.get("started_at", time.strftime("%H:%M:%S"))

# ── 더미 데이터 ──
ALL_ALERTS = {
    "스카이렌터카": [
        {"세션ID": "SES-0421", "시간": time_offset(_base_t, 1), "심각도": "중간",  "이벤트": "전방 차량 접근 감지", "운전자": "이영희", "차량번호": "34나 7890"},
        {"세션ID": "SES-0420", "시간": time_offset(_base_t, 4), "심각도": "중간",  "이벤트": "급제동 감지",         "운전자": "김철수", "차량번호": "12가 3456"},
    ],
    "제주렌터카": [
        {"세션ID": "SES-0431", "시간": time_offset(_base_t, 2), "심각도": "중간",  "이벤트": "고속 주행 감지",     "운전자": "박민수", "차량번호": "11바 1234"},
        {"세션ID": "SES-0430", "시간": time_offset(_base_t, 6), "심각도": "높음",  "이벤트": "전방 차량 충돌 위험", "운전자": "최지현", "차량번호": "22사 5678"},
    ],
}

# ── DB에서 실제 danger 세션 읽어서 이벤트 로그 생성 ──
DRIVER_SESSION_MAP = {
    "driver1": {"세션": "sess_scenario_1_ecae33", "운전자": "김철수",  "면허번호": "경기-12-345678", "차량번호": "12가 3456", "company": "comp_sky"},
    "driver2": {"세션": "sess_scenario_2_8eebf6", "운전자": "이영희",  "면허번호": "서울-08-112233", "차량번호": "34나 7890", "company": "comp_sky"},
    "driver3": {"세션": "sess_scenario_3_70fae7", "운전자": "박민수",  "면허번호": "인천-15-667788", "차량번호": "11바 1234", "company": "comp_jeju"},
    "driver4": {"세션": "sess_test_99c74936",     "운전자": "최지현",  "면허번호": "경남-03-990011", "차량번호": "22사 5678", "company": "comp_jeju"},
}
DYNAMIC_CLASSES = {"Vehicle", "Human", "Two-wheeled Vehicle", "Wheelchair", "Stroller", "Shopping Cart", "Animal"}
API_BASE = "https://unfocusedly-pleurocarpous-gina.ngrok-free.dev"

def _has_danger_banner(session_id: str) -> bool:
    """연속 3프레임 이상 danger(동적 객체 기준) 있는지 확인"""
    try:
        r = requests.get(f"{API_BASE}/logs",
            params={"session_id": session_id, "limit": 10000},
            headers={"ngrok-skip-browser-warning": "true"}, timeout=10)
        frames = r.json().get("frames", [])
        consecutive = 0
        for f in sorted(frames, key=lambda x: x["frame_number"]):
            risks = [o["risk_level"] for o in f.get("objects", []) if o.get("class_name") in DYNAMIC_CLASSES]
            if "danger" in risks:
                consecutive += 1
                if consecutive >= 3:
                    return True
            else:
                consecutive = 0
    except Exception:
        pass
    return False

def _get_score(session_id: str) -> int:
    """세션 최종 점수 조회"""
    try:
        r = requests.get(f"{API_BASE}/company/scores",
            headers={"ngrok-skip-browser-warning": "true", "Authorization": f"Bearer {st.session_state.get('token', '')}"},
            timeout=5)
        scores = r.json()
        if isinstance(scores, list):
            for s in scores:
                if s.get("session_id") == session_id:
                    return s.get("final_score", 22)
    except Exception:
        pass
    return 22

# 실제 DB 기반 이벤트 로그 생성
_live_events = {"스카이렌터카": [], "제주렌터카": []}
_comp_name_map = {"comp_sky": "스카이렌터카", "comp_jeju": "제주렌터카"}
_event_label = {"driver4": "전방 차량 충돌 위험", "driver2": "전방 차량 접근 감지", "driver1": "급제동 감지", "driver3": "고속 주행 감지"}

for did, info in DRIVER_SESSION_MAP.items():
    if _has_danger_banner(info["세션"]):
        comp = _comp_name_map.get(info["company"], "")
        score = 22 if did == "driver4" else 78
        severity = "위험" if did == "driver4" else "경고"
        _live_events[comp].append({
            "시간": time_offset(_base_t, {"driver1": 4, "driver2": 1, "driver3": 2, "driver4": 6}.get(did, 5)),
            "운전자": info["운전자"],
            "면허번호": info["면허번호"],
            "차량번호": info["차량번호"],
            "이벤트": _event_label.get(did, "위험 이벤트"),
            "점수": score,
            "위험도": severity,
        })

ALL_EVENTS = _live_events if any(_live_events.values()) else {
    "스카이렌터카": [],
    "제주렌터카": [
        {"시간": time_offset(_base_t, 6), "운전자": "최지현", "면허번호": "경남-03-990011", "차량번호": "22사 5678", "이벤트": "전방 차량 충돌 위험", "점수": 22, "위험도": "위험"},
    ],
}

DUMMY_REPORTS = {
    "서울-22-334455": {"이름": "홍길동", "총점": 18, "총 이벤트": 7, "이벤트 목록": [
        {"시간": "2026-05-18 13:15:22", "이벤트": "충돌 위험 경고",          "감점": -15},
        {"시간": "2026-05-18 13:14:10", "이벤트": "급제동 – 브레이크 88%",   "감점": -15},
        {"시간": "2026-05-18 13:12:45", "이벤트": "급출발 – 가속도 4.2m/s²", "감점": -15},
        {"시간": "2026-05-18 13:10:30", "이벤트": "근접 과속",               "감점": -8},
        {"시간": "2026-05-18 13:08:15", "이벤트": "급제동",                  "감점": -12},
        {"시간": "2026-05-18 13:06:00", "이벤트": "급출발",                  "감점": -12},
        {"시간": "2026-05-18 13:04:30", "이벤트": "근접 급가속",             "감점": -5},
    ]},
    "경기-09-778899": {"이름": "이민재", "총점": 29, "총 이벤트": 4, "이벤트 목록": [
        {"시간": "2026-05-20 11:32:10", "이벤트": "급제동 – 브레이크 75%",   "감점": -15},
        {"시간": "2026-05-20 11:30:05", "이벤트": "보행자 근접 1.1m",        "감점": -10},
        {"시간": "2026-05-20 11:28:22", "이벤트": "급출발 – 가속도 3.8m/s²", "감점": -15},
        {"시간": "2026-05-20 11:26:00", "이벤트": "과속 주행",               "감점": -8},
    ]},
    "부산-14-223344": {"이름": "강동원", "총점": 21, "총 이벤트": 6, "이벤트 목록": [
        {"시간": "2026-05-22 10:45:33", "이벤트": "충돌 위험 경고",          "감점": -15},
        {"시간": "2026-05-22 10:43:20", "이벤트": "급제동 – 브레이크 91%",   "감점": -15},
        {"시간": "2026-05-22 10:41:10", "이벤트": "급출발 – 가속도 4.7m/s²", "감점": -15},
        {"시간": "2026-05-22 10:39:00", "이벤트": "근접 과속",               "감점": -8},
        {"시간": "2026-05-22 10:37:30", "이벤트": "급제동",                  "감점": -12},
        {"시간": "2026-05-22 10:35:00", "이벤트": "과속 주행",               "감점": -5},
    ]},
    "제주-07-112233": {"이름": "박서준", "총점": 34, "총 이벤트": 3, "이벤트 목록": [
        {"시간": "2026-05-25 09:22:15", "이벤트": "급제동 – 브레이크 70%",   "감점": -15},
        {"시간": "2026-05-25 09:20:00", "이벤트": "급출발 – 가속도 3.5m/s²", "감점": -15},
        {"시간": "2026-05-25 09:18:30", "이벤트": "과속 주행",               "감점": -8},
    ]},
}

score_data = pd.DataFrame({
    "월": ["1월","2월","3월","4월","5월","6월","7월","8월","9월","10월","11월","12월"],
    "평균점수": [72, 68, 75, 71, 78, 82, 79, 85, 81, 88, 84, 90],
})
distance_data = pd.DataFrame({
    "월": ["1월","2월","3월","4월","5월","6월","7월","8월","9월","10월","11월","12월"],
    "거리(km)": [1200, 1450, 1380, 1620, 1890, 2100, 2350, 2580, 2410, 2700, 2850, 3100],
})
event_stats = pd.DataFrame({
    "이벤트": ["충돌 위험", "급제동", "급출발", "과속"],
    "횟수": [8, 22, 15, 12],
})

# ── API 데이터 로딩 ──
api_events = api_get("/company/events")
api_blacklist = api_get("/company/blacklist")
api_scores = api_get("/company/scores")
api_notifications = api_get("/company/notifications")

# ── 업체 선택 ──
companies = ["스카이렌터카", "제주렌터카"]

st.title("🏢 Company Dashboard")
if is_online():
    st.caption("🟢 서버 연결됨")
else:
    st.caption("🟡 오프라인 모드")

if role == "admin":
    api_companies = api_get("/auth/companies")
    if api_companies and isinstance(api_companies, list) and len(api_companies) > 0:
        _names = [c.get("company_name", "") for c in api_companies if c.get("company_name")]
        if _names:
            companies = _names
        else:
            companies = ["스카이렌터카", "제주렌터카"]
    else:
        companies = ["스카이렌터카", "제주렌터카"]
    search_col, drop_col = st.columns([1, 2])
    with search_col:
        company_search = st.text_input("업체 검색", placeholder="업체명 입력...", key="company_search_1")
    with drop_col:
        filtered = [c for c in companies if not company_search or company_search in c]
        selected_company = st.selectbox("업체 선택", filtered if filtered else companies)
    st.markdown(f"**{selected_company}** 운행 현황")
else:
    selected_company = company_map.get(get_company_id(), "스카이렌터카")
    st.markdown(f"**{get_company_name()}** 운행 현황")

# ── 현재 운행 중인 차량 (해당 업체 전체) ──
comp_id_map = {"스카이렌터카": "comp_sky", "제주렌터카": "comp_jeju"}
current_comp_id = comp_id_map.get(selected_company, "comp_sky")
running_drivers = {k: v for k, v in SCENARIO_INFO.items() if v["company"] == current_comp_id}

RENTAL_START_TIME = {
    "driver1": "2026-06-02 09:15:00",
    "driver2": "2026-06-02 09:32:00",
    "driver3": "2026-06-02 10:05:00",
    "driver4": "2026-06-02 10:22:00",
}

if running_drivers:
    st.markdown("**🚗 현재 운행 중인 차량**")
    cols = st.columns(len(running_drivers))
    for i, (did, info) in enumerate(running_drivers.items()):
        with cols[i]:
            started = RENTAL_START_TIME.get(did, "2026-06-02 09:00:00")
            st.markdown(f"""
            <div style='border:1px solid #e2e8f0; border-radius:8px; padding:12px; background:#f8fafc;'>
                <div style='font-size:0.8rem; color:#555; font-weight:bold;'>운행 중</div>
                <div style='font-weight:bold; margin-top:4px;'>{info['차량번호']}</div>
                <div style='font-size:0.85rem; color:#555;'>{info['운전자']}</div>
                <div style='font-size:0.75rem; color:#888; margin-top:2px;'>시작: {started}</div>
            </div>
            """, unsafe_allow_html=True)

st.divider()

# ── 알림 + 블랙리스트 ──
if api_notifications and isinstance(api_notifications, list) and len(api_notifications) > 0:
    alerts = api_notifications
else:
    alerts = ALL_ALERTS.get(selected_company, [])

if api_events and isinstance(api_events, list) and len(api_events) > 0:
    events = api_events
else:
    events = ALL_EVENTS.get(selected_company, [])

blacklist_raw = st.session_state["blacklist_data"].get(selected_company, [])
# session_state 상태 반영
for item in blacklist_raw:
    item["상태"] = st.session_state["blacklist_status"].get(item["면허번호"], item["상태"])

col1, col2 = st.columns(2)

with col1:
    st.subheader("🚨 실시간 위험 알림")
    if alerts:
        # 컬럼 순서: 세션ID, 시간, 심각도, 이벤트, 운전자, 차량번호
        col_order = ["세션ID", "시간", "심각도", "이벤트", "운전자", "차량번호"]
        alerts_df = pd.DataFrame(alerts)
        existing_cols = [c for c in col_order if c in alerts_df.columns]
        alerts_df = alerts_df[existing_cols]
        if "심각도" in alerts_df.columns:
            styled_alerts = alerts_df.style.map(severity_color, subset=["심각도"])
            st.dataframe(styled_alerts, use_container_width=True, hide_index=True)
        else:
            st.dataframe(alerts_df, use_container_width=True, hide_index=True)
    else:
        st.success("위험 알림이 없습니다.")

with col2:
    st.subheader("🚫 블랙리스트 운전자 관리")
    if blacklist_raw:
        bl_df = pd.DataFrame(blacklist_raw)
        styled_bl = bl_df.style
        if "점수" in bl_df.columns:
            styled_bl = styled_bl.map(score_color, subset=["점수"])
        if "상태" in bl_df.columns:
            styled_bl = styled_bl.map(status_color, subset=["상태"])
        st.dataframe(styled_bl, use_container_width=True, hide_index=True)

        # 운전자 선택 → 리포트 + 상태 변경
        driver_options = [f"{item['운전자']} ({item['면허번호']})" for item in blacklist_raw]
        selected_bl_driver = st.selectbox("운전자 선택", driver_options, key="bl_driver_select")

        selected_idx = driver_options.index(selected_bl_driver)
        selected_item = blacklist_raw[selected_idx]
        license_no = selected_item["면허번호"]

        bc1, bc2 = st.columns(2)
        with bc1:
            if st.button("📋 리포트 보기", use_container_width=True, key="btn_report_view_1"):
                st.session_state["show_report"] = license_no
        with bc2:
            cur_status = st.session_state["blacklist_status"].get(license_no, selected_item["상태"])
            new_status = st.selectbox(
                "상태 변경",
                ["관찰 중", "제한", "해제"],
                index=["관찰 중", "제한", "해제"].index(cur_status) if cur_status in ["관찰 중", "제한", "해제"] else 0,
                key=f"status_select_{license_no}"
            )
            if new_status != cur_status:
                if new_status == "해제":
                    # 블랙리스트에서 제거
                    st.session_state["blacklist_data"][selected_company] = [
                        item for item in st.session_state["blacklist_data"][selected_company]
                        if item["면허번호"] != license_no
                    ]
                    if license_no in st.session_state["blacklist_status"]:
                        del st.session_state["blacklist_status"][license_no]
                    st.success(f"✅ {selected_item['운전자']} 블랙리스트 해제")
                else:
                    st.session_state["blacklist_status"][license_no] = new_status
                    st.success(f"✅ 상태 변경: {new_status}")
                st.rerun()
    else:
        st.success("블랙리스트 운전자가 없습니다.")

# ── 리포트 모달 ──
if st.session_state.get("show_report"):
    license_no = st.session_state["show_report"]
    if license_no in DUMMY_REPORTS:
        report = DUMMY_REPORTS[license_no]
        with st.expander(f"📋 {report['이름']} ({license_no}) 종합 리포트", expanded=True):
            rc1, rc2 = st.columns(2)
            rc1.metric("최종 점수", f"{report['총점']}점")
            rc2.metric("총 위험 이벤트", f"{report['총 이벤트']}건")
            st.dataframe(pd.DataFrame(report["이벤트 목록"]), use_container_width=True, hide_index=True)
            if st.button("닫기", key="btn_close_2"):
                st.session_state["show_report"] = None
                st.rerun()

st.divider()

# ── 이벤트 로그 ──
st.subheader("📋 스코어 이력 및 이벤트 로그")
st.caption("운전자 이름을 선택해 블랙리스트에 추가하거나 전·후 영상을 확인할 수 있습니다.")

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

        with st.expander(f"🎬 {ev.get('운전자', 'N/A')} ({ev.get('면허번호', 'N/A')}) | {ev.get('이벤트', '')} | {ev.get('시간', '')}", expanded=True):
            from pathlib import Path
            import tempfile, glob

            ev_license = ev.get("면허번호", "")
            ev_driver  = ev.get("운전자", "")
            ev_score   = ev.get("점수", 100)
            plate      = ev.get("차량번호", "")

            PLATE_SCENARIO = {"12가 3456": 1, "34나 7890": 2, "11바 1234": 3, "22사 5678": 4}
            DRIVER_ID = {1: "driver1", 2: "driver2", 3: "driver3", 4: "driver4"}
            scenario_num = PLATE_SCENARIO.get(plate, 1)
            driver_id = DRIVER_ID.get(scenario_num, "driver1")

            base = Path(_os.getcwd())
            tmp_dir = Path(tempfile.gettempdir())
            annotated_files = sorted(glob.glob(str(tmp_dir / f"ida_annotated_{driver_id}_*.mp4")))

            # 블랙리스트 추가 버튼
            is_already_bl = any(
                item["면허번호"] == ev_license
                for item in st.session_state["blacklist_data"].get(selected_company, [])
            )
            if not is_already_bl and ev_score < 80:
                if st.button(f"🚫 {ev_driver} 블랙리스트 추가 (관찰 중)", key=f"add_bl_{ev_license}", use_container_width=True):
                    existing = st.session_state["blacklist_data"].get(selected_company, [])
                    new_rank = len(existing) + 1
                    existing.append({
                        "순위": new_rank,
                        "운전자": ev_driver,
                        "면허번호": ev_license,
                        "점수": ev_score,
                        "상태": "관찰 중"
                    })
                    st.session_state["blacklist_data"][selected_company] = existing
                    st.session_state["blacklist_status"][ev_license] = "관찰 중"
                    st.success(f"✅ {ev_driver} 블랙리스트(관찰 중) 추가 완료!")
                    st.rerun()
            elif is_already_bl:
                st.info(f"ℹ️ {ev_driver}은 이미 블랙리스트에 등록되어 있습니다.")

            st.divider()

            # 시나리오4(충돌 위험)만 영상 클립 표시
            if plate == "22사 5678":
                col_v1, col_v2 = st.columns(2)
                with col_v1:
                    st.markdown("**📹 이벤트 전 (5초)**")
                    before_src = base / f"videos/test_scenario_{scenario_num}.mp4"
                    clip_before = tmp_dir / f"clip_before_{scenario_num}.mp4"
                    if not clip_before.exists() and before_src.exists():
                        import subprocess
                        subprocess.run([
                            "ffmpeg", "-y", "-i", str(before_src),
                            "-t", "5", "-c", "copy", str(clip_before)
                        ], capture_output=True)
                    if clip_before.exists():
                        st.video(str(clip_before))
                    elif before_src.exists():
                        st.video(str(before_src))
                    else:
                        st.info("영상 파일 없음")

                with col_v2:
                    st.markdown("**📹 이벤트 후 (끝까지)**")
                    after_src = Path(annotated_files[-1]) if annotated_files else (base / f"videos/test_scenario_{scenario_num}.mp4")
                    clip_after = tmp_dir / f"clip_after_{scenario_num}.mp4"
                    if not clip_after.exists() and after_src.exists():
                        import subprocess
                        subprocess.run([
                            "ffmpeg", "-y", "-i", str(after_src),
                            "-ss", "8", "-c", "copy", str(clip_after)
                        ], capture_output=True)
                    if clip_after.exists():
                        st.video(str(clip_after))
                    elif after_src.exists():
                        st.video(str(after_src))
                    else:
                        st.info("영상 파일 없음. 드라이버 대시보드에서 먼저 재생해주세요.")
            else:
                st.info("ℹ️ 위험 이벤트(DANGER)가 발생한 경우에만 영상 클립이 제공됩니다.")

else:
    if not events:
        st.success("위험 이벤트가 없습니다.")

st.divider()

# ── 반납 리포트 ──
st.subheader("📊 반납 리포트")
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
