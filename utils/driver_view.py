import streamlit as st
from pathlib import Path
import os, subprocess, tempfile, json, requests
import cv2
import numpy as np
from PIL import ImageFont, ImageDraw, Image

# ── 설정 ──
BASE_URL = "https://practitioner-productivity-reduction-manufacturer.trycloudflare.com"

DRIVER_MAP = {
    "driver1": ("videos/test_scenario_1.mp4", "sess_scenario_1_0602_131649"),
    "driver2": ("videos/test_scenario_2.mp4", "sess_scenario_2_0602_131649"),
    "driver3": ("videos/test_scenario_3.mp4", "sess_scenario_3_0602_131649"),
    "driver4": ("videos/test_scenario_4.mp4", "sess_scenario_4_0602_131649"),
}

# 특정 세션에서 오탐(false-positive)으로 확인된 collision_warning 구간을 배너 대상에서 제외
# 값은 "탐지 frame_number" 범위 (frames 데이터의 frame_number 기준, 영상 프레임idx 아님)
EXCLUDE_DETECTION_RANGES = {
    "sess_scenario_3_0602_131649": [(693, 751)],  # 5번 구간: 실제 위험 없음 (모델 오탐으로 추정)
}

# ── 한글 폰트 로드 (없으면 None → OpenCV 기본) ──
def load_font(size=22):
    candidates = [
        "C:/Windows/Fonts/malgunbd.ttf",     # 맑은 고딕 Bold (Windows) - 우선
        "C:/Windows/Fonts/malgun.ttf",       # 맑은 고딕 Regular
        "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/nanum/NanumGothicBold.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return None

def draw_banner(frame_bgr, text, font, width, height):
    """둥근 모서리 + 반투명 배너 PIL로 렌더링"""
    bw = int(width * 0.38)   # 배너 폭 (화면의 38%)
    bh = 80                   # 배너 높이
    bx = (width - bw) // 2
    by = 60

    # PIL 이미지로 변환
    img_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(img_rgb).convert("RGBA")

    # 반투명 배너 레이어
    overlay = Image.new("RGBA", pil_img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # 둥근 모서리 사각형 (반투명)
    radius = 16
    color = (210, 30, 30, 160)  # 빨강 반투명 강화 (alpha 160)
    draw.rounded_rectangle([bx, by, bx+bw, by+bh], radius=radius, fill=color)

    # 테두리 (약간 밝은 빨강)
    draw.rounded_rectangle([bx, by, bx+bw, by+bh], radius=radius,
                            outline=(240, 80, 80, 180), width=2)

    # 합성
    pil_img = Image.alpha_composite(pil_img, overlay).convert("RGB")

    # 텍스트 정중앙 배치
    draw2 = ImageDraw.Draw(pil_img)
    bbox_t = font.getbbox(text)
    text_w = bbox_t[2] - bbox_t[0]
    text_h = bbox_t[3] - bbox_t[1]
    text_x = bx + (bw - text_w) // 2
    text_y = by + (bh - text_h) // 2 - bbox_t[1]

    # 텍스트 그림자
    draw2.text((text_x+2, text_y+2), text, font=font, fill=(0, 0, 0, 160))
    # 텍스트
    draw2.text((text_x, text_y), text, font=font, fill=(255, 255, 255))

    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

def fetch_logs(session_id: str, limit: int = 1000) -> dict:
    """API에서 로그 데이터 가져오기"""
    try:
        r = requests.get(
            f"{BASE_URL}/logs",
            params={"session_id": session_id, "limit": limit},
            headers={"ngrok-skip-browser-warning": "true"},
            timeout=30
        )
        return r.json()
    except Exception as e:
        return {"total_count": 0, "frames": [], "error": str(e)}

def build_banner_frames(frames: list, gap_fill: int = 12, min_run: int = 24) -> set:
    """BE collision_warning 판정 기반 배너 프레임 집합
    - gap_fill: 짧은 끊김(<=gap_fill 프레임)은 메움
    - min_run: 끊김 메운 후, min_run 프레임 미만인 짧은 구간(노이즈/오탐)은 제거
    """
    flagged = sorted(f["frame_number"] for f in frames if f.get("collision_warning"))
    if not flagged:
        return set()

    # 1) 끊김 메우기: 연속 구간으로 그룹화
    groups = [[flagged[0]]]
    for fn in flagged[1:]:
        if fn - groups[-1][-1] <= gap_fill:
            # 끊긴 구간도 포함해서 메움
            groups[-1].extend(range(groups[-1][-1] + 1, fn + 1))
        else:
            groups.append([fn])

    # 2) 최소 길이 미만 구간 제거 (짧은 노이즈/오탐 컷)
    banner = set()
    for g in groups:
        if len(g) >= min_run:
            banner.update(g)

    return banner

def annotate_video(src: Path, frames: list, out: Path, session_id: str = ""):
    cap    = cv2.VideoCapture(str(src))
    fps    = cap.get(cv2.CAP_PROP_FPS) or 24
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    tmp = out.with_suffix(".tmp.mp4")
    writer = cv2.VideoWriter(
        str(tmp),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps, (width, height)
    )

    total  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1

    font_lg = load_font(42)

    banner_frames = build_banner_frames(frames)

    # 오탐으로 확인된 구간 제외
    exclude_ranges = EXCLUDE_DETECTION_RANGES.get(session_id, [])
    for (a, b) in exclude_ranges:
        banner_frames -= set(range(a, b + 1))

    # 탐지 frame_number(샘플링 fps)와 영상 프레임 인덱스(원본 fps) 스케일 보정
    max_det = max((f["frame_number"] for f in frames), default=total - 1) + 1
    scale = max_det / total
    print(f"[DEBUG] 배너 표시 프레임 수: {len(banner_frames)}, 스케일: {scale:.4f}")

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # ── 배너 (BE collision_warning 판정 기반) ──
        if int(round(frame_idx * scale)) in banner_frames:
            frame = draw_banner(frame, "추돌 주의", font_lg, width, height)

        # REC 표시
        cv2.circle(frame, (20, 20), 7, (0, 0, 220), -1)
        cv2.putText(frame, f"REC  {int(fps)}FPS", (32, 26),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 220), 1, cv2.LINE_AA)

        writer.write(frame)
        frame_idx += 1

    cap.release()
    writer.release()

    r = subprocess.run([
        "ffmpeg", "-y", "-i", str(tmp),
        "-c:v", "libx264", "-profile:v", "baseline", "-level", "3.0",
        "-movflags", "+faststart", str(out)
    ], capture_output=True)
    tmp.unlink(missing_ok=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode(errors="ignore"))

def render_driver_dashboard():
    st.markdown("""
    <style>
        .stApp { background:#000 !important; }
        header[data-testid="stHeader"]   { display:none !important; }
        [data-testid="stSidebar"]        { display:none !important; }
        [data-testid="stSidebarNav"]     { display:none !important; }
        [data-testid="collapsedControl"] { display:none !important; }
        .block-container { padding:0 !important; max-width:100% !important; }
        section.main > div { padding-top:0 !important; }
        div[data-testid="stVideo"] { padding:0 !important; }
        video { width:100% !important; }
    </style>
    """, unsafe_allow_html=True)

    user_id = st.session_state.get("user_id", "driver1")
    raw_rel, session_id = DRIVER_MAP.get(user_id, DRIVER_MAP["driver1"])

    # ── 활성 세션 파일 기록 (Company 대시보드 실시간 연동) ──
    import time as _time
    SCENARIO_INFO = {
        "driver1": {"차량번호": "12가 3456", "운전자": "김철수", "면허번호": "경기-12-345678", "시나리오": "정상 주행", "company": "comp_sky"},
        "driver2": {"차량번호": "34나 7890", "운전자": "이영희", "면허번호": "서울-08-112233", "시나리오": "차량 접근", "company": "comp_sky"},
        "driver3": {"차량번호": "11바 1234", "운전자": "박민수", "면허번호": "인천-15-667788", "시나리오": "고속 주행", "company": "comp_jeju"},
        "driver4": {"차량번호": "22사 5678", "운전자": "최지현", "면허번호": "경남-03-990011", "시나리오": "충돌 위험", "company": "comp_jeju"},
    }
    try:
        active_info = SCENARIO_INFO.get(user_id, {})
        active_data = {
            "user_id": user_id,
            "session_id": session_id,
            "started_at": _time.strftime("%H:%M:%S"),
            **active_info
        }
        active_file = Path(os.getcwd()) / "active_session.json"
        with open(active_file, "w", encoding="utf-8") as f:
            json.dump(active_data, f, ensure_ascii=False)
    except Exception:
        pass

    search_bases = [Path(os.getcwd()), Path(__file__).parent.parent]

    # 원본 영상 탐색
    raw_path = None
    for base in search_bases:
        p = base / raw_rel
        if p.exists():
            raw_path = p
            break

    if not raw_path:
        st.error("영상 파일 없음: " + " / ".join(str(b/raw_rel) for b in search_bases))
        return

    cache_dir = Path(tempfile.gettempdir())
    annotated_path = cache_dir / f"ida_annotated_{user_id}_{session_id}.mp4"
    cache_key = f"_annotated_{user_id}_{session_id}"

    if cache_key not in st.session_state:
        if annotated_path.exists():
            try:
                annotated_path.unlink()
            except Exception:
                import time
                annotated_path = cache_dir / f"ida_annotated_{user_id}_{session_id}_{int(time.time())}.mp4"

        with st.spinner("DB에서 감지 데이터 불러오는 중..."):
            data = fetch_logs(session_id, limit=10000)

        if data.get("error"):
            st.error(f"API 오류: {data['error']}")
            st.stop()

        frames = data.get("frames") or []
        print(f"[DEBUG] frames={len(frames)}")

        if len(frames) == 0:
            st.warning("감지 데이터 없음 — 원본 영상으로 재생합니다.")

        with st.spinner(f"영상 생성 중... ({len(frames)}프레임)"):
            annotate_video(raw_path, frames, annotated_path, session_id=session_id)

        st.session_state[cache_key] = str(annotated_path)

    st.video(st.session_state[cache_key])
