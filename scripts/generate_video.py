#!/usr/bin/env python3
"""Original 2D Hindi/Hinglish entertainment Shorts renderer - Phase 2 polished pass."""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import wave
from array import array
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 720, 1280, 18
MIN_DURATION, MAX_DURATION = 35.0, 58.0

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
FRAMES = BUILD / "frames"
VOICE_DIR = BUILD / "voice"
AUDIO_DIR = BUILD / "audio"
VIDEO_ONLY = BUILD / "video-only.mp4"
VOICE_WAV = AUDIO_DIR / "voice.wav"
MIX_WAV = AUDIO_DIR / "mix.wav"
OUT = BUILD / "stickman-video.mp4"
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


def character(draw, x, ground, t, role, mood, speaking, frame, s=1.0):
    body = C["hero"] if role == "hero" else C["mom"]
    shirt = C["hero_light"] if role == "hero" else C["mom_light"]
    ph = t * math.tau

    if mood == "run":
        swing = math.sin(ph*2.2) * 70
        arms = [(-92, 35+swing), (92, 42-swing)]
        legs = [(-78-swing*.35, 5), (78+swing*.35, 7)]
    elif mood == "panic":
        arms = [(-114, -64), (114, -80)]
        legs = [(-88, 4), (88, 8)]
    elif mood == "celebrate":
        arms = [(-112, -106), (112, -106)]
        legs = [(-76, 5), (76, 5)]
    elif mood == "scold":
        arms = [(-85, 2), (112, -48)]
        legs = [(-70, 3), (70, 3)]
    elif mood == "phone":
        arms = [(-82, 28), (55, -10)]
        legs = [(-70, 3), (70, 3)]
    elif mood == "sad":
        arms = [(-78, 46), (78, 46)]
        legs = [(-62, 3), (62, 3)]
    else:
        sway = math.sin(ph)*10
        arms = [(-87, 34+sway), (87, 34-sway)]
        legs = [(-68, 3), (68, 3)]

    torso = ground - int(285*s)
    hip = ground - int(125*s)
    head = torso - int(102*s)
    hr = int(44*s)
    lw = max(3, int(7*s))

    draw.ellipse((x-int(58*s), ground+3, x+int(58*s), ground+22), fill=(202, 202, 204))
    for dx, dy in legs:
        draw.line((x, hip, x+int(dx*s), ground+int(dy*s)), fill=C["ink"], width=lw)
        sx, sy = x+int(dx*s), ground+int(dy*s)
        draw.line((sx-2, sy, sx+18, sy), fill=C["ink"], width=max(2, lw-1))

    draw.rounded_rectangle((x-int(38*s), torso, x+int(38*s), hip), 22, fill=shirt, outline=body, width=max(2, int(4*s)))
    for dx, dy in arms:
        draw.line(
            (x, torso+int(48*s), x+int(dx*s), torso+int(48*s)+int(dy*s)),
            fill=C["ink"], width=lw,
        )

    draw.ellipse((x-hr, head-hr, x+hr, head+hr), fill=C["skin"], outline=C["ink"], width=lw)
    draw.arc((x-hr, head-int(hr*.72)-10, x+hr, head-int(hr*.72)+50), 190, 350, fill=body, width=max(3, lw))
    face(draw, x, head, mood, speaking, frame, s)


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


def elevenlabs_json_request(url, method="GET", payload=None, api_key=""):
    headers = {"xi-api-key": api_key, "Accept": "application/json"}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"ElevenLabs API error {exc.code}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"ElevenLabs network error: {exc.reason}") from exc


def elevenlabs_audio(text, voice_id, model_id, output_path, api_key):
    params = urllib.parse.urlencode({"output_format": "mp3_44100_128"})
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?{params}"
    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": 0.45,
            "similarity_boost": 0.82,
            "style": 0.28,
            "speed": 1.02,
            "use_speaker_boost": True,
        },
    }
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            output_path.write_bytes(response.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"ElevenLabs TTS error {exc.code}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"ElevenLabs TTS network error: {exc.reason}") from exc


def choose_voice(api_key, gender, preferred_names, explicit_id="", used_ids=None):
    used_ids = used_ids or set()
    explicit_id = explicit_id.strip()
    if explicit_id:
        return explicit_id

    base_params = {
        "language": "hi",
        "accent": "indian",
        "gender": gender.lower(),
        "page_size": "100",
    }

    # Prefer a stable, named Hindi/Indian voice when the account exposes it.
    for name in preferred_names:
        params = dict(base_params)
        params["search"] = name
        url = "https://api.elevenlabs.io/v2/voices?" + urllib.parse.urlencode(params)
        data = elevenlabs_json_request(url, api_key=api_key)
        for voice in data.get("voices", []):
            vid = str(voice.get("voice_id", "")).strip()
            vname = str(voice.get("name", "")).strip()
            if vid and vid not in used_ids and vname:
                return vid

    # Otherwise use the first Hindi/Indian voice available to this API key.
    url = "https://api.elevenlabs.io/v2/voices?" + urllib.parse.urlencode(base_params)
    data = elevenlabs_json_request(url, api_key=api_key)
    candidates = []
    for voice in data.get("voices", []):
        vid = str(voice.get("voice_id", "")).strip()
        if not vid or vid in used_ids:
            continue
        labels = voice.get("labels") or {}
        language = str(labels.get("language", "")).lower()
        accent = str(labels.get("accent", "")).lower()
        if language in {"hi", "hindi"} or accent in {"indian", "desi"}:
            candidates.append(vid)

    if candidates:
        return candidates[0]

    raise RuntimeError(
        f"No usable Hindi/Indian {gender} ElevenLabs voice found. "
        "Set the matching ELEVENLABS_*_VOICE_ID GitHub secret/environment value."
    )


def make_voice(story_data):
    VOICE_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY is required for the final render.")

    model_id = os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2").strip()

    used_ids = set()
    voice_map = {
        "narrator": choose_voice(
            api_key, "female",
            ["Monika Sogam", "Devi", "Niraj"],
            os.getenv("ELEVENLABS_NARRATOR_VOICE_ID", ""),
            used_ids,
        ),
        "hero": choose_voice(
            api_key, "male",
            ["Bunty", "Raju", "Vikram", "Krishna Gupta"],
            os.getenv("ELEVENLABS_HERO_VOICE_ID", ""),
            used_ids,
        ),
        "mom": choose_voice(
            api_key, "female",
            ["Devi", "Monika Sogam"],
            os.getenv("ELEVENLABS_MOM_VOICE_ID", ""),
            used_ids,
        ),
    }
    used_ids.update(voice_map.values())

    durations, paths = [], []
    for i, scene in enumerate(story_data, 1):
        mp3 = VOICE_DIR / f"scene-{i}.mp3"
        wav = VOICE_DIR / f"scene-{i}.wav"
        selected = voice_map[scene["voice"]]
        elevenlabs_audio(scene["line"], selected, model_id, mp3, api_key)
        run([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(mp3),
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=9",
            "-ar", "48000", "-ac", "1", str(wav)
        ])
        durations.append(duration(wav))
        paths.append(wav)

    lst = AUDIO_DIR / "concat.txt"
    lst.write_text(
        "".join(f"file '{p.as_posix()}'\n" for p in paths),
        encoding="utf-8",
    )
    run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(lst),
        "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(VOICE_WAV)
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


def build(topic):
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
        "topic": topic,
        "format": {"width": W, "height": H, "fps": FPS},
        "timeline": timeline,
        "voice_map": voice_map,
        "quality_target": "polished original 2D entertainment Short",
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
    build(topic)
    if not OUT.exists() or OUT.stat().st_size < 30000:
        raise RuntimeError("Final video was not created correctly.")
    print(f"Created: {OUT}")
    print(f"Timeline: {TIMELINE}")


if __name__ == "__main__":
    main()
