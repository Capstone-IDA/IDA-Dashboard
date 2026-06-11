import cv2
from pathlib import Path

VIDEO_PATH = "videos/test_scenario_3.mp4"  # 프로젝트 루트 기준 상대경로

p = Path(VIDEO_PATH)
if not p.exists():
    print(f"파일 없음: {p.resolve()}")
else:
    cap = cv2.VideoCapture(str(p))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    print(f"파일: {p}")
    print(f"FPS: {fps}")
    print(f"총 프레임 수 (cv2): {total}")
    print(f"DB 탐지 프레임 수(max_det): 1252")
    print(f"scale = max_det / total = {1252/total:.4f}")
