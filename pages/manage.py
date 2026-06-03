import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from utils.auth import is_logged_in, get_role, get_company_name, get_company_id, is_online
from utils.sidebar import render_sidebar
from utils.api import api_get, api_post

if not is_logged_in() or get_role() not in ["company", "admin"]:
    st.switch_page("app.py")

render_sidebar()

role = get_role()
is_admin = role == "admin"

if is_admin:
    st.title("🏢 업체 관리")
else:
    st.title("📋 운영 관리")

if is_online():
    st.caption("🟢 서버 연결됨")
else:
    st.caption("🟡 오프라인 — 데모 데이터 모드")

# ═══════════════════════════════════════
#  관리자: 업체 등록만
# ═══════════════════════════════════════
if is_admin:
    st.subheader("등록 업체 목록")

    if "companies" not in st.session_state:
        st.session_state["companies"] = [
            {"name": "스카이렌터카", "company_id": "comp_sky",  "contact": "02-1234-5678", "vehicles": 5, "registered": "2025-01-10"},
            {"name": "제주렌터카",   "company_id": "comp_jeju", "contact": "064-987-6543", "vehicles": 4, "registered": "2025-02-15"},
        ]

    companies_api = api_get("/auth/companies")

    if companies_api and isinstance(companies_api, list):
        if len(companies_api) > 0:
            df_comp = pd.DataFrame(companies_api)
            st.dataframe(df_comp, use_container_width=True, hide_index=True)
        else:
            st.info("등록된 업체가 없습니다.")
        comp_count = len(companies_api)
    else:
        demo_companies = st.session_state["companies"]
        df_comp = pd.DataFrame(demo_companies)
        st.dataframe(df_comp, use_container_width=True, hide_index=True)
        comp_count = len(demo_companies)

    st.metric("등록 업체 수", f"{comp_count}개")

    st.divider()
    st.subheader("➕ 신규 업체 등록")

    with st.form("add_company", clear_on_submit=True):
        fc1, fc2 = st.columns(2)
        new_comp_name = fc1.text_input("업체명", placeholder="예: 한라렌터카")
        new_comp_id   = fc2.text_input("업체 ID", placeholder="예: comp_halla")
        fc3, fc4 = st.columns(2)
        new_comp_username = fc3.text_input("로그인 계정 ID", placeholder="예: halla_rental")
        new_comp_password = fc4.text_input("로그인 비밀번호", type="password", placeholder="비밀번호 설정")

        submitted_comp = st.form_submit_button("업체 등록", use_container_width=True, type="primary")
        if submitted_comp:
            if new_comp_name and new_comp_id and new_comp_username and new_comp_password:
                result = api_post("/auth/accounts", {
                    "username": new_comp_username, "password": new_comp_password,
                    "role": "company", "company_id": new_comp_id, "company_name": new_comp_name
                })
                if result:
                    st.success(f"✅ {new_comp_name} 업체 등록 완료! (로그인: {new_comp_username})")
                    st.rerun()
                else:
                    st.warning("⚠️ 서버 연결 실패 — 오프라인에서는 업체 등록이 저장되지 않습니다.")
            else:
                st.error("업체명, 업체 ID, 로그인 계정, 비밀번호를 모두 입력해주세요.")

    st.stop()

# ═══════════════════════════════════════
#  업체: 렌탈 · 차량 · 고객 관리
# ═══════════════════════════════════════
company_id = get_company_id()  # "comp_sky" / "comp_jeju" 등

# 회사별 더미 데이터 정의 (company.py 대시보드와 동기화)
_DUMMY_VEHICLES = {
    "comp_sky": [
        {"plate": "12가 3456", "model": "현대 아반떼", "year": 2024, "status": "대여중", "registered": "2025-01-15"},
        {"plate": "34나 7890", "model": "기아 K5",     "year": 2023, "status": "대여중", "registered": "2025-02-20"},
        {"plate": "56다 1234", "model": "현대 쏘나타", "year": 2024, "status": "대기",   "registered": "2025-03-10"},
        {"plate": "78라 5678", "model": "기아 셀토스", "year": 2025, "status": "정비중", "registered": "2025-04-05"},
        {"plate": "90마 9012", "model": "현대 투싼",   "year": 2023, "status": "대기",   "registered": "2025-05-01"},
    ],
    "comp_jeju": [
        {"plate": "11바 1234", "model": "기아 카니발",   "year": 2024, "status": "대여중", "registered": "2025-02-10"},
        {"plate": "22사 5678", "model": "현대 스타리아", "year": 2023, "status": "대여중", "registered": "2025-03-05"},
        {"plate": "33아 9012", "model": "기아 쏘렌토",   "year": 2024, "status": "대기",   "registered": "2025-04-20"},
        {"plate": "44아 3456", "model": "현대 팰리세이드","year": 2025, "status": "대기",   "registered": "2025-05-10"},
    ],
}
_DUMMY_CUSTOMERS = {
    "comp_sky": [
        {"name": "김철수", "phone": "010-1234-5678", "license": "경기-12-345678", "blacklist": False, "registered": "2025-01-20", "rentals": 8},
        {"name": "이영희", "phone": "010-9876-5432", "license": "서울-08-112233", "blacklist": False, "registered": "2025-02-15", "rentals": 5},
        {"name": "홍길동", "phone": "010-2345-6789", "license": "서울-22-334455", "blacklist": True,  "registered": "2024-11-10", "rentals": 12},
        {"name": "이민재", "phone": "010-3456-7890", "license": "경기-09-778899", "blacklist": True,  "registered": "2024-12-05", "rentals": 9},
    ],
    "comp_jeju": [
        {"name": "박민수", "phone": "010-5555-1234", "license": "인천-15-667788", "blacklist": False, "registered": "2025-02-20", "rentals": 4},
        {"name": "최지현", "phone": "010-2233-4455", "license": "경남-03-990011", "blacklist": False, "registered": "2025-03-15", "rentals": 3},
        {"name": "강동원", "phone": "010-4567-8901", "license": "부산-14-223344", "blacklist": True,  "registered": "2024-10-20", "rentals": 7},
        {"name": "박서준", "phone": "010-5678-9012", "license": "제주-07-112233", "blacklist": True,  "registered": "2024-11-30", "rentals": 5},
    ],
}
_DUMMY_RENTALS = {
    "comp_sky": [
        {"customer": "김철수", "plate": "12가 3456", "start": "2026-06-01", "end": "2026-06-05", "status": "진행중", "session_id": "sess_941291c069fc"},
        {"customer": "이영희", "plate": "34나 7890", "start": "2026-06-01", "end": "2026-06-04", "status": "진행중", "session_id": "sess_c5adc3d33164"},
    ],
    "comp_jeju": [
        {"customer": "박민수", "plate": "11바 1234", "start": "2026-06-01", "end": "2026-06-06", "status": "진행중", "session_id": "sess_5324ba7103e4"},
        {"customer": "최지현", "plate": "22사 5678", "start": "2026-06-01", "end": "2026-06-03", "status": "진행중", "session_id": "sess_test_99c74936"},
    ],
}

# 회사별 session_state 키 사용 (다른 회사 데이터와 혼재 방지)
_vkey = f"vehicles_{company_id}"
_ckey = f"customers_{company_id}"
_rkey = f"rentals_{company_id}"

# 더미 데이터 버전 관리 (변경 시 캐시 강제 초기화)
_DATA_VERSION = "v5"
if st.session_state.get("_data_version") != _DATA_VERSION:
    for k in [_vkey, _ckey, _rkey, "vehicles", "customers", "rentals"]:
        st.session_state.pop(k, None)
    st.session_state["_data_version"] = _DATA_VERSION

if _vkey not in st.session_state:
    st.session_state[_vkey] = _DUMMY_VEHICLES.get(company_id, _DUMMY_VEHICLES["comp_sky"])
if _ckey not in st.session_state:
    st.session_state[_ckey] = _DUMMY_CUSTOMERS.get(company_id, _DUMMY_CUSTOMERS["comp_sky"])
if _rkey not in st.session_state:
    st.session_state[_rkey] = _DUMMY_RENTALS.get(company_id, _DUMMY_RENTALS["comp_sky"])

# 이후 코드에서 공통으로 쓸 수 있게 alias
if "vehicles" not in st.session_state or st.session_state.get("_last_company") != company_id:
    st.session_state["vehicles"] = st.session_state[_vkey]
    st.session_state["customers"] = st.session_state[_ckey]
    st.session_state["rentals"] = st.session_state[_rkey]
    st.session_state["_last_company"] = company_id

tab_rental, tab_vehicle, tab_customer = st.tabs(["📋 렌탈 관리", "🚗 차량 관리", "👤 고객 관리"])

# ───────────────────────────────────────
#  렌탈 관리
# ───────────────────────────────────────
with tab_rental:
    st.subheader("현재 렌탈 현황")

    sessions_api = api_get("/company/sessions")
    if sessions_api and isinstance(sessions_api, list):
        rentals = sessions_api
        r_active = sum(1 for r in rentals if r.get("status") == "active")
    else:
        rentals = st.session_state["rentals"]
        r_active = sum(1 for r in rentals if r.get("status") in ["진행중", "active"])

    rc1, rc2, rc3 = st.columns(3)
    rc1.metric("전체 렌탈", f"{len(rentals)}건")
    rc2.metric("진행 중", f"{r_active}건")
    rc3.metric("완료", f"{len(rentals) - r_active}건")

    st.divider()

    if rentals:
        df_r = pd.DataFrame(rentals)
        st.dataframe(df_r, use_container_width=True, hide_index=True)
    else:
        st.info("렌탈 내역이 없습니다.")

    st.divider()
    active = [r for r in st.session_state["rentals"] if r.get("status") == "진행중"]
    if active:
        st.subheader("🔄 렌탈 반납 처리")
        return_options = [f"{r['customer']} → {r['plate']} ({r['start']} ~ {r['end']})" for r in active]
        selected_return = st.selectbox("반납할 렌탈 선택", return_options)

        if st.button("반납 처리", type="primary"):
            idx = return_options.index(selected_return)
            target = active[idx]
            session_id = target.get("session_id", "")

            result = api_post("/session/end", {"session_id": session_id})
            if result:
                st.success(f"✅ 세션 {session_id} 반납 완료!")
            else:
                for r in st.session_state["rentals"]:
                    if r.get("session_id") == session_id:
                        r["status"] = "완료"
                        break
                st.success(f"✅ 반납 완료!")

            for v in st.session_state["vehicles"]:
                if v["plate"] == target["plate"]:
                    v["status"] = "대기"
                    break
            st.rerun()

    st.divider()
    st.subheader("➕ 신규 렌탈 등록")

    # 렌탈 등록용 차량/고객 목록도 API에서 가져오기
    vehicles_api = api_get("/company/vehicles")
    customers_api = api_get("/company/customers")
    
    vehicles = vehicles_api if (vehicles_api and isinstance(vehicles_api, list)) else st.session_state["vehicles"]
    customers = customers_api if (customers_api and isinstance(customers_api, list)) else st.session_state["customers"]
    
    available_vehicles = [v for v in vehicles if v.get("status", "대기") == "대기"]
    valid_customers = [c for c in customers if not c.get("blacklist", False)]

    if not available_vehicles:
        st.warning("⚠️ 대기 중인 차량이 없습니다.")
    elif not valid_customers:
        st.warning("⚠️ 대여 가능한 고객이 없습니다.")
    else:
        with st.form("add_rental", clear_on_submit=True):
            fr1, fr2 = st.columns(2)
            customer_options = [
                f"{c.get('name', 'N/A')} ({c.get('phone', 'N/A')})" 
                for c in valid_customers
            ]
            selected_customer = fr1.selectbox("고객 선택", customer_options)
            
            vehicle_options = [
                f"{v.get('plate_number') or v.get('plate', 'N/A')} — {v.get('model', 'N/A')}" 
                for v in available_vehicles
            ]
            selected_vehicle = fr2.selectbox("차량 선택", vehicle_options)

            fd1, fd2 = st.columns(2)
            start_date = fd1.date_input("대여일", value=date.today())
            end_date   = fd2.date_input("반납 예정일", value=date.today() + timedelta(days=3))
            scenario = st.selectbox("감시 시나리오", ["normal", "parking", "urban"])

            submitted_r = st.form_submit_button("렌탈 등록", use_container_width=True, type="primary")
            if submitted_r:
                if end_date <= start_date:
                    st.error("반납일은 대여일 이후여야 합니다.")
                else:
                    cust_name = selected_customer.split(" (")[0]
                    plate = selected_vehicle.split(" — ")[0]

                    result = api_post("/session/start", {
                        "user_id": cust_name, "vehicle_id": plate, "scenario": scenario
                    })
                    if result:
                        st.success(f"✅ {cust_name}님 → {plate} 렌탈 등록 완료! (세션: {result.get('session_id', 'N/A')})")
                    else:
                        st.session_state["rentals"].append({
                            "customer": cust_name, "plate": plate,
                            "start": start_date.isoformat(), "end": end_date.isoformat(),
                            "status": "진행중", "session_id": f"offline_{len(st.session_state['rentals'])}"
                        })
                        st.success(f"✅ {cust_name}님 → {plate} 렌탈 등록 완료! (오프라인)")

                    for v in st.session_state["vehicles"]:
                        if v["plate"] == plate:
                            v["status"] = "대여중"
                            break
                    for c in st.session_state["customers"]:
                        if c["name"] == cust_name:
                            c["rentals"] = c.get("rentals", 0) + 1
                            break
                    st.rerun()

# ───────────────────────────────────────
#  차량 관리
# ───────────────────────────────────────
with tab_vehicle:
    st.subheader("등록 차량 목록")

    # API에서 차량 목록 가져오기 (우선) → 실패하면 세션 폴백
    vehicles_api = api_get("/company/vehicles")
    if vehicles_api and isinstance(vehicles_api, list):
        vehicles = vehicles_api
    else:
        vehicles = st.session_state["vehicles"]
    v_available = sum(1 for v in vehicles if v.get("status", "대기") == "대기")
    v_rented    = sum(1 for v in vehicles if v.get("status", "대기") == "대여중")
    v_maint     = sum(1 for v in vehicles if v.get("status", "대기") == "정비중")

    vc1, vc2, vc3, vc4 = st.columns(4)
    vc1.metric("전체 차량", f"{len(vehicles)}대")
    vc2.metric("대기 중", f"{v_available}대")
    vc3.metric("대여 중", f"{v_rented}대")
    vc4.metric("정비 중", f"{v_maint}대")

    st.divider()

    if vehicles:
        # API 응답과 세션스테이트 구조 통합
        display_vehicles = []
        for v in vehicles:
            display_vehicles.append({
                "차량번호": v.get("plate_number") or v.get("plate", "N/A"),
                "모델": v.get("model", "N/A"),
                "연식": v.get("year", "N/A"),
                "상태": v.get("status", "대기"),  # API엔 없을 수 있음
                "등록일": v.get("registered", v.get("created_at", "N/A"))
            })
        
        df_v = pd.DataFrame(display_vehicles)

        def status_style(val):
            if val == "대여중":
                return "background-color: #fff3cc; color: #854f0b; font-weight: bold"
            elif val == "정비중":
                return "background-color: #ffcccc; color: #a32d2d; font-weight: bold"
            elif val == "대기":
                return "background-color: #ccf0d8; color: #085041; font-weight: bold"
            return ""

        styled = df_v.style.map(status_style, subset=["상태"])
        st.dataframe(styled, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("➕ 신규 차량 등록")
    with st.form("add_vehicle", clear_on_submit=True):
        fv1, fv2, fv3 = st.columns(3)
        new_plate = fv1.text_input("차량번호", placeholder="예: 11바 2345")
        new_model = fv2.text_input("모델명", placeholder="예: 현대 아반떼")
        new_year  = fv3.number_input("연식", min_value=2015, max_value=2030, value=2025)

        submitted_v = st.form_submit_button("차량 등록", use_container_width=True, type="primary")
        if submitted_v:
            if new_plate and new_model:
                result = api_post("/company/vehicles", {
                    "plate_number": new_plate, 
                    "model": new_model,
                    "year": str(new_year)  # 백엔드 스키마 타입(str)에 맞춰 변환
                })
                if result:
                    plate_num = result.get("plate_number", new_plate)
                    vid = result.get("vehicle_id", "")
                    st.success(f"✅ 차량 {plate_num} 등록 완료! (ID: {vid})")
                else:
                    st.session_state["vehicles"].append({
                        "plate": new_plate, "model": new_model,
                        "year": new_year, "status": "대기",
                        "registered": date.today().isoformat()
                    })
                    st.success(f"✅ {new_plate} ({new_model}) 등록 완료! (오프라인)")
                st.rerun()
            else:
                st.error("차량번호와 모델명을 입력해주세요.")

# ───────────────────────────────────────
#  고객 관리 / 블랙리스트
# ───────────────────────────────────────
with tab_customer:
    st.subheader("등록 고객 목록")

    # API에서 고객 목록 가져오기 (우선) → 실패하면 세션 폴백
    customers_api = api_get("/company/customers")
    if customers_api and isinstance(customers_api, list):
        customers = customers_api
    else:
        customers = st.session_state["customers"]
    c_total     = len(customers)
    c_blacklist = sum(1 for c in customers if c.get("blacklist", False))

    cc1, cc2, cc3 = st.columns(3)
    cc1.metric("전체 고객", f"{c_total}명")
    cc2.metric("정상 고객", f"{c_total - c_blacklist}명")
    cc3.metric("🚫 블랙리스트", f"{c_blacklist}명")

    st.divider()

    search_query = st.text_input("🔍 고객 검색", placeholder="이름, 전화번호, 또는 면허번호로 검색")

    filtered = customers
    if search_query:
        filtered = [c for c in customers
                    if search_query in c.get("name", "")
                    or search_query in c.get("phone", "")
                    or search_query in c.get("license", "")]

    if filtered:
        # API 응답과 세션스테이트 구조 통합
        display_customers = []
        for c in filtered:
            display_customers.append({
                "이름": c.get("name", "N/A"),
                "연락처": c.get("phone", "N/A"),
                "면허번호": c.get("license") or c.get("user_id", "N/A"),  # API는 user_id 사용
                "블랙리스트": "🚫 블랙" if c.get("blacklist", False) else "✅ 정상",
                "등록일": c.get("registered") or c.get("created_at", "N/A"),
                "대여횟수": c.get("rentals", 0)
            })
        
        df_c = pd.DataFrame(display_customers)

        def bl_style(val):
            if val == "🚫 블랙":
                return "background-color: #ffcccc; color: #a32d2d; font-weight: bold"
            elif val == "✅ 정상":
                return "background-color: #ccf0d8; color: #085041"
            return ""

        styled_c = df_c.style.map(bl_style, subset=["블랙리스트"])
        st.dataframe(styled_c, use_container_width=True, hide_index=True)
    else:
        st.info("검색 결과가 없습니다.")

    st.divider()

    st.subheader("🚫 블랙리스트 조회")
    st.caption("동명이인 구분을 위해 이름 + 연락처 또는 면허번호를 함께 입력하세요.")

    bl_col1, bl_col2 = st.columns(2)
    bl_name  = bl_col1.text_input("고객 이름", placeholder="이름 입력", key="bl_name")
    bl_extra = bl_col2.text_input("연락처 또는 면허번호 (선택)", placeholder="추가 정보로 동명이인 구분", key="bl_extra")

    if st.button("블랙리스트 조회", key="bl_check"):
        if bl_name:
            bl_data = api_get("/blacklist")
            if bl_data and isinstance(bl_data, list):
                found = [b for b in bl_data if bl_name in b.get("name", "") or bl_name in b.get("user_id", "")]
                if bl_extra:
                    found = [b for b in found if bl_extra in b.get("phone", "") or bl_extra in b.get("license", "") or bl_extra in b.get("user_id", "")]
            else:
                found = [c for c in customers if bl_name in c.get("name", "")]
                if bl_extra:
                    found = [c for c in found if bl_extra in c.get("phone", "") or bl_extra in c.get("license", "")]

            if not found:
                st.warning(f"'{bl_name}' 고객을 찾을 수 없습니다.")
            elif len(found) == 1:
                c = found[0]
                if c.get("blacklist", False):
                    st.error(f"🚫 **{c.get('name', '')}** (연락처: {c.get('phone', 'N/A')} / 면허: {c.get('license', 'N/A')}) — **블랙리스트 등록 고객**입니다. 대여가 제한됩니다.")
                else:
                    st.success(f"✅ **{c.get('name', '')}** (연락처: {c.get('phone', 'N/A')} / 면허: {c.get('license', 'N/A')}) — 정상 고객입니다. 대여 가능합니다.")
            else:
                st.warning(f"⚠️ '{bl_name}' 이름으로 {len(found)}명이 조회되었습니다.")
                for i, c in enumerate(found, 1):
                    is_bl = c.get("blacklist", False)
                    icon = "🚫" if is_bl else "✅"
                    status = "블랙리스트" if is_bl else "정상"
                    st.markdown(f"**{i}.** {icon} **{c.get('name', '')}** — 연락처: `{c.get('phone', 'N/A')}` / 면허: `{c.get('license', 'N/A')}` → **{status}**")
        else:
            st.error("고객 이름을 입력해주세요.")

    st.divider()
    st.subheader("➕ 신규 고객 등록")
    with st.form("add_customer", clear_on_submit=True):
        fc1, fc2 = st.columns(2)
        new_name    = fc1.text_input("이름", placeholder="예: 홍길동")
        new_phone   = fc2.text_input("연락처", placeholder="예: 010-1234-5678")
        new_license = st.text_input("면허번호", placeholder="예: 서울 12-345678")

        submitted_c = st.form_submit_button("고객 등록", use_container_width=True, type="primary")
        if submitted_c:
            if new_name and new_phone and new_license:
                result = api_post("/company/customers", {
                    "name": new_name, "phone": new_phone, "license": new_license
                })
                if not result:
                    st.session_state["customers"].append({
                        "name": new_name, "phone": new_phone,
                        "license": new_license, "blacklist": False,
                        "registered": date.today().isoformat(), "rentals": 0
                    })
                st.success(f"✅ {new_name} 고객 등록 완료!")
                st.rerun()
            else:
                st.error("모든 항목을 입력해주세요.")
