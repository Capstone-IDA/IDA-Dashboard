import requests

BASE_URL = "https://practitioner-productivity-reduction-manufacturer.trycloudflare.com"
SESSION_ID = "sess_scenario_3_0602_131649"
#SESSION_ID = "sess_scenario_4_0602_131649"

r = requests.get(
    f"{BASE_URL}/logs",
    params={"session_id": SESSION_ID, "limit": 10000},
    headers={"ngrok-skip-browser-warning": "true"},
    timeout=30
)
frames = r.json().get("frames", [])
frames_sorted = sorted(frames, key=lambda x: x["frame_number"])
total = len(frames_sorted)
print(f"총 프레임 수: {total}")

# collision_warning 프레임 추출
flagged = [f["frame_number"] for f in frames_sorted if f.get("collision_warning")]
print(f"collision_warning=True 프레임 수: {len(flagged)}")
print(f"프레임 번호 목록: {flagged}")

# 연속 구간 분석
if flagged:
    groups = []
    group = [flagged[0]]
    for fn in flagged[1:]:
        if fn == group[-1] + 1:
            group.append(fn)
        else:
            groups.append(group)
            group = [fn]
    groups.append(group)

    print(f"\n연속 구간 {len(groups)}개:")
    for g in groups:
        print(f"  프레임 {g[0]}~{g[-1]} → {len(g)}프레임 연속")

    # 구간 사이 간격(gap) 확인 → gap_fill=12 적정성 체크
    print("\n구간 사이 간격:")
    for (g1, g2) in zip(groups, groups[1:]):
        gap = g2[0] - g1[-1]
        print(f"  {g1[-1]} → {g2[0]} : gap={gap}")

# 영상 프레임 인덱스로 변환 시 위치 확인 (scale 적용)
if flagged:
    max_det = max(f["frame_number"] for f in frames_sorted) + 1
    print(f"\n탐지 프레임 수(max_det): {max_det}")
    print("⚠ 영상의 실제 총 프레임 수(cv2.CAP_PROP_FRAME_COUNT)를 알아야 scale 계산 가능")
    print("   scale = max_det / 영상총프레임수")
    print("   배너 뜨는 영상 프레임 idx = round(원본프레임idx * scale)")
