#!/usr/bin/env python3
"""Original 2D cartoon Hindi/Hinglish entertainment Shorts renderer - Phase 2 quality test."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import shutil
import subprocess
import wave
from array import array
from pathlib import Path

import edge_tts
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 720, 1280, 24
MIN_DURATION, MAX_DURATION = 30.0, 58.0

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
FRAMES = BUILD / "frames"
VOICE_DIR = BUILD / "voice"
AUDIO_DIR = BUILD / "audio"
VIDEO_ONLY = BUILD / "video-only.mp4"
VOICE_WAV = AUDIO_DIR / "voice.wav"
MIX_WAV = AUDIO_DIR / "mix.wav"
OUT = BUILD / "cartoon-short.mp4"
TIMELINE = BUILD / "story.json"

FONT_BOLD = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
]
FONT_REG = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
]

C = {
    "ink": (24, 25, 30),
    "muted": (96, 98, 104),
    "white": (255, 255, 255),
    "hero": (43, 111, 224),
    "hero_light": (223, 235, 255),
    "mom": (216, 76, 103),
    "mom_light": (255, 226, 235),
    "skin": (255, 238, 216),
    "red": (218, 61, 61),
}


def ft(paths, size):
    for p in paths:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


TITLE = ft(FONT_BOLD, 50)
SUBTITLE = ft(FONT_BOLD, 36)
CAPTION = ft(FONT_BOLD, 34)
SMALL = ft(FONT_REG, 23)
TINY = ft(FONT_REG, 18)


def run(cmd):
    subprocess.run(cmd, check=True)


def duration(path: Path) -> float:
    raw = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        text=True,
    )
    return float(raw.strip())


def tw(draw, text, font):
    b = draw.textbbox((0, 0), text, font=font)
    return b[2] - b[0]


def wrap(draw, text, font, max_width):
    words = text.split()
    lines, cur = [], ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if tw(draw, trial, font) <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def centered(draw, text, y, font, max_width, fill=C["ink"]):
    lines = wrap(draw, text, font, max_width)
    lh = font.getbbox("Ag")[3] - font.getbbox("Ag")[1] + 7
    for i, line in enumerate(lines):
        draw.text(((W - tw(draw, line, font)) // 2, y + i * lh), line, font=font, fill=fill)


def background(draw, kind):
    colors = {
        "room": ((238, 242, 248), (223, 214, 201)),
        "hall": ((247, 240, 230), (220, 213, 201)),
        "street": ((229, 240, 248), (106, 112, 122)),
    }
    top, floor = colors.get(kind, colors["room"])
    draw.rectangle((0, 0, W, 920), fill=top)
    draw.rectangle((0, 920, W, H), fill=floor)

    if kind == "room":
        draw.rectangle((70, 170, 650, 530), fill=(212, 232, 246), outline=(62, 72, 83), width=4)
        draw.line((360, 170, 360, 530), fill=(62, 72, 83), width=3)
        draw.line((70, 350, 650, 350), fill=(62, 72, 83), width=3)
        draw.rounded_rectangle((98, 600, 622, 875), 36, fill=(183, 120, 111), outline=(91, 67, 60), width=4)
        draw.rounded_rectangle((135, 700, 310, 835), 24, fill=(229, 184, 178))
        draw.rounded_rectangle((410, 700, 585, 835), 24, fill=(229, 184, 178))
    elif kind == "hall":
        draw.rectangle((530, 170, 670, 825), fill=(188, 155, 116), outline=(90, 67, 51), width=4)
        draw.ellipse((585, 480, 605, 500), fill=(90, 67, 51))
        draw.rectangle((62, 700, 245, 860), fill=(196, 195, 194), outline=(94, 94, 94), width=3)
        draw.rectangle((476, 700, 658, 860), fill=(196, 195, 194), outline=(94, 94, 94), width=3)
    else:
        draw.rectangle((0, 760, W, 920), fill=(105, 111, 121))
        for x in range(-80, W + 80, 180):
            draw.rounded_rectangle((x, 835, x + 105, 855), 8, fill=(247, 244, 210))
        draw.rectangle((75, 235, 250, 555), fill=(209, 196, 180), outline=(84, 80, 74), width=4)
        draw.rectangle((100, 260, 225, 430), fill=(191, 220, 233))
        draw.rectangle((515, 430, 555, 615), fill=(98, 62, 34))
        draw.ellipse((480, 355, 590, 470), fill=(63, 132, 70))
    draw.rectangle((0, 910, W, 930), fill=(56, 58, 63))


def phone(draw, x, y, s=1.0, alert=False):
    w, h = int(118*s), int(208*s)
    draw.rounded_rectangle((x, y, x+w, y+h), 20, fill=(27, 29, 34), outline=(7, 7, 8), width=4)
    sx, sy = x+10, y+16
    draw.rounded_rectangle((sx, sy, x+w-10, y+h-16), 11, fill=(225, 241, 252))
    draw.rectangle((sx+14, sy+40, x+w-24, sy+49), fill=(91, 137, 218))
    draw.rectangle((sx+14, sy+66, x+w-42, sy+74), fill=(160, 173, 187))
    draw.rectangle((sx+14, sy+91, x+w-34, sy+99), fill=(160, 173, 187))
    draw.text((sx+15, sy+12), "98%", font=TINY, fill=C["red"] if alert else C["muted"])


def exclaim(draw, x, y, size=72):
    draw.text((x, y), "!!!", font=ft(FONT_BOLD, size), fill=C["red"])


def face(draw, cx, cy, mood, speaking, frame, s):
    ey = int(cy - 10*s)
    dx = int(18*s)
    dot = max(2, int(4*s))
    if mood in {"shock", "panic"}:
        r = dot + 4
        draw.ellipse((cx-dx-r, ey-r, cx-dx+r, ey+r), fill=C["ink"])
        draw.ellipse((cx+dx-r, ey-r, cx+dx+r, ey+r), fill=C["ink"])
    elif frame % 54 < 3:
        draw.line((cx-dx-8, ey, cx-dx+8, ey), fill=C["ink"], width=max(2, dot))
        draw.line((cx+dx-8, ey, cx+dx+8, ey), fill=C["ink"], width=max(2, dot))
    else:
        draw.ellipse((cx-dx-dot, ey-dot, cx-dx+dot, ey+dot), fill=C["ink"])
        draw.ellipse((cx+dx-dot, ey-dot, cx+dx+dot, ey+dot), fill=C["ink"])

    if mood in {"happy", "proud", "laugh"}:
        draw.arc((cx-24, ey+10, cx+24, ey+44), 20, 160, fill=C["ink"], width=max(2, dot))
    elif mood in {"sad", "tired"}:
        draw.arc((cx-24, ey+22, cx+24, ey+58), 195, 345, fill=C["ink"], width=max(2, dot))
    elif speaking:
        open_now = (frame // 3) % 2 == 0
        if open_now:
            draw.ellipse((cx-8, ey+28, cx+8, ey+48), fill=C["ink"])
        else:
            draw.line((cx-10, ey+39, cx+10, ey+39), fill=C["ink"], width=max(2, dot))
    else:
        draw.line((cx-10, ey+39, cx+10, ey+39), fill=C["ink"], width=max(2, dot))


def _limb(draw, a, b, fill, width):
    draw.line((a[0], a[1], b[0], b[1]), fill=fill, width=width)
    r=max(5, width//2)
    draw.ellipse((b[0]-r, b[1]-r, b[0]+r, b[1]+r), fill=fill)


def _hand(draw, x, y, r, fill):
    draw.ellipse((x-r, y-r, x+r, y+r), fill=fill, outline=C["ink"], width=max(1, r//4))


def _shoe(draw, x, y, side, s):
    w=int(58*s); h=int(24*s)
    if side < 0:
        box=(x-w, y-h, x+8, y+6)
    else:
        box=(x-8, y-h, x+w, y+6)
    draw.rounded_rectangle(box, 10, fill=(38,39,44), outline=C["ink"], width=max(2,int(2*s)))


def _hair(draw, cx, cy, role, s):
    dark=(35,30,29)
    if role=="hero":
        pts=[
            (cx-int(42*s),cy-int(28*s)),(cx-int(30*s),cy-int(54*s)),
            (cx-int(8*s),cy-int(68*s)),(cx+int(5*s),cy-int(48*s)),
            (cx+int(24*s),cy-int(66*s)),(cx+int(44*s),cy-int(38*s)),
            (cx+int(52*s),cy-int(8*s)),(cx-int(50*s),cy-int(6*s))
        ]
        draw.polygon(pts, fill=dark)
    else:
        draw.ellipse((cx+int(32*s), cy-int(62*s), cx+int(74*s), cy-int(20*s)), fill=dark, outline=C["ink"], width=max(2,int(2*s)))
        draw.ellipse((cx-int(48*s),cy-int(58*s),cx+int(48*s),cy+int(8*s)), fill=dark)
        draw.pieslice((cx-int(49*s),cy-int(71*s),cx+int(49*s),cy+int(30*s)), 185, 355, fill=dark)


def _cartoon_face(draw, cx, cy, mood, speaking, frame, s):
    eye_y=cy-int(8*s)
    ex=int(18*s)
    er=max(3,int(5*s))
    brow=max(2,int(4*s))

    if mood in {"shock","panic"}:
        draw.ellipse((cx-ex-er,eye_y-er,cx-ex+er,eye_y+er), fill=C["ink"])
        draw.ellipse((cx+ex-er,eye_y-er,cx+ex+er,eye_y+er), fill=C["ink"])
        draw.line((cx-ex-int(10*s),eye_y-int(13*s),cx-ex+int(8*s),eye_y-int(18*s)), fill=C["ink"], width=brow)
        draw.line((cx+ex-int(8*s),eye_y-int(18*s),cx+ex+int(10*s),eye_y-int(13*s)), fill=C["ink"], width=brow)
    else:
        blink=(frame % 72) in (0,1,2)
        if blink:
            draw.line((cx-ex-int(7*s),eye_y,cx-ex+int(7*s),eye_y), fill=C["ink"], width=brow)
            draw.line((cx+ex-int(7*s),eye_y,cx+ex+int(7*s),eye_y), fill=C["ink"], width=brow)
        else:
            for dx in (-ex,ex):
                draw.ellipse((cx+dx-er,eye_y-er,cx+dx+er,eye_y+er), fill=C["white"], outline=C["ink"], width=max(1,brow//2))
                pupil_x=cx+dx+int(2*s*math.sin(frame/10))
                draw.ellipse((pupil_x-int(3*s),eye_y-int(3*s),pupil_x+int(3*s),eye_y+int(3*s)), fill=C["ink"])
        if mood in {"scold","angry"}:
            draw.line((cx-ex-int(8*s),eye_y-int(10*s),cx-ex+int(7*s),eye_y-int(5*s)), fill=C["ink"], width=brow)
            draw.line((cx+ex-int(7*s),eye_y-int(5*s),cx+ex+int(8*s),eye_y-int(10*s)), fill=C["ink"], width=brow)

    # Small nose plus expressive mouth.
    draw.ellipse((cx-int(3*s),cy+int(7*s),cx+int(3*s),cy+int(13*s)), fill=(215,170,143))
    if mood in {"happy","proud","laugh","celebrate"}:
        draw.arc((cx-int(20*s),cy+int(14*s),cx+int(20*s),cy+int(44*s)), 15, 165, fill=C["ink"], width=max(2,int(3*s)))
    elif mood in {"sad","tired"}:
        draw.arc((cx-int(20*s),cy+int(24*s),cx+int(20*s),cy+int(50*s)), 195, 345, fill=C["ink"], width=max(2,int(3*s)))
    elif speaking:
        open_now=(frame//3)%2==0
        if open_now:
            draw.ellipse((cx-int(9*s),cy+int(19*s),cx+int(9*s),cy+int(43*s)), fill=C["ink"])
            draw.ellipse((cx-int(5*s),cy+int(22*s),cx+int(5*s),cy+int(29*s)), fill=(248,176,176))
        else:
            draw.rounded_rectangle((cx-int(10*s),cy+int(27*s),cx+int(10*s),cy+int(34*s)), 3, fill=C["ink"])
    else:
        draw.line((cx-int(10*s),cy+int(31*s),cx+int(10*s),cy+int(31*s)), fill=C["ink"], width=max(2,int(3*s)))


def character(draw, x, ground, t, role, mood, speaking, frame, s=1.0):
    # Fully drawn cartoon character: head, hair, clothing, hands and shoes.
    body = C["hero"] if role=="hero" else C["mom"]
    skin = C["skin"]
    ph=t*math.tau

    if mood=="run":
        swing=math.sin(ph*2.2)*62
        arm_data=[(-92,28+swing),(92,40-swing)]
        leg_data=[(-72-swing*.35,6),(72+swing*.35,8)]
    elif mood=="panic":
        arm_data=[(-118,-54),(118,-72)]
        leg_data=[(-82,6),(82,8)]
    elif mood=="celebrate":
        arm_data=[(-112,-98),(112,-98)]
        leg_data=[(-70,6),(70,6)]
    elif mood=="scold":
        arm_data=[(-82,22),(112,-48)]
        leg_data=[(-68,5),(68,5)]
    elif mood=="phone":
        arm_data=[(-82,30),(62,-5)]
        leg_data=[(-66,5),(66,5)]
    elif mood=="sad":
        arm_data=[(-75,43),(75,43)]
        leg_data=[(-60,5),(60,5)]
    else:
        sway=math.sin(ph)*9
        arm_data=[(-84,30+sway),(84,30-sway)]
        leg_data=[(-64,5),(64,5)]

    torso_top=ground-int(270*s)
    hip=ground-int(132*s)
    head=torso_top-int(92*s)
    hr=int(50*s)
    lw=max(7,int(11*s))
    outline=max(2,int(3*s))

    # Ground shadow.
    draw.ellipse((x-int(78*s),ground+2,x+int(78*s),ground+24), fill=(194,196,201))

    # Legs with pants and shoes.
    pants=(39,48,70) if role=="hero" else (82,54,65)
    for dx,dy in leg_data:
        kx=x+int(dx*s); ky=hip+int(34*s)
        fx=x+int(dx*s); fy=ground+int(dy*s)
        _limb(draw,(kx,ky),(fx,fy),pants,max(12,int(22*s)))
    _shoe(draw,x+int(leg_data[0][0]*s),ground+int(leg_data[0][1]*s),-1,s)
    _shoe(draw,x+int(leg_data[1][0]*s),ground+int(leg_data[1][1]*s),1,s)

    # Body.
    if role=="hero":
        draw.rounded_rectangle(
            (x-int(57*s),torso_top,x+int(57*s),hip+int(26*s)),
            int(26*s), fill=C["hero_light"], outline=body, width=outline
        )
        draw.rounded_rectangle(
            (x-int(45*s),torso_top+int(14*s),x+int(45*s),hip),
            int(20*s), fill=(255,255,255)
        )
        draw.rectangle((x-int(12*s),torso_top+int(55*s),x+int(12*s),torso_top+int(69*s)), fill=body)
    else:
        draw.rounded_rectangle(
            (x-int(60*s),torso_top,x+int(60*s),hip+int(22*s)),
            int(28*s), fill=C["mom_light"], outline=body, width=outline
        )
        draw.polygon([
            (x-int(59*s),torso_top+int(8*s)),
            (x+int(4*s),torso_top+int(8*s)),
            (x+int(48*s),hip+int(23*s)),
            (x-int(18*s),hip+int(23*s))
        ], fill=(255,244,248))

    # Arms, sleeves and hands.
    sleeve_fill=body
    for dx,dy in arm_data:
        ax=x+int(dx*s); ay=torso_top+int(54*s)+int(dy*s)
        elbow=x+int(dx*0.52*s); ey=torso_top+int(54*s)+int(dy*0.48*s)
        _limb(draw,(x,torso_top+int(54*s)),(elbow,ey),sleeve_fill,max(12,int(20*s)))
        _limb(draw,(elbow,ey),(ax,ay),skin,max(10,int(15*s)))
        _hand(draw,ax,ay,max(9,int(11*s)),skin)

    # Neck and head.
    draw.rounded_rectangle(
        (x-int(16*s),head+int(30*s),x+int(16*s),head+int(62*s)),
        10, fill=skin, outline=C["ink"], width=outline
    )
    draw.ellipse((x-hr,head-hr,x+hr,head+hr), fill=skin, outline=C["ink"], width=outline)
    _hair(draw,x,head,role,s)
    _cartoon_face(draw,x,head,mood,speaking,frame,s)

    # Tiny clothing cue makes characters easy to distinguish.
    if role=="hero":
        draw.ellipse((x-int(15*s),torso_top+int(18*s),x+int(15*s),torso_top+int(48*s)), fill=body)
        draw.text((x-int(10*s),torso_top+int(20*s)), "★", font=ft(FONT_BOLD,int(16*s)), fill=C["white"])
    else:
        draw.ellipse((x+int(36*s),hip-int(62*s),x+int(55*s),hip-int(43*s)), fill=(247,191,70), outline=C["ink"], width=max(1,int(2*s)))

def caption_box(draw, text, p):
    f = ft(FONT_BOLD, 34 + int(2*math.sin(math.pi*p)))
    lines = wrap(draw, text, f, 575)
    lh = 41
    h = 32 + lh*len(lines)
    top = 1000
    draw.rounded_rectangle((40, top, 680, top+h), 28, fill=C["white"], outline=C["ink"], width=3)
    for i, line in enumerate(lines):
        draw.text(((W-tw(draw, line, f))//2, top+15+i*lh), line, font=f, fill=C["ink"])


def caption_chunks(text, dur):
    words = text.split()
    if not words:
        return []
    size = 3 if len(words) <= 12 else 4
    chunks = [" ".join(words[i:i+size]) for i in range(0, len(words), size)]
    weights = [max(1, len(c.replace(" ", ""))) for c in chunks]
    total = sum(weights)
    out, t = [], 0.0
    for wt, chunk in zip(weights, chunks):
        span = dur*wt/total
        out.append((t, min(dur, t+span), chunk))
        t += span
    return out


def camera(img, scene_index, t):
    # A gentle push/pan prevents the composition from feeling like a frozen card.
    zoom = 1.0 + 0.045*math.sin(math.pi*t) + (0.035 if scene_index in {3, 6} else 0)
    pan = int((18 if scene_index % 2 else -18) * math.sin(math.pi*t))
    nw, nh = int(W*zoom), int(H*zoom)
    scaled = img.resize((nw, nh), Image.Resampling.LANCZOS)
    left = max(0, min(nw-W, (nw-W)//2 + pan))
    top = max(0, min(nh-H, (nh-H)//2 + int(10*math.sin(math.pi*t))))
    return scaled.crop((left, top, left+W, top+H))


def story(topic):
    t = " ".join(topic.split()).strip()
    return [
        dict(id="hook", bg="room", shot="close", role="hero", voice="narrator", mood="happy",
             caption="BAS DO MINUTE...", line=f"{t} ka sabse dangerous part pata hai? Jab dimaag bolta hai - bas do minute aur.", event="pop"),
        dict(id="confidence", bg="room", shot="medium", role="hero", voice="hero", mood="proud",
             caption="FULL CONFIDENCE", line="Maine bhi wahi socha. Do minute. Full control. Kya hi galat ho sakta hai?", event="pop"),
        dict(id="interrupt", bg="room", shot="wide", role="mom", voice="mom", mood="scold",
             caption="KYA KAR RAHE HO?", line="Do minute? Beta, ye phone tumhare haath mein kab se hai?", event="hit"),
        dict(id="excuse", bg="room", shot="medium", role="hero", voice="hero", mood="shock",
             caption="MAIN? PHONE? NAHI TOH...", line="Maa, actually main phone nahi chala raha tha. Main... research kar raha tha.", event="whoosh"),
        dict(id="proof", bg="room", shot="close", role="mom", voice="mom", mood="laugh",
             caption="ACHHA?", line="Research? Toh ye teen ghante ka screen time kis subject ka tha?", event="hit"),
        dict(id="panic", bg="hall", shot="shake", role="hero", voice="hero", mood="panic",
             caption="THREE HOURS?!", line="Teen ghante?! Impossible. Phone bhi jhoot bolta hai kya?", event="impact"),
        dict(id="realisation", bg="hall", shot="close", role="hero", voice="narrator", mood="sad",
             caption="ASLI PROBLEM...", line="Aur us moment mujhe samajh aaya: problem phone nahi tha. Overconfidence tha.", event="whoosh"),
        dict(id="punchline", bg="street", shot="wide", role="hero", voice="hero", mood="celebrate",
             caption="BACKUP PLAN RAKHO", line="Agli baar sirf do minute bolne se pehle timer lagaunga. Varna mera phone hi mera boss ban jayega.", event="celebrate"),
    ]


def draw_scene(scene, local, dur, scene_number, total, frame):
    base = Image.new("RGB", (W, H), C["white"])
    draw = ImageDraw.Draw(base)
    background(draw, scene["bg"])
    t = local/max(dur, 0.001)
    speaking = True

    # Short title card on entry.
    if t < 0.35:
        alpha = int(255*(1 - t/0.35))
        overlay = Image.new("RGBA", (W, H), (255,255,255,0))
        od = ImageDraw.Draw(overlay)
        od.rounded_rectangle((34, 48, 686, 138), 26, fill=(255,255,255,alpha), outline=(24,25,30,alpha), width=3)
        base = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(base)
        centered(draw, scene["caption"], 72, SUBTITLE, 600)

    if scene["shot"] == "wide":
        hx = int(230 + 55*math.sin(math.pi*t))
        mx = int(490 - 40*math.sin(math.pi*t))
        character(draw, hx, 900, t, "hero", "phone" if scene["id"]=="interrupt" else "normal", scene["voice"]=="hero", frame, 0.92)
        character(draw, mx, 900, t+0.15, "mom", "scold" if scene["id"] in {"interrupt","proof"} else "normal", scene["voice"]=="mom", frame, 0.98)
        if scene["id"] == "interrupt":
            phone(draw, 188, 625, 0.72, True)
    elif scene["shot"] == "shake":
        shake = int(13*math.sin(t*math.tau*7))
        character(draw, 360+shake, 900, t*1.7, "hero", scene["mood"], True, frame, 1.08)
        exclaim(draw, 88, 560, 68)
        exclaim(draw, 525, 600, 68)
    else:
        role = scene["role"] if scene["role"] in {"hero","mom"} else "hero"
        x = 300 if role == "mom" else 420
        ground = 950 if scene["shot"] == "close" else 900
        scale = 1.20 if scene["shot"] == "close" else 1.04
        x += int(18*math.sin(math.pi*2*t))
        character(draw, x, ground, t, role, scene["mood"], True, frame, scale)

        if scene["id"] == "hook":
            phone(draw, 474, 575, 0.80, True)
            exclaim(draw, 530, 515, 58)
        elif scene["id"] == "confidence":
            draw.rounded_rectangle((395, 525, 625, 620), 22, fill=C["white"], outline=C["hero"], width=3)
            centered(draw, "FULL CONTROL", 554, SMALL, 205, C["hero"])
        elif scene["id"] == "excuse":
            phone(draw, 355, 660, 0.72, True)
        elif scene["id"] == "proof":
            draw.rounded_rectangle((190, 515, 390, 610), 22, fill=C["white"], outline=C["mom"], width=3)
            centered(draw, "ACHHA?", 548, SMALL, 165, C["mom"])
        elif scene["id"] == "realisation":
            centered(draw, "...", 565, TITLE, 150, C["muted"])

    chunks = caption_chunks(scene["line"], dur)
    active = chunks[-1][2] if chunks else ""
    for a, b, text in chunks:
        if a <= local <= b:
            active = text
            caption_box(draw, text, (local-a)/max(0.001, b-a))
            break
    if not active:
        caption_box(draw, active, 1.0)

    total_p = (scene_number-1+t)/total
    draw.rounded_rectangle((46, 1180, 674, 1193), 8, fill=(206,207,212))
    draw.rounded_rectangle((46, 1180, 46+int(628*total_p), 1193), 8, fill=C["ink"])

    frame_img = camera(base, scene_number, t)

    # Tiny beat flash makes the hard cuts feel intentional.
    if local < 0.10 and scene["event"] in {"hit","impact"}:
        flash = max(0, int(95*(1-local/0.10)))
        ov = Image.new("RGBA", (W, H), (255,255,255,flash))
        frame_img = Image.alpha_composite(frame_img.convert("RGBA"), ov).convert("RGB")
    return frame_img


async def choose_voice(locale, gender, preferred):
    voices = await edge_tts.list_voices()
    available = {v["ShortName"]: v for v in voices}
    for name in preferred:
        if name in available:
            return name
    matches = [v["ShortName"] for v in voices if v.get("Locale")==locale and v.get("Gender")==gender]
    if matches:
        return matches[0]
    fallback = [v["ShortName"] for v in voices if v.get("Locale")==locale]
    if fallback:
        return fallback[0]
    raise RuntimeError("No hi-IN neural voice available.")


async def make_voice(story_data):
    VOICE_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    narrator = await choose_voice("hi-IN", "Female", ["hi-IN-SwaraNeural", "hi-IN-AnanyaNeural"])
    hero = await choose_voice("hi-IN", "Male", ["hi-IN-MadhurNeural", "hi-IN-KunalNeural", "hi-IN-AaravNeural"])
    mom = await choose_voice("hi-IN", "Female", ["hi-IN-AnanyaNeural", "hi-IN-SwaraNeural", "hi-IN-AartiNeural"])

    voice_map = {"narrator": narrator, "hero": hero, "mom": mom}
    durations, paths = [], []

    for i, scene in enumerate(story_data, 1):
        mp3 = VOICE_DIR / f"scene-{i}.mp3"
        wav = VOICE_DIR / f"scene-{i}.wav"
        selected = voice_map[scene["voice"]]
        rate = "+2%" if scene["voice"] == "mom" else "+6%"
        pitch = "+2Hz" if scene["voice"] == "mom" else ("0Hz" if scene["voice"] == "hero" else "+1Hz")
        await edge_tts.Communicate(
            scene["line"], voice=selected, rate=rate, pitch=pitch, volume="+0%"
        ).save(str(mp3))
        run([
            "ffmpeg","-y","-hide_banner","-loglevel","error","-i",str(mp3),
            "-af","loudnorm=I=-16:TP=-1.5:LRA=9","-ar","48000","-ac","1",str(wav)
        ])
        durations.append(duration(wav))
        paths.append(wav)

    lst = AUDIO_DIR / "concat.txt"
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in paths), encoding="utf-8")
    run([
        "ffmpeg","-y","-hide_banner","-loglevel","error","-f","concat","-safe","0",
        "-i",str(lst),"-ar","48000","-ac","1","-c:a","pcm_s16le",str(VOICE_WAV)
    ])
    return durations, voice_map


def write_frames(story_data, durations):
    FRAMES.mkdir(parents=True, exist_ok=True)
    idx = 0
    for sn, (scene, dur) in enumerate(zip(story_data, durations), 1):
        count = max(1, math.ceil(dur*FPS))
        for n in range(count):
            local = n/FPS
            draw_scene(scene, local, dur, sn, len(story_data), idx).save(
                FRAMES/f"frame-{idx:06d}.png", optimize=True
            )
            idx += 1


def render_video():
    run([
        "ffmpeg","-y","-hide_banner","-loglevel","error",
        "-framerate",str(FPS),"-i",str(FRAMES/"frame-%06d.png"),
        "-c:v","libx264","-preset","medium","-crf","19","-pix_fmt","yuv420p",
        "-movflags","+faststart",str(VIDEO_ONLY)
    ])


def read_wav(path):
    with wave.open(str(path),"rb") as wf:
        ch, rate, width = wf.getnchannels(), wf.getframerate(), wf.getsampwidth()
        if (ch, rate, width) != (1, 48000, 2):
            raise RuntimeError("Unexpected normalized audio format")
        return array("h", wf.readframes(wf.getnframes())), rate


def mix_audio(story_data, durations):
    samples, rate = read_wav(VOICE_WAV)
    out = array("h", samples)

    scene_start = 0.0
    notes = [220.0, 196.0, 174.61, 196.0]
    note_len = 1.6

    def add_tone(start, secs, freq, gain):
        begin = int(start*rate)
        length = min(int(secs*rate), max(0, len(out)-begin))
        for i in range(length):
            env = min(1.0, i/(rate*0.012), (length-i)/(rate*0.06))
            val = math.sin(2*math.pi*freq*i/rate)*32767*gain*env
            out[begin+i] = max(-32768, min(32767, int(out[begin+i]+val)))

    # Soft continuous music bed.
    for i in range(len(out)):
        t = i/rate
        chord = notes[int(t/note_len)%len(notes)]
        pad = (
            math.sin(2*math.pi*chord*t)
            + 0.55*math.sin(2*math.pi*chord*1.5*t)
        ) * 32767 * 0.028
        out[i] = max(-32768, min(32767, int(out[i] + pad)))

    for scene, dur in zip(story_data, durations):
        if scene["event"] in {"pop","whoosh"}:
            add_tone(scene_start, 0.10, 620, 0.055)
        elif scene["event"] == "hit":
            add_tone(scene_start, 0.11, 105, 0.085)
        elif scene["event"] == "impact":
            add_tone(scene_start, 0.15, 72, 0.13)
        elif scene["event"] == "celebrate":
            add_tone(scene_start, 0.12, 760, 0.07)
            add_tone(scene_start+0.10, 0.12, 940, 0.055)
        scene_start += dur

    with wave.open(str(MIX_WAV),"wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(out.tobytes())


def mux():
    d = duration(VIDEO_ONLY)
    run([
        "ffmpeg","-y","-hide_banner","-loglevel","error",
        "-i",str(VIDEO_ONLY),"-i",str(MIX_WAV),
        "-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac","-b:a","160k",
        "-shortest","-movflags","+faststart",str(OUT)
    ])


async def build(topic):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise SystemExit("FFmpeg and ffprobe are required.")

    shutil.rmtree(FRAMES, ignore_errors=True)
    shutil.rmtree(VOICE_DIR, ignore_errors=True)
    shutil.rmtree(AUDIO_DIR, ignore_errors=True)
    BUILD.mkdir(parents=True, exist_ok=True)

    story_data = story(topic)
    durations, voice_map = await make_voice(story_data)
    total = sum(durations)

    if not MIN_DURATION <= total <= MAX_DURATION:
        raise RuntimeError(f"Narration length {total:.2f}s outside {MIN_DURATION}-{MAX_DURATION}s")

    timeline, offset = [], 0.0
    for scene, dur in zip(story_data, durations):
        timeline.append({
            "id": scene["id"],
            "start_seconds": round(offset, 3),
            "duration_seconds": round(dur, 3),
            "end_seconds": round(offset+dur, 3),
            "speaker": scene["voice"],
            "voice": voice_map[scene["voice"]],
            "caption": scene["caption"],
            "event": scene["event"],
        })
        offset += dur

    TIMELINE.write_text(json.dumps({
        "phase": 2,
        "render_style": "original expressive full-body cartoon",
        "topic": topic,
        "format": {"width": W, "height": H, "fps": FPS},
        "timeline": timeline,
        "voice_map": voice_map,
        "quality_target": "polished original 2D cartoon entertainment Short",
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    write_frames(story_data, durations)
    render_video()
    mix_audio(story_data, durations)
    mux()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", required=True)
    topic = " ".join(ap.parse_args().topic.split()).strip()
    if not topic:
        raise SystemExit("Topic cannot be empty.")
    asyncio.run(build(topic))
    if not OUT.exists() or OUT.stat().st_size < 30000:
        raise RuntimeError("Final video was not created correctly.")
    print(f"Created: {OUT}")
    print(f"Timeline: {TIMELINE}")


if __name__ == "__main__":
    main()
