import requests
import json

BASE_URL = "https://practitioner-productivity-reduction-manufacturer.trycloudflare.com"
SESSION_ID = "sess_scenario_3_0602_131649"

r = requests.get(
    f"{BASE_URL}/logs",
    params={"session_id": SESSION_ID, "limit": 1},
    headers={"ngrok-skip-browser-warning": "true"},
    timeout=30
)
data = r.json()

print("=== 최상위 키 ===")
print(list(data.keys()))

frames = data.get("frames", [])
if frames:
    print("\n=== frame 1개의 전체 내용 ===")
    print(json.dumps(frames[0], indent=2, ensure_ascii=False))
