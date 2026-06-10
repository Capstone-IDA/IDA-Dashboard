import requests

BASE_URL = "https://blast-london-istanbul-kitty.trycloudflare.com"
SESSION_ID = "sess_scenario_3_0602_131649"

r = requests.get(
    f"{BASE_URL}/logs",
    params={"session_id": SESSION_ID, "limit": 10000},
    headers={"ngrok-skip-browser-warning": "true"},
    timeout=30
)
frames = r.json().get("frames", [])
print(f"총 프레임 수: {len(frames)}")

# danger 프레임 추출
danger_frames = []
for f in sorted(frames, key=lambda x: x["frame_number"]):
    risks = [o["risk_level"] for o in f.get("objects", [])]
    if "danger" in risks:
        danger_frames.append(f["frame_number"])

print(f"danger 프레임 수: {len(danger_frames)}")
print(f"danger 프레임 목록: {danger_frames}")

# 연속 구간 분석
if danger_frames:
    groups = []
    group = [danger_frames[0]]
    for fn in danger_frames[1:]:
        if fn == group[-1] + 1:
            group.append(fn)
        else:
            groups.append(group)
            group = [fn]
    groups.append(group)

    print(f"\n연속 구간 {len(groups)}개:")
    for g in groups:
        print(f"  프레임 {g[0]}~{g[-1]} → {len(g)}프레임 연속")
    print(f"\n최대 연속 길이: {max(len(g) for g in groups)}")
