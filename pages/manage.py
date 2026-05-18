import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from utils.auth import is_logged_in, get_role, get_company_name, get_company_id, is_online
from utils.sidebar import render_sidebar
from utils.api import api_get, api_post

if not is_logged_in() or get_role() not in ["company", "admin"]:
    st.switch_page("app.py")

render_sidebar()

st.title(f"🏢 {get_company_name()} — 업체 관리")

# 서버 연결 상태
if is_online():
    st.caption("🟢 서버 연결됨 — 실데이터 모드")
else:
    st.caption("🟡 오프라인 — 데모 데이터 모드")

# ═══════════════════════════════════════
#  오프라인 데모 데이터 (서버 안 될 때 폴백)
# ═══════════════════════════════════════
if "vehicles" not in st.session_state:
    st.session_state["vehicles"] = [
        {"plate": "12가 3456", "model": "현대 아반떼", "year": 2024, "status": "대여중", "registered": "2025-01-15"},
        {"plate": "34나 7890", "model": "기아 K5",     "year": 2023, "status": "대기",   "registered": "2025-02-20"},
        {"plate": "56다 1234", "model": "현대 쏘나타", "year": 2024, "status": "대기",   "registered": "2025-03-10"},
        {"plate": "78라 5678", "model": "기아 셀토스", "year": 2025, "status": "정비중", "registered": "2025-04-05"},
        {"plate": "90마 9012", "model": "현대 투싼",   "year": 2023, "status": "대기",   "registered": "2025-05-01"},
    ]

if "customers" not in st.session_state:
    st.session_state["customers"] = [
        {"name": "김민수", "phone": "010-1234-5678", "license": "서울 12-345678", "blacklist": False, "registered": "2025-01-20", "rentals": 3},
        {"name": "이영희", "phone": "010-9876-5432", "license": "경기 34-567890", "blacklist": False, "registered": "2025-02-15", "rentals": 1},
        {"name": "박준호", "phone": "010-5555-1234", "license": "제주 56-789012", "blacklist": True,  "registered": "2025-03-01", "rentals": 5},
        {"name": "최수진", "phone": "010-7777-8888", "license": "서울 78-901234", "blacklist": False, "registered": "2025-04-10", "rentals": 2},
    ]

# ═══════════════════════════════════════
#  탭 구성
# ═══════════════════════════════════════
if get_role() == "admin":
    tab_company_reg, tab_vehicle, tab_customer, tab_rental = st.tabs(["🏢 업체 등록", "🚗 차량 관리", "👤 고객 관리", "📋 렌탈 관리"])
else:
    tab_company_reg = None
    tab_vehicle, tab_customer, tab_rental = st.tabs(["🚗 차량 관리", "👤 고객 관리", "📋 렌탈 관리"])

# ───────────────────────────────────────
#  업체 등록 (관리자 전용) → POST /auth/accounts + GET /auth/companies
# ───────────────────────────────────────
if tab_company_reg is not None:
    with tab_company_reg:
        st.subheader("등록 업체 목록")

        # API에서 업체 목록 가져오기
        companies_api = api_get("/auth/companies")

        if companies_api and isinstance(companies_api, list):
            if len(companies_api) > 0:
                df_comp = pd.DataFrame(companies_api)
                st.dataframe(df_comp, use_container_width=True, hide_index=True)
            else:
                st.info("등록된 업체가 없습니다.")
            comp_count = len(companies_api)
        else:
            # 오프라인 폴백
            demo_companies = [
                {"company_name": "스카이렌터카", "company_id": "comp_sky", "role": "company"},
                {"company_name": "제주렌터카",   "company_id": "comp_jeju", "role": "company"},
            ]
            df_comp = pd.DataFrame(demo_companies)
            df_comp.columns = ["업체명", "업체 ID", "역할"]
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
                    # 실제 API 호출: POST /auth/accounts
                    result = api_post("/auth/accounts", {
                        "username": new_comp_username,
                        "password": new_comp_password,
                        "role": "company",
                        "company_id": new_comp_id,
                        "company_name": new_comp_name
                    })
                    if result:
                        st.success(f"✅ {new_comp_name} 업체 등록 완료! (로그인: {new_comp_username})")
                        st.rerun()
                    else:
                        st.warning("⚠️ 서버 연결 실패 — 오프라인에서는 업체 등록이 저장되지 않습니다.")
                else:
                    st.error("업체명, 업체 ID, 로그인 계정, 비밀번호를 모두 입력해주세요.")

# ───────────────────────────────────────
#  차량 관리 (추후 API 연동: /company/vehicles)
# ───────────────────────────────────────
with tab_vehicle:
    st.subheader("등록 차량 목록")

    # 차량 API 있으면 사용, 없으면 로컬
    vehicles_api = api_get("/company/vehicles")
    if vehicles_api and isinstance(vehicles_api, list):
        vehicles = vehicles_api
    else:
        vehicles = st.session_state["vehicles"]

    v_available = sum(1 for v in vehicles if v.get("status") == "대기")
    v_rented    = sum(1 for v in vehicles if v.get("status") == "대여중")
    v_maint     = sum(1 for v in vehicles if v.get("status") == "정비중")

    vc1, vc2, vc3, vc4 = st.columns(4)
    vc1.metric("전체 차량", f"{len(vehicles)}대")
    vc2.metric("대기 중", f"{v_available}대")
    vc3.metric("대여 중", f"{v_rented}대")
    vc4.metric("정비 중", f"{v_maint}대")

    st.divider()

    if vehicles:
        df_v = pd.DataFrame(vehicles)
        display_cols = ["plate", "model", "year", "status", "registered"]
        existing_cols = [c for c in display_cols if c in df_v.columns]
        df_v = df_v[existing_cols]
        col_map = {"plate": "차량번호", "model": "모델", "year": "연식", "status": "상태", "registered": "등록일"}
        df_v.rename(columns=col_map, inplace=True)

        def status_style(val):
            if val == "대여중":
                return "background-color: #fff3cc; color: #854f0b; font-weight: bold"
            elif val == "정비중":
                return "background-color: #ffcccc; color: #a32d2d; font-weight: bold"
            elif val == "대기":
                return "background-color: #ccf0d8; color: #085041; font-weight: bold"
            return ""

        if "상태" in df_v.columns:
            styled = df_v.style.map(status_style, subset=["상태"])
            st.dataframe(styled, use_container_width=True, hide_index=True)
        else:
            st.dataframe(df_v, use_container_width=True, hide_index=True)

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
                # API 시도
                result = api_post("/company/vehicles", {
                    "plate": new_plate, "model": new_model, "year": new_year
                })
                if not result:
                    # 오프라인 폴백
                    st.session_state["vehicles"].append({
                        "plate": new_plate, "model": new_model,
                        "year": new_year, "status": "대기",
                        "registered": date.today().isoformat()
                    })
                st.success(f"✅ {new_plate} ({new_model}) 등록 완료!")
                st.rerun()
            else:
                st.error("차량번호와 모델명을 입력해주세요.")

# ───────────────────────────────────────
#  고객 관리 (추후 API 연동: /company/customers)
# ───────────────────────────────────────
with tab_customer:
    st.subheader("등록 고객 목록")

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

    search_query = st.text_input("🔍 고객 검색", placeholder="이름 또는 전화번호로 검색")

    filtered = customers
    if search_query:
        filtered = [c for c in customers if search_query in c.get("name", "") or search_query in c.get("phone", "")]

    if filtered:
        df_c = pd.DataFrame(filtered)
        if "blacklist" in df_c.columns:
            df_c["blacklist"] = df_c["blacklist"].map({True: "🚫 블랙", False: "✅ 정상"})

            def bl_style(val):
                if val == "🚫 블랙":
                    return "background-color: #ffcccc; color: #a32d2d; font-weight: bold"
                elif val == "✅ 정상":
                    return "background-color: #ccf0d8; color: #085041"
                return ""

            display_cols = ["name", "phone", "license", "blacklist", "registered", "rentals"]
            existing = [c for c in display_cols if c in df_c.columns]
            df_c = df_c[existing]
            col_map = {"name": "이름", "phone": "연락처", "license": "면허번호", "blacklist": "블랙리스트", "registered": "등록일", "rentals": "대여횟수"}
            df_c.rename(columns=col_map, inplace=True)

            if "블랙리스트" in df_c.columns:
                styled_c = df_c.style.map(bl_style, subset=["블랙리스트"])
                st.dataframe(styled_c, use_container_width=True, hide_index=True)
            else:
                st.dataframe(df_c, use_container_width=True, hide_index=True)
        else:
            st.dataframe(df_c, use_container_width=True, hide_index=True)
    else:
        st.info("검색 결과가 없습니다.")

    st.divider()

    # 블랙리스트 조회 → GET /blacklist
    st.subheader("🚫 블랙리스트 조회")
    check_name = st.text_input("고객 이름으로 블랙리스트 확인", placeholder="이름 입력")
    if st.button("조회", key="bl_check"):
        if check_name:
            # API에서 블랙리스트 조회
            bl_data = api_get("/blacklist")
            if bl_data and isinstance(bl_data, list):
                found = [b for b in bl_data if check_name in b.get("name", "") or check_name in b.get("user_id", "")]
                if found:
                    for b in found:
                        st.error(f"🚫 {b.get('name', b.get('user_id', ''))} — 블랙리스트 등록 고객입니다.")
                else:
                    st.success(f"✅ {check_name} — 블랙리스트에 없습니다. 대여 가능합니다.")
            else:
                # 오프라인 폴백
                found = [c for c in customers if check_name in c.get("name", "")]
                if found:
                    for c in found:
                        if c.get("blacklist"):
                            st.error(f"🚫 {c['name']} — 블랙리스트 등록 고객입니다.")
                        else:
                            st.success(f"✅ {c['name']} — 정상 고객입니다. 대여 가능합니다.")
                else:
                    st.warning("등록되지 않은 고객입니다. 신규 등록 후 이용해주세요.")

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

# ───────────────────────────────────────
#  렌탈 관리 → POST /session/start, /session/end, GET /company/sessions
# ───────────────────────────────────────
with tab_rental:
    st.subheader("현재 렌탈 현황")

    # API에서 세션(렌탈) 목록 가져오기
    sessions_api = api_get("/company/sessions")

    if sessions_api and isinstance(sessions_api, list):
        rentals = sessions_api
        r_active = sum(1 for r in rentals if r.get("status") == "active")
    else:
        # 오프라인 데모
        if "rentals" not in st.session_state:
            st.session_state["rentals"] = [
                {"customer": "김민수", "plate": "12가 3456", "start": "2026-05-10", "end": "2026-05-15", "status": "진행중", "session_id": "demo_001"},
            ]
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

    st.divider()

    # 신규 렌탈 등록 → POST /session/start
    st.subheader("➕ 신규 렌탈 등록")

    vehicles = st.session_state.get("vehicles", [])
    customers = st.session_state.get("customers", [])

    available_vehicles = [v for v in vehicles if v.get("status") == "대기"]
    valid_customers = [c for c in customers if not c.get("blacklist", False)]

    if not available_vehicles:
        st.warning("⚠️ 대기 중인 차량이 없습니다.")
    elif not valid_customers:
        st.warning("⚠️ 대여 가능한 고객이 없습니다.")
    else:
        with st.form("add_rental", clear_on_submit=True):
            fr1, fr2 = st.columns(2)

            customer_options = [f"{c['name']} ({c['phone']})" for c in valid_customers]
            selected_customer = fr1.selectbox("고객 선택", customer_options)

            vehicle_options = [f"{v['plate']} — {v['model']}" for v in available_vehicles]
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

                    # 실제 API 호출: POST /session/start
                    result = api_post("/session/start", {
                        "user_id": cust_name,
                        "vehicle_id": plate,
                        "scenario": scenario
                    })

                    if result:
                        st.success(f"✅ {cust_name}님 → {plate} 렌탈 등록 완료! (세션: {result.get('session_id', 'N/A')})")
                    else:
                        # 오프라인 폴백
                        if "rentals" not in st.session_state:
                            st.session_state["rentals"] = []
                        st.session_state["rentals"].append({
                            "customer": cust_name, "plate": plate,
                            "start": start_date.isoformat(), "end": end_date.isoformat(),
                            "status": "진행중", "session_id": f"offline_{len(st.session_state['rentals'])}"
                        })
                        st.success(f"✅ {cust_name}님 → {plate} 렌탈 등록 완료! (오프라인)")

                    # 차량 상태 변경
                    for v in st.session_state.get("vehicles", []):
                        if v["plate"] == plate:
                            v["status"] = "대여중"
                            break

                    # 고객 대여횟수 증가
                    for c in st.session_state.get("customers", []):
                        if c["name"] == cust_name:
                            c["rentals"] = c.get("rentals", 0) + 1
                            break

                    st.rerun()

    st.divider()

    # 렌탈 반납 → POST /session/end
    if sessions_api and isinstance(sessions_api, list):
        active = [r for r in sessions_api if r.get("status") == "active"]
    else:
        active = [r for r in st.session_state.get("rentals", []) if r.get("status") == "진행중"]

    if active:
        st.subheader("🔄 렌탈 반납 처리")

        if sessions_api:
            return_options = [f"{r.get('user_id', '')} → {r.get('vehicle_id', '')} (세션: {r.get('session_id', '')})" for r in active]
        else:
            return_options = [f"{r['customer']} → {r['plate']} ({r['start']} ~ {r['end']})" for r in active]

        selected_return = st.selectbox("반납할 렌탈 선택", return_options)

        if st.button("반납 처리", type="primary"):
            idx = return_options.index(selected_return)
            target = active[idx]

            # 실제 API 호출: POST /session/end
            session_id = target.get("session_id", "")
            result = api_post("/session/end", {"session_id": session_id})

            if result:
                st.success(f"✅ 세션 {session_id} 반납 완료!")
            else:
                # 오프라인 폴백
                for r in st.session_state.get("rentals", []):
                    if r.get("session_id") == session_id or (r.get("customer") == target.get("customer") and r.get("status") == "진행중"):
                        r["status"] = "완료"
                        break
                st.success(f"✅ 반납 완료! (오프라인)")

            # 차량 상태 복구
            plate = target.get("plate", target.get("vehicle_id", ""))
            for v in st.session_state.get("vehicles", []):
                if v["plate"] == plate:
                    v["status"] = "대기"
                    break

            st.rerun()
