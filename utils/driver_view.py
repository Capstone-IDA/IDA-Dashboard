import streamlit as st
import cv2
import numpy as np
from datetime import datetime
from pathlib import Path


# ── 위험도 판정 ──
def get_risk(depth_val, obj_speed_px, is_moving):
    if depth_val < 0.25:
        return "DANGER", (79, 68, 239)
    elif depth_val < 0.5:
        if is_moving and obj_speed_px > 1.0:
            return "DANGER", (79, 68, 239)
        return "WARNING", (21, 204, 250)
    return "SAFE", (248, 189, 56)


def draw_bbox(frame, obj, frame_h, frame_w):
    bbox = obj["bbox"]
    x1 = int(bbox["x"] * frame_w)
    y1 = int(bbox["y"] * frame_h)
    x2 = int((bbox["x"] + bbox["w"]) * frame_w)
    y2 = int((bbox["y"] + bbox["h"]) * frame_h)

    risk, color = get_risk(obj["depth_val"], obj["obj_speed_px"], obj["is_moving"])

    overlay = frame.copy()
    cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
    cv2.addWeighted(overlay, 0.08, frame, 0.92, 0, frame)

    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

    clen = min(x2 - x1, y2 - y1) // 4
    thickness = 3
    cv2.line(frame, (x1, y1), (x1 + clen, y1), color, thickness)
    cv2.line(frame, (x1, y1), (x1, y1 + clen), color, thickness)
    cv2.line(frame, (x2, y1), (x2 - clen, y1), color, thickness)
    cv2.line(frame, (x2, y1), (x2, y1 + clen), color, thickness)
    cv2.line(frame, (x1, y2), (x1 + clen, y2), color, thickness)
    cv2.line(frame, (x1, y2), (x1, y2 - clen), color, thickness)
    cv2.line(frame, (x2, y2), (x2 - clen, y2), color, thickness)
    cv2.line(frame, (x2, y2), (x2, y2 - clen), color, thickness)

    label = f"{obj['class_name']} - {obj['confidence']:.0%}"
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.55
    (tw, th), _ = cv2.getTextSize(label, font, font_scale, 1)
    cv2.rectangle(frame, (x1, y1 - th - 14), (x1 + tw + 8, y1), color, -1)
    cv2.putText(frame, label, (x1 + 4, y1 - 8), font, font_scale, (255, 255, 255), 1, cv2.LINE_AA)

    return frame


def draw_hud_overlay(frame, data, frame_h, frame_w):
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.circle(frame, (20, 25), 6, (0, 0, 239), -1)
    fps = data.get("system", {}).get("fps", 0)
    cv2.putText(frame, f"REC  {fps:.0f} FPS", (32, 30), font, 0.5, (0, 0, 239), 1, cv2.LINE_AA)
    fid = data.get("frame_id", 0)
    cv2.putText(frame, f"F:{fid}", (frame_w - 70, 30), font, 0.45, (100, 110, 130), 1, cv2.LINE_AA)
    return frame


@st.cache_data
def get_total_frames(video_path_str):
    cap = cv2.VideoCapture(video_path_str)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    return total


def get_video_frame(video_path, frame_number):
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return None
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
    ret, frame = cap.read()
    cap.release()
    return frame if ret else None


# ── 더미 탐지 데이터 ──
DUMMY_DETECT = {
    "session_id": "a1b2c3d4-5678",
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
            "bbox": {"x": 0.10, "y": 0.30, "w": 0.25, "h": 0.40},
            "track_id": 5, "depth_val": 0.18,
            "obj_speed_px": 2.4, "is_moving": True
        },
        {
            "class_id": 1, "class_name": "보행자", "confidence": 0.70,
            "bbox": {"x": 0.60, "y": 0.25, "w": 0.10, "h": 0.35},
            "track_id": 12, "depth_val": 0.45,
            "obj_speed_px": 1.1, "is_moving": True
        },
        {
            "class_id": 2, "class_name": "기둥", "confidence": 0.92,
            "bbox": {"x": 0.82, "y": 0.15, "w": 0.05, "h": 0.55},
            "track_id": 3, "depth_val": 0.72,
            "obj_speed_px": 0.0, "is_moving": False
        },
    ]
}


def render_driver_dashboard():

    # ── 스타일 ──
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Noto+Sans+KR:wght@400;700;900&display=swap');
        .stApp { background-color: #000000; color: #e0e6f0; }

        header[data-testid="stHeader"] { display: none !important; }
        .block-container { padding: 0.3rem 0 0 0 !important; max-width: 100% !important; }
        div[data-testid="stAppViewBlockContainer"] { padding-top: 0 !important; }
        .appview-container { padding-top: 0 !important; }
        section.main > div { padding-top: 0 !important; }
        #root > div:first-child { padding-top: 0 !important; }

        div[data-testid="stSlider"] { padding: 0 0.5rem !important; }
        div[data-testid="stSlider"] label { display: none !important; }
        div[data-testid="stSlider"] > div { margin-top: -0.3rem !important; margin-bottom: -0.3rem !important; }

        .alert-banner {
            background: linear-gradient(135deg, rgba(220,38,38,0.92) 0%, rgba(185,28,28,0.92) 100%);
            padding: 0.6rem 1.5rem; text-align: center;
            border-radius: 14px;
            box-shadow: 0 0 25px rgba(220,38,38,0.5);
            animation: pulse-glow 1.5s ease-in-out infinite;
            backdrop-filter: blur(4px);
        }
        @keyframes pulse-glow {
            0%, 100% { box-shadow: 0 0 15px rgba(220,38,38,0.4); }
            50% { box-shadow: 0 0 35px rgba(220,38,38,0.7); }
        }
        .alert-title {
            font-family: 'Noto Sans KR', sans-serif;
            font-weight: 900; color: #fff;
        }
        .alert-sub {
            font-family: 'Noto Sans KR', sans-serif;
            color: rgba(255,255,255,0.85);
        }
        .alert-banner-warning {
            background: linear-gradient(135deg, rgba(217,119,6,0.92) 0%, rgba(180,83,9,0.92) 100%);
            padding: 0.6rem 1.5rem; text-align: center;
            border-radius: 14px;
            box-shadow: 0 0 20px rgba(217,119,6,0.4);
            backdrop-filter: blur(4px);
        }
    </style>
    """, unsafe_allow_html=True)

    # ── 데이터 ──
    data = DUMMY_DETECT

    # ── 영상 ──
    video_path = Path(__file__).parent.parent / "parking.mp4"
    total_frames = get_total_frames(str(video_path))

    # ── 슬라이더 ──
    frame_num = st.slider("frame", 0, max(total_frames - 1, 1), 100, label_visibility="collapsed")

    # ── 프레임 처리 ──
    frame = get_video_frame(video_path, frame_number=frame_num)

    if frame is not None:
        h, w = frame.shape[:2]

        # 바운딩박스 그리기
        if data and data.get("objects"):
            for obj in data["objects"]:
                frame = draw_bbox(frame, obj, h, w)
            data["frame_id"] = frame_num
            frame = draw_hud_overlay(frame, data, h, w)

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # 경고 배너 (영상 상단에 겹침)
        if data and data.get("objects"):
            danger_objs = [o for o in data["objects"]
                           if get_risk(o["depth_val"], o["obj_speed_px"], o["is_moving"])[0] == "DANGER"]
            warning_objs = [o for o in data["objects"]
                            if get_risk(o["depth_val"], o["obj_speed_px"], o["is_moving"])[0] == "WARNING"]
            if danger_objs:
                obj_names = ", ".join(set(o["class_name"] for o in danger_objs))
                st.markdown(f"""
                <div style="position:relative;z-index:10;margin-bottom:-75px;padding:0.5rem 1rem 0 1rem;">
                    <div class="alert-banner">
                        <div class="alert-title" style="font-size:1.1rem;">경고 알림: 추돌 주의!</div>
                        <div class="alert-sub" style="font-size:0.85rem;">전방 {obj_names} 감지됨!</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            elif warning_objs:
                obj_names = ", ".join(set(o["class_name"] for o in warning_objs))
                st.markdown(f"""
                <div style="position:relative;z-index:10;margin-bottom:-75px;padding:0.5rem 1rem 0 1rem;">
                    <div class="alert-banner-warning">
                        <div class="alert-title" style="font-size:1rem;">⚡ 주의: 접근 물체 감지</div>
                        <div class="alert-sub" style="font-size:0.85rem;">{obj_names} 주의 구간</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        # 영상 프레임 (전체 폭 사용)
        st.image(frame_rgb, use_column_width=True)

        # 하단 정보 바 (영상 하단에 겹침)
        can = data["can"] if data and data.get("can") else {"speed_kmh": 0, "acceleration": 0, "brake_intensity": 0}
        obj_count = len(data["objects"]) if data and data.get("objects") else 0
        speed_color = "#ef4444" if can["speed_kmh"] > 15 else ("#facc15" if can["speed_kmh"] > 10 else "#22c55e")

        st.markdown(f"""
        <div style="position:relative;z-index:10;margin-top:-65px;padding:0 1rem 0.5rem 1rem;">
            <div style="display:flex;justify-content:space-between;align-items:center;
                        background:rgba(0,0,0,0.75);backdrop-filter:blur(4px);
                        border-radius:14px;padding:0.5rem 1.5rem;">
                <div style="display:flex;align-items:baseline;gap:0.4rem;">
                    <span style="font-family:'Orbitron',sans-serif;font-size:1.8rem;font-weight:900;color:{speed_color};">
                        {can['speed_kmh']:.0f}
                    </span>
                    <span style="font-family:'Orbitron',sans-serif;font-size:0.6rem;color:#6b7b99;">km/h</span>
                </div>
                <div style="text-align:center;">
                    <div style="font-family:'Noto Sans KR',sans-serif;font-size:0.75rem;font-weight:700;color:#38bdf8;letter-spacing:2px;">
                        주차 감시 모드 활성화
                    </div>
                </div>
                <div style="display:flex;gap:1.2rem;">
                    <div style="text-align:center;">
                        <div style="font-family:'Orbitron',sans-serif;font-size:0.55rem;color:#6b7b99;">ACCEL</div>
                        <div style="font-family:'Orbitron',sans-serif;font-size:0.9rem;font-weight:700;color:#e0e6f0;">
                            {can['acceleration']:.1f}
                        </div>
                    </div>
                    <div style="text-align:center;">
                        <div style="font-family:'Orbitron',sans-serif;font-size:0.55rem;color:#6b7b99;">BRAKE</div>
                        <div style="font-family:'Orbitron',sans-serif;font-size:0.9rem;font-weight:700;color:#e0e6f0;">
                            {can['brake_intensity']:.1f}
                        </div>
                    </div>
                    <div style="text-align:center;">
                        <div style="font-family:'Orbitron',sans-serif;font-size:0.55rem;color:#6b7b99;">OBJ</div>
                        <div style="font-family:'Orbitron',sans-serif;font-size:0.9rem;font-weight:700;color:#a78bfa;">
                            {obj_count}
                        </div>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    else:
        st.markdown("""
        <div style="background:#111318;border-radius:12px;height:55vh;
                    display:flex;align-items:center;justify-content:center;flex-direction:column;">
            <div style="font-size:2rem;color:#2a2f3a;">⦿</div>
            <div style="color:#3a4050;font-family:'Noto Sans KR',sans-serif;">영상 파일을 찾을 수 없습니다</div>
        </div>
        """, unsafe_allow_html=True)
