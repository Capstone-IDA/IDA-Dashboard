import requests
import json

BASE_URL = "https://practitioner-productivity-reduction-manufacturer.trycloudflare.com"

endpoints = [
    "/company/scores",
    "/company/events",
    "/company/notifications",
    "/company/blacklist",
]

for ep in endpoints:
    print(f"\n{'='*40}")
    print(f"GET {ep}")
    try:
        r = requests.get(f"{BASE_URL}{ep}",
            headers={"ngrok-skip-browser-warning": "true"}, timeout=10)
        print(f"status: {r.status_code}")
        try:
            data = r.json()
            print(json.dumps(data, indent=2, ensure_ascii=False)[:1000])
        except Exception:
            print("(JSON 아님)", r.text[:300])
    except Exception as e:
        print(f"오류: {e}")
