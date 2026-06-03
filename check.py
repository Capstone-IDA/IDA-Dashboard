import requests

# 제주렌터카 로그인
r = requests.post(
    'https://unfocusedly-pleurocarpous-gina.ngrok-free.dev/auth/login',
    json={"username": "jeju_rental", "password": "jeju1234"},
    headers={"ngrok-skip-browser-warning": "true"},
    timeout=10
)
token = r.json().get("token", "")
print("토큰:", token[:30], "...")

# company dashboard 조회
r2 = requests.get(
    'https://unfocusedly-pleurocarpous-gina.ngrok-free.dev/company/dashboard',
    headers={"Authorization": f"Bearer {token}", "ngrok-skip-browser-warning": "true"},
    timeout=10
)
print("dashboard:", r2.json())