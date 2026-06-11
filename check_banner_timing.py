import requests

BASE_URL = "https://practitioner-productivity-reduction-manufacturer.trycloudflare.com"
SESSION_ID = "sess_scenario_3_0602_131649"
VIDEO_TOTAL_FRAMES = 1566   # cv2로 확인한 영상 총 프레임수
VIDEO_FPS = 30.0

r = requests.get(
    f"{BASE_URL}/logs",
    params={"session_id": SESSION_ID, "limit": 10000},
    headers={"ngrok-skip-browser-warning": "true"},
    timeout=30
)
frames = r.json().get("frames", [])

def build_banner_frames(frames, gap_fill=12):
    flagged = sorted(f["frame_number"] for f in frames if f.get("collision_warning"))
    banner = set(flagged)
    for a, b in zip(flagged, flagged[1:]):
        if 1 < b - a <= gap_fill:
            banner.update(range(a + 1, b))
    return banner

banner_frames = build_banner_frames(frames)
max_det = max((f["frame_number"] for f in frames), default=VIDEO_TOTAL_FRAMES - 1) + 1
scale = max_det / VIDEO_TOTAL_FRAMES
print(f"max_det={max_det}, scale={scale:.4f}")

# 영상 프레임마다 배너 뜨는지 확인 → 연속 구간으로 묶어서 출력
hits = []
for frame_idx in range(VIDEO_TOTAL_FRAMES):
    if int(round(frame_idx * scale)) in banner_frames:
        hits.append(frame_idx)

print(f"\n배너 뜨는 영상 프레임 수: {len(hits)}")

# 연속 구간 묶기
groups = []
if hits:
    g = [hits[0]]
    for fn in hits[1:]:
        if fn == g[-1] + 1:
            g.append(fn)
        else:
            groups.append(g)
            g = [fn]
    groups.append(g)

print(f"\n배너 뜨는 영상 구간 ({len(groups)}개):")
for g in groups:
    t1, t2 = g[0]/VIDEO_FPS, g[-1]/VIDEO_FPS
    print(f"  프레임 {g[0]}~{g[-1]} → {t1:.1f}초 ~ {t2:.1f}초")
