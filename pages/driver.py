import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random
from utils.api import api_get

st.set_page_config(page_title="IDA - Vehicle Dashboard", layout="wide")


# ── 더미 Detection 데이터 생성 함수 ──
def generate_mock_detections(session_id, total_frames, duration_sec):
    """영상별 더미 detection 데이터 생성 (현실적인 시나리오)"""
    detections = []
    start_time = datetime(2026, 6, 1, 14, 23, 15)
    
    for frame_id in range(1, total_frames + 1):
        # 타임스탬프 계산
        timestamp = start_time + timedelta(seconds=frame_id / 30)
        
        # 프레임 위치 비율 (0.0 ~ 1.0)
        progress = frame_id / total_frames
        
        # 시나리오별 위험도 패턴
        if progress < 0.3:  # 초반 30%: SAFE
            risk_factor = 0.1
            speed = random.uniform(10, 15)
        elif progress < 0.6:  # 중반 30%: WARNING
            risk_factor = 0.4
            speed = random.uniform(15, 25)
        elif progress < 0.8:  # 후반 20%: WARNING → DANGER 전환
            risk_factor = 0.6
            speed = random.uniform(20, 30)
        else:  # 마지막 20%: DANGER
            risk_factor = 0.8
            speed = random.uniform(25, 35)
        
        # 객체 생성
        objects = []
        
        # 차량 (항상 존재)
        vehicle_depth = max(0.15, 0.8 - (progress * risk_factor))
        objects.append({
            "class_id": 0,
            "class_name": "차량",
            "confidence": random.uniform(0.90, 0.98),
            "bbox": {
                "x": random.uniform(0.1, 0.3),
                "y": random.uniform(0.25, 0.35),
                "w": random.uniform(0.25, 0.35),
                "h": random.uniform(0.35, 0.45)
            },
            "track_id": 5,
            "depth_val": vehicle_depth,
            "obj_speed_px": random.uniform(1.5, 3.5) if risk_factor > 0.5 else random.uniform(0.5, 1.5),
            "is_moving": True
        })
        
        # 보행자 (중반부터 등장)
        if progress > 0.3:
            pedestrian_depth = max(0.2, 0.7 - (progress * risk_factor * 0.8))
            objects.append({
                "class_id": 1,
                "class_name": "보행자",
                "confidence": random.uniform(0.65, 0.85),
                "bbox": {
                    "x": random.uniform(0.5, 0.7),
                    "y": random.uniform(0.2, 0.3),
                    "w": random.uniform(0.08, 0.15),
                    "h": random.uniform(0.35, 0.45)
                },
                "track_id": 12,
                "depth_val": pedestrian_depth,
                "obj_speed_px": random.uniform(0.8, 1.8) if risk_factor > 0.6 else random.uniform(0.3, 0.9),
                "is_moving": True
            })
        
        # 기둥/벽 (항상 존재)
        objects.append({
            "class_id": 2,
            "class_name": "기둥",
            "confidence": random.uniform(0.88, 0.95),
            "bbox": {
                "x": random.uniform(0.82, 0.88),
                "y": random.uniform(0.12, 0.18),
                "w": random.uniform(0.05, 0.08),
                "h": random.uniform(0.55, 0.65)
            },
            "track_id": 3,
            "depth_val": random.uniform(0.65, 0.85),
            "obj_speed_px": 0.0,
            "is_moving": False
        })
        
        detections.append({
            "session_id": session_id,
            "frame_id": frame_id,
            "timestamp": timestamp.isoformat(),
            "system": {
                "fps": random.uniform(28, 32),
                "inference_time_ms": random.uniform(30, 40)
            },
            "can": {
                "speed_kmh": speed,
                "acceleration": random.uniform(-0.5, 1.5) if risk_factor > 0.5 else random.uniform(0, 0.8),
                "brake_intensity": random.uniform(0.3, 0.7) if risk_factor > 0.7 else 0.0,
                "scenario": "normal"
            },
            "objects": objects
        })
    
    return detections

# ── 차량 HUD 스타일 ──
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Noto+Sans+KR:wght@400;700;900&display=swap');

    .stApp {
        background-color: #000000;
        color: #e0e6f0;
    }

    header[data-testid="stHeader"] { background: #000; }
    .block-container { padding: 0.5rem 1rem 0 1rem !important; max-width: 100% !important; }

    .hud-title {
        font-family: 'Orbitron', sans-serif;
        font-size: 1rem;
        font-weight: 700;
        color: #c0c8d8;
        text-align: center;
        letter-spacing: 4px;
        padding: 0.3rem 0;
    }

    .alert-banner {
        background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
        border-radius: 10px;
        padding: 0.6rem 1.2rem;
        text-align: center;
        box-shadow: 0 0 20px rgba(220,38,38,0.4);
        animation: pulse-glow 1.5s ease-in-out infinite;
    }

    @keyframes pulse-glow {
        0%, 100% { box-shadow: 0 0 15px rgba(220,38,38,0.3); }
        50% { box-shadow: 0 0 30px rgba(220,38,38,0.6); }
    }

    .alert-title {
        font-family: 'Noto Sans KR', sans-serif;
        font-size: 1rem;
        font-weight: 900;
        color: #ffffff;
    }

    .alert-sub {
        font-family: 'Noto Sans KR', sans-serif;
        font-size: 0.8rem;
        color: rgba(255,255,255,0.85);
        margin-top: 0.1rem;
    }

    .alert-banner-warning {
        background: linear-gradient(135deg, #d97706 0%, #b45309 100%);
        border-radius: 10px;
        padding: 0.6rem 1.2rem;
        text-align: center;
        box-shadow: 0 0 20px rgba(217,119,6,0.3);
    }

    .alert-banner-safe {
        background: linear-gradient(135deg, #15803d 0%, #166534 100%);
        border-radius: 10px;
        padding: 0.5rem 1.2rem;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)


def get_risk(depth_val, obj_speed_px, is_moving):
    if depth_val < 0.25:
        return "DANGER", "#ef4444"
    elif depth_val < 0.5:
        if is_moving and obj_speed_px > 1.0:
            return "DANGER", "#ef4444"
        return "WARNING", "#facc15"
    return "SAFE", "#38bdf8"


def hex_to_rgba(hex_color, alpha):
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return f"rgba({r},{g},{b},{alpha})"


# ── 카메라 뷰 (주차장 + 바운딩박스) ──
def draw_vehicle_view(data):
    fig = go.Figure()

    # 주차장 배경 — 바닥
    fig.add_shape(type="rect", x0=0, y0=0, x1=1, y1=0.35,
                  fillcolor="#1a1c20", line=dict(width=0))
    # 벽/천장
    fig.add_shape(type="rect", x0=0, y0=0.35, x1=1, y1=1,
                  fillcolor="#14161a", line=dict(width=0))

    # 주차 라인
    for lx in [0.22, 0.44, 0.66, 0.88]:
        fig.add_shape(type="line", x0=lx, y0=0, x1=lx, y1=0.18,
                      line=dict(color="rgba(255,255,255,0.06)", width=2))

    # 천장 조명
    for lx in [0.25, 0.5, 0.75]:
        fig.add_shape(type="rect", x0=lx-0.02, y0=0.92, x1=lx+0.02, y1=0.95,
                      fillcolor="rgba(255,255,255,0.08)", line=dict(width=0))
        fig.add_shape(type="path",
                      path=f"M {lx-0.02} 0.92 L {lx-0.06} 0.55 L {lx+0.06} 0.55 L {lx+0.02} 0.92 Z",
                      fillcolor="rgba(255,255,255,0.015)", line=dict(width=0))

    # 바운딩박스
    for obj in data["objects"]:
        bbox = obj["bbox"]
        x0 = bbox["x"]
        x1 = bbox["x"] + bbox["w"]
        y0 = 1 - (bbox["y"] + bbox["h"])
        y1 = 1 - bbox["y"]

        risk, color = get_risk(obj["depth_val"], obj["obj_speed_px"], obj["is_moving"])

        # 박스 + 반투명 채우기
        fig.add_shape(
            type="rect", x0=x0, y0=y0, x1=x1, y1=y1,
            line=dict(color=color, width=2),
            fillcolor=hex_to_rgba(color, 0.04)
        )

        # 코너 강조
        clen = min(bbox["w"], bbox["h"]) * 0.22
        for cx, cy, dx, dy in [
            (x0, y1, 1, 0), (x0, y1, 0, -1),
            (x1, y1, -1, 0), (x1, y1, 0, -1),
            (x0, y0, 1, 0), (x0, y0, 0, 1),
            (x1, y0, -1, 0), (x1, y0, 0, 1),
        ]:
            fig.add_shape(type="line",
                          x0=cx, y0=cy, x1=cx + dx * clen, y1=cy + dy * clen,
                          line=dict(color=color, width=3.5))

        # 레이블
        label = f"{obj['class_name']} - {obj['confidence']:.0%}"
        fig.add_annotation(
            x=(x0 + x1) / 2, y=y1 + 0.02,
            text=f"<b>{label}</b>",
            showarrow=False,
            font=dict(size=12, color="#ffffff", family="Noto Sans KR, sans-serif"),
            bgcolor=hex_to_rgba(color, 0.75),
            borderpad=5,
            xanchor="center",
        )

    # REC 표시 (좌상단)
    fig.add_annotation(
        x=0.01, y=0.98,
        text=f"<b>● REC</b>  {data['system']['fps']:.0f} FPS",
        showarrow=False,
        font=dict(size=10, color="#ef4444", family="Orbitron, monospace"),
        xanchor="left", yanchor="top",
        bgcolor="rgba(0,0,0,0.5)", borderpad=4
    )

    # 프레임 번호 (우상단)
    fig.add_annotation(
        x=0.99, y=0.98,
        text=f"F:{data['frame_id']}",
        showarrow=False,
        font=dict(size=9, color="#4a5568", family="Orbitron, monospace"),
        xanchor="right", yanchor="top",
    )

    fig.update_layout(
        xaxis=dict(range=[0, 1], showgrid=False, zeroline=False, visible=False),
        yaxis=dict(range=[0, 1], showgrid=False, zeroline=False, visible=False,
                   scaleanchor="x", scaleratio=0.56),
        plot_bgcolor="#111318",
        paper_bgcolor="#000000",
        margin=dict(l=0, r=0, t=0, b=0),
        height=500,
        dragmode=False,
    )
    return fig


# ═══════════════════════════════
#  화면 구성
# ═══════════════════════════════

# 세션별 영상 매핑 (FE에 저장된 테스트 영상)
VIDEO_MAP = {
    "session_001": {
        "video": "videos/test_scenario_1.mp4",
        "name": "시나리오 1 (60초)",
        "duration": 60,
        "frames": 1800
    },
    "session_002": {
        "video": "videos/test_scenario_2.mp4",
        "name": "시나리오 2 (34초)",
        "duration": 34,
        "frames": 1020
    },
    "session_003": {
        "video": "videos/test_scenario_3.mp4",
        "name": "시나리오 3 (52초)",
        "duration": 52,
        "frames": 1560
    },
}

# 사이드바: 세션 선택
st.sidebar.markdown("### 🎬 시나리오 선택")
selected_session = st.sidebar.selectbox(
    "테스트 시나리오",
    options=list(VIDEO_MAP.keys()),
    format_func=lambda x: f"{VIDEO_MAP[x]['name']}"
)

video_info = VIDEO_MAP[selected_session]
st.sidebar.caption(f"📹 {video_info['duration']}초 / {video_info['frames']} 프레임")

# Detection 결과 가져오기 (API 우선 → 더미 폴백)
cache_key = f'detection_cache_{selected_session}'

if cache_key not in st.session_state:
    # API 시도
    detect_results = api_get(f"/detect?session_id={selected_session}")
    
    if detect_results and isinstance(detect_results, list):
        st.session_state[cache_key] = detect_results
        st.sidebar.success("🟢 API 데이터 로드 완료")
    else:
        # 더미 데이터 생성
        st.session_state[cache_key] = generate_mock_detections(
            selected_session,
            video_info['frames'],
            video_info['duration']
        )
        st.sidebar.warning("🟡 오프라인 - 더미 데이터")

cached_results = st.session_state[cache_key]

# 프레임 선택 (실제 영상 플레이어와 동기화 예정)
st.sidebar.markdown("---")
st.sidebar.markdown("### 🎮 프레임 탐색 (테스트용)")
current_frame_id = st.sidebar.slider(
    "프레임",
    min_value=1,
    max_value=video_info['frames'],
    value=1,
    help="실제 데모에서는 영상 재생과 자동 동기화됩니다"
)

# 현재 프레임 데이터
data = cached_results[current_frame_id - 1]

# 상단 타이틀
st.markdown('<div class="hud-title">VEHICLE DASHBOARD</div>', unsafe_allow_html=True)

# 경고 배너
danger_objs = [o for o in data["objects"]
               if get_risk(o["depth_val"], o["obj_speed_px"], o["is_moving"])[0] == "DANGER"]
warning_objs = [o for o in data["objects"]
                if get_risk(o["depth_val"], o["obj_speed_px"], o["is_moving"])[0] == "WARNING"]

_, col_alert, _ = st.columns([1.5, 1, 1.5])
with col_alert:
    if danger_objs:
        obj_names = ", ".join(set(o["class_name"] for o in danger_objs))
        st.markdown(f"""
        <div class="alert-banner">
            <div class="alert-title">경고 알림: 추돌 주의!</div>
            <div class="alert-sub">전방 {obj_names} 감지됨!</div>
        </div>
        """, unsafe_allow_html=True)
    elif warning_objs:
        obj_names = ", ".join(set(o["class_name"] for o in warning_objs))
        st.markdown(f"""
        <div class="alert-banner-warning">
            <div class="alert-title" style="font-size:0.9rem;">⚡ 주의: 접근 물체 감지</div>
            <div class="alert-sub">{obj_names} 주의 구간</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="alert-banner-safe">
            <div class="alert-title" style="font-size:0.85rem;">✓ 안전 운행 중</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<div style='height:0.3rem;'></div>", unsafe_allow_html=True)

# 카메라 뷰 (전체 폭)
fig = draw_vehicle_view(data)
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# 하단 정보 바
can = data["can"]
speed_color = "#ef4444" if can["speed_kmh"] > 15 else ("#facc15" if can["speed_kmh"] > 10 else "#22c55e")

st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;
            background:rgba(10,14,23,0.9);border:1px solid #1e2a3a;border-radius:10px;
            padding:0.5rem 1.5rem;margin-top:-0.5rem;">

    <div style="display:flex;align-items:baseline;gap:0.4rem;">
        <span style="font-family:'Orbitron',sans-serif;font-size:2rem;font-weight:900;color:{speed_color};">
            {can['speed_kmh']:.0f}
        </span>
        <span style="font-family:'Orbitron',sans-serif;font-size:0.65rem;color:#6b7b99;">km/h</span>
    </div>

    <div style="text-align:center;">
        <div style="font-family:'Noto Sans KR',sans-serif;font-size:0.8rem;font-weight:700;color:#38bdf8;letter-spacing:2px;">
            주차 감시 모드 활성화
        </div>
    </div>

    <div style="display:flex;gap:1.2rem;">
        <div style="text-align:center;">
            <div style="font-family:'Orbitron',sans-serif;font-size:0.6rem;color:#6b7b99;">ACCEL</div>
            <div style="font-family:'Orbitron',sans-serif;font-size:0.95rem;font-weight:700;color:#e0e6f0;">
                {can['acceleration']:.1f}
            </div>
        </div>
        <div style="text-align:center;">
            <div style="font-family:'Orbitron',sans-serif;font-size:0.6rem;color:#6b7b99;">BRAKE</div>
            <div style="font-family:'Orbitron',sans-serif;font-size:0.95rem;font-weight:700;color:#e0e6f0;">
                {can['brake_intensity']:.1f}
            </div>
        </div>
        <div style="text-align:center;">
            <div style="font-family:'Orbitron',sans-serif;font-size:0.6rem;color:#6b7b99;">OBJ</div>
            <div style="font-family:'Orbitron',sans-serif;font-size:0.95rem;font-weight:700;color:#a78bfa;">
                {len(data['objects'])}
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)
