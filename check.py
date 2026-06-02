import requests
r = requests.get(
    'https://unfocusedly-pleurocarpous-gina.ngrok-free.dev/logs',
    params={'session_id': 'sess_scenario_2_8eebf6', 'limit': 10000},
    headers={'ngrok-skip-browser-warning': 'true'},
    timeout=15
)
data = r.json()
frames = data['frames']
DYNAMIC = {"Vehicle", "Human", "Two-wheeled Vehicle", "Wheelchair", "Stroller", "Shopping Cart", "Animal"}
danger = [f['frame_number'] for f in frames if any(o['risk_level']=='danger' and o['class_name'] in DYNAMIC for o in f['objects'])]
print(f'총 프레임: {len(frames)}')
print(f'danger 프레임들: {danger}')
if danger:
    fps = 30
    print(f'danger 시작: {min(danger)/fps:.1f}초 ~ 끝: {max(danger)/fps:.1f}초')