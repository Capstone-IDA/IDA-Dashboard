import streamlit as st
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="IDA - Vehicle Dashboard", layout="wide")

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


# ── 더미 /detect 응답 (건중이 JSON 스키마 기반) ──
DUMMY_DETECT = {
    "session_id": "a1b2c3d4-5678-9abc-def0-123456789abc",
    "frame_id": 847,
    "timestamp": datetime.now().isoformat(),
    "system": {"fps": 28.4, "inference_time_ms": 35.2},
    "can": {
        "speed_kmh": 12.5,
        "acceleration": 0.8,
        "brake_intensity": 0.0,
        "scenario": "normal"
    },
    "objects": [
        {
            "class_id": 0, "class_name": "차량", "confidence": 0.95,
            "bbox": {"x": 0.12, "y": 0.28, "w": 0.28, "h": 0.42},
            "track_id": 5, "depth_val": 0.18,
            "obj_speed_px": 2.4, "is_moving": True
        },
        {
            "class_id": 1, "class_name": "보행자", "confidence": 0.70,
            "bbox": {"x": 0.62, "y": 0.22, "w": 0.12, "h": 0.40},
            "track_id": 12, "depth_val": 0.45,
            "obj_speed_px": 1.1, "is_moving": True
        },
        {
            "class_id": 2, "class_name": "기둥", "confidence": 0.92,
            "bbox": {"x": 0.85, "y": 0.15, "w": 0.06, "h": 0.60},
            "track_id": 3, "depth_val": 0.72,
            "obj_speed_px": 0.0, "is_moving": False
        },
    ]
}


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

data = DUMMY_DETECT

# 상단 타이틀
st.markdown('<div class="hud-title">VEHICLE DASHBOARD</div>', unsafe_allow_html=True)

# 경고 배너
danger_objs = [o for o in data["objects"]
               if get_risk(o["depth_val"], o["obj_speed_px"], o["is_moving"])[0] == "DANGER"]
warning_objs = [o for o in data["objects"]
                if get_risk(o["depth_val"], o["obj_speed_px"], o["is_moving"])[0] == "WARNING"]

_, col_alert, _ = st.columns([1, 2, 1])
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
