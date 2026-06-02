# -*- coding: utf-8 -*-
"""
IDA — 시나리오 영상 전처리 스크립트
실행: python preprocess_videos.py
출력: videos/annotated/test_scenario_{1~4}.mp4
"""
import cv2, numpy as np, os, subprocess, shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

VIDEOS_DIR = Path("videos")
OUT_DIR    = VIDEOS_DIR / "annotated"
OUT_DIR.mkdir(parents=True, exist_ok=True)

def get_font(size):
    for name in ["malgun.ttf","malgunbd.ttf","gulim.ttc",
                 "C:/Windows/Fonts/malgun.ttf","C:/Windows/Fonts/gulim.ttc",
                 "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"]:
        try: return ImageFont.truetype(name, size)
        except: continue
    return ImageFont.load_default()

CLASS_KO = {"Vehicle":"차량","Human":"보행자","Pillar":"기둥",
            "Cone":"콘","Person":"사람","Wall":"벽","Sign":"표지판"}
def ko(n): return CLASS_KO.get(n, n)

def get_risk(depth, speed, moving):
    if depth <= 0.15: return "DANGER", (220,40,40)
    if depth <= 0.35 and moving and speed>1.0: return "DANGER", (220,40,40)
    if depth <= 0.35: return "WARNING", (240,180,0)
    return "SAFE", (30,190,30)

def cv2pil(frame): return Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
def pil2cv(img):   return cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)

def alpha_composite(img, overlay):
    """RGBA overlay를 img에 합성"""
    return Image.alpha_composite(img, overlay)

def draw_bbox_pil(img, obj, fh, fw):
    b = obj["bbox"]
    x1,y1 = int(b["x"]*fw), int(b["y"]*fh)
    x2,y2 = int((b["x"]+b["w"])*fw), int((b["y"]+b["h"])*fh)
    risk, rgb = get_risk(obj["depth_val"], obj["obj_speed_px"], obj["is_moving"])

    ov = Image.new("RGBA", img.size, (0,0,0,0))
    d  = ImageDraw.Draw(ov)

    # 반투명 박스
    d.rectangle([x1,y1,x2,y2], outline=rgb+(255,), width=2, fill=rgb+(20,))

    # 코너 강조
    cl = min(x2-x1, y2-y1)//4
    for (ax,ay),(bx,by) in [
        ((x1,y1),(x1+cl,y1)),((x1,y1),(x1,y1+cl)),
        ((x2,y1),(x2-cl,y1)),((x2,y1),(x2,y1+cl)),
        ((x1,y2),(x1+cl,y2)),((x1,y2),(x1,y2-cl)),
        ((x2,y2),(x2-cl,y2)),((x2,y2),(x2,y2-cl)),
    ]:
        d.line([(ax,ay),(bx,by)], fill=rgb+(255,), width=3)

    # 한글 라벨
    font  = get_font(max(14, int(fh*0.022)))
    label = f"[{risk}] {ko(obj['class_name'])} {obj['confidence']:.0%}"
    bb    = font.getbbox(label)
    tw,th = bb[2]-bb[0], bb[3]-bb[1]
    try:
        d.rounded_rectangle([x1, y1-th-12, x1+tw+10, y1], radius=5, fill=rgb+(220,))
    except:
        d.rectangle([x1, y1-th-12, x1+tw+10, y1], fill=rgb+(220,))
    d.text((x1+5, y1-th-8), label, font=font, fill=(255,255,255,255))

    return alpha_composite(img, ov)

def draw_alert_pil(img, title, sub, level="DANGER"):
    w, h = img.size
    bx1,by1 = int(w*0.25), int(h*0.03)
    bx2,by2 = int(w*0.75), int(h*0.19)
    bg = (200,30,30,215) if level=="DANGER" else (200,120,10,205)

    ov = Image.new("RGBA", img.size, (0,0,0,0))
    d  = ImageDraw.Draw(ov)
    try:
        d.rounded_rectangle([bx1,by1,bx2,by2], radius=16, fill=bg)
    except:
        d.rectangle([bx1,by1,bx2,by2], fill=bg)

    ft = get_font(max(18, int(h*0.045)))
    fs = get_font(max(13, int(h*0.028)))
    cx = (bx1+bx2)//2
    cy = (by1+by2)//2

    bt = ft.getbbox(title); tw = bt[2]-bt[0]
    d.text((cx-tw//2, cy - int(h*0.035)), title, font=ft, fill=(255,255,255,255))
    bs = fs.getbbox(sub);   sw = bs[2]-bs[0]
    d.text((cx-sw//2, cy + int(h*0.008)), sub,   font=fs, fill=(255,240,210,220))

    return alpha_composite(img, ov)

def draw_infobar(img, sdesc):
    """하단 정보바 — 프레임 하단에 반투명 오버레이"""
    w, h = img.size
    bar_h = max(52, int(h * 0.08))

    ov = Image.new("RGBA", img.size, (0,0,0,0))
    d  = ImageDraw.Draw(ov)

    # 반투명 배경
    d.rectangle([0, h-bar_h, w, h], fill=(5, 8, 16, 210))
    d.line([(0, h-bar_h), (w, h-bar_h)], fill=(30, 42, 58, 255), width=1)

    ft = get_font(max(15, int(bar_h * 0.38)))
    fs = get_font(max(11, int(bar_h * 0.24)))

    # 가운데 텍스트
    title = "● 주차 감시 모드 활성화"
    bt = ft.getbbox(title); tw = bt[2]-bt[0]
    cy = h - bar_h//2
    d.text((w//2 - tw//2, cy - int(bar_h*0.22)), title, font=ft, fill=(56,189,248,255))

    bs = fs.getbbox(sdesc); sw = bs[2]-bs[0]
    d.text((w//2 - sw//2, cy + int(bar_h*0.12)), sdesc, font=fs, fill=(74,85,104,255))

    return alpha_composite(img, ov)

def draw_hud(img, fps, frame_id):
    ov = Image.new("RGBA", img.size, (0,0,0,0))
    d  = ImageDraw.Draw(ov)
    d.ellipse([12,14,26,28], fill=(220,0,0,200))
    font = get_font(16)
    d.text((30,14), f"REC  {fps:.0f}FPS", font=font, fill=(220,0,0,255))
    d.text((img.size[0]-70,14), f"F:{frame_id}", font=font, fill=(100,110,130,255))
    return alpha_composite(img, ov)

def get_objects(sn, fn, total):
    progress = fn / max(total-1,1)
    objs = []
    if sn == 4:
        t = fn/24
        dv = max(0.05, 0.60-(t-7.0)*1.5) if t>=7 else 0.60
        mv = t>=7.0
        objs.append({"class_name":"Vehicle","confidence":0.95,
            "bbox":{"x":0.08,"y":0.28,"w":0.35,"h":0.45},
            "depth_val":dv,"obj_speed_px":3.2 if mv else 0.2,"is_moving":mv})
        if t>=7.0:
            objs.append({"class_name":"Vehicle","confidence":0.88,
                "bbox":{"x":0.55,"y":0.30,"w":0.28,"h":0.38},
                "depth_val":max(0.08,0.50-(t-7.0)*2.0),"obj_speed_px":2.5,"is_moving":True})
    elif sn == 3:
        objs.append({"class_name":"Pillar","confidence":0.92,
            "bbox":{"x":0.80,"y":0.15,"w":0.06,"h":0.55},
            "depth_val":0.75,"obj_speed_px":0.0,"is_moving":False})
        if progress>0.4:
            objs.append({"class_name":"Human","confidence":0.74,
                "bbox":{"x":0.50,"y":0.30,"w":0.12,"h":0.38},
                "depth_val":max(0.25,0.32-progress*0.1),"obj_speed_px":1.2,"is_moving":True})
    else:
        objs.append({"class_name":"Vehicle","confidence":0.91,
            "bbox":{"x":0.15,"y":0.32,"w":0.25,"h":0.38},
            "depth_val":0.50+progress*0.2,"obj_speed_px":0.4,"is_moving":False})
        objs.append({"class_name":"Pillar","confidence":0.89,
            "bbox":{"x":0.82,"y":0.14,"w":0.05,"h":0.52},
            "depth_val":0.80,"obj_speed_px":0.0,"is_moving":False})
    return objs

SCENARIO_DESC = {1:"지하주차장 일반 주행", 2:"주차장 진입 및 후진 주차",
                 3:"나선형 램프 상승 → 주차 탐색", 4:"직선 램프 상승 → 우측 차량 충돌"}

def process_video(sn):
    src = VIDEOS_DIR / f"test_scenario_{sn}.mp4"
    dst = OUT_DIR    / f"test_scenario_{sn}.mp4"
    if not src.exists(): print(f"  ⚠ 없음: {src}"); return

    cap   = cv2.VideoCapture(str(src))
    fps   = cap.get(cv2.CAP_PROP_FPS) or 24
    w     = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h     = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    sdesc = SCENARIO_DESC.get(sn, "")

    tmp_dst = str(dst) + ".tmp.avi"
    out = cv2.VideoWriter(tmp_dst, cv2.VideoWriter_fourcc(*"XVID"), fps, (w, h))

    print(f"  시나리오 {sn}: {total}프레임 ({total/fps:.1f}초)")
    for fn in range(total):
        ret, frame = cap.read()
        if not ret: break

        fh, fw = frame.shape[:2]
        objs   = get_objects(sn, fn, total)
        img    = cv2pil(frame)

        for obj in objs:
            img = draw_bbox_pil(img, obj, fh, fw)

        danger  = [o for o in objs if get_risk(o["depth_val"],o["obj_speed_px"],o["is_moving"])[0]=="DANGER"]
        warning = [o for o in objs if get_risk(o["depth_val"],o["obj_speed_px"],o["is_moving"])[0]=="WARNING"]
        if danger:
            img = draw_alert_pil(img, "⚠ 추돌 주의",
                                 "전방 "+"·".join(set(ko(o["class_name"]) for o in danger))+" 근접 감지", "DANGER")
        elif warning:
            img = draw_alert_pil(img, "⚡ 접근 물체 감지",
                                 "·".join(set(ko(o["class_name"]) for o in warning))+" 주의 구간", "WARNING")

        img = draw_hud(img, fps, fn)
        img = draw_infobar(img, sdesc)  # 하단 정보바
        out.write(pil2cv(img))

        if fn % 150 == 0:
            print(f"    {fn}/{total} ({fn/total*100:.0f}%)")

    cap.release(); out.release()

    # ffmpeg으로 MP4(H.264 faststart) 변환
    r = subprocess.run(
        ["ffmpeg","-y","-i",tmp_dst,
         "-c:v","libx264","-profile:v","baseline","-level","3.0",
         "-movflags","+faststart","-c:a","aac", str(dst)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    os.remove(tmp_dst)
    print(f"  ✅ 완료: {dst}" if r.returncode==0 else f"  ❌ ffmpeg 실패")

if __name__ == "__main__":
    print("=== IDA 영상 전처리 ===")
    for s in [1,2,3,4]:
        process_video(s)
    print("\n완료!")
