#!/usr/bin/env python3
"""Generate a 45-second animated Hindi/Hinglish stickman comedy Short."""

import argparse
import asyncio
import json
import math
import shutil
import subprocess
import wave
from pathlib import Path

import edge_tts
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 720, 1280, 15
SCENE_SECONDS = 7.5
SCENES = 6
FRAMES_PER_SCENE = int(SCENE_SECONDS * FPS)

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
FRAMES = BUILD / "frames"
VOICE_DIR = BUILD / "voice"
VIDEO = BUILD / "video-only.mp4"
VOICE = BUILD / "voice.wav"
OUT = BUILD / "stickman-video.mp4"

FONT_BOLD = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
]
FONT_REGULAR = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
]


def pick_font(paths, size):
    for path in paths:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


TITLE = pick_font(FONT_BOLD, 48)
CAPTION = pick_font(FONT_BOLD, 38)
SMALL = pick_font(FONT_REGULAR, 24)
TINY = pick_font(FONT_REGULAR, 20)


def center_text(draw, text, y, font, max_width=630, fill=(20, 20, 20)):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        trial = word if not current else current + " " + word
        if draw.textbbox((0, 0), trial, font=font)[2] <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    line_h = font.getbbox("Ag")[3] - font.getbbox("Ag")[1] + 6
    for i, line in enumerate(lines):
        box = draw.textbbox((0, 0), line, font=font)
        x = (W - (box[2] - box[0])) // 2
        draw.text((x, y + i * line_h), line, font=font, fill=fill)


def draw_phone(draw, x, y, scale=1.0, tilt=0):
    sw, sh = int(115 * scale), int(205 * scale)
    draw.rounded_rectangle(
        (x, y, x + sw, y + sh),
        radius=int(18 * scale),
        fill=(35, 35, 35),
        outline=(10, 10, 10),
        width=max(2, int(4 * scale)),
    )
    draw.rounded_rectangle(
        (x + int(9 * scale), y + int(14 * scale), x + sw - int(9 * scale), y + sh - int(14 * scale)),
        radius=int(10 * scale),
        fill=(220, 240, 255),
    )
    draw.text((x + int(16 * scale), y + int(24 * scale)), "1%", font=TINY, fill=(200, 30, 30))


def draw_exclamation(draw, x, y, size=90):
    draw.text((x, y), "!!!", font=pick_font(FONT_BOLD, size), fill=(220, 40, 40))


def draw_stickman(draw, cx, ground, t, mood="normal", scale=1.0, bounce=0):
    cx += int(math.sin(t * math.tau) * 14)
    ground += int(math.sin(t * math.tau * 2) * bounce)

    head_r = int(44 * scale)
    shoulder = ground - int(285 * scale)
    hip = ground - int(135 * scale)
    lw = max(3, int(7 * scale))

    draw.ellipse(
        (cx - head_r, shoulder - 105 * scale, cx + head_r, shoulder - 105 * scale + 2 * head_r),
        outline=(25, 25, 25),
        width=lw,
    )
    draw.line((cx, shoulder - 15 * scale, cx, hip), fill=(25, 25, 25), width=lw)

    if mood == "panic":
        arms = [(-125, -55), (125, -70)]
        legs = [(-100, 10), (105, 15)]
    elif mood == "run":
        swing = math.sin(t * math.tau * 2) * 55
        arms = [(-85, 50 + swing), (85, 35 - swing)]
        legs = [(-90 - swing * 0.2, 0), (90 + swing * 0.2, 15)]
    elif mood == "celebrate":
        arms = [(-115, -105), (115, -110)]
        legs = [(-75, 10), (75, 5)]
    elif mood == "sad":
        arms = [(-80, 55), (80, 55)]
        legs = [(-62, 0), (62, 0)]
    else:
        arms = [(-95, 35), (95, 35)]
        legs = [(-70, 0), (70, 0)]

    for dx, dy in arms:
        draw.line((cx, shoulder, cx + int(dx * scale), shoulder + int(dy * scale)), fill=(25, 25, 25), width=lw)
    for dx, dy in legs:
        draw.line((cx, hip, cx + int(dx * scale), ground + int(10 * scale)), fill=(25, 25, 25), width=lw)

    eye_y = int(shoulder - 92 * scale)
    eye_dx = int(18 * scale)
    if mood == "sad":
        draw.arc((cx - 24, eye_y + 16, cx + 24, eye_y + 52), 200, 340, fill=(25, 25, 25), width=max(2, lw // 2))
    elif mood in ("panic", "surprise"):
        draw.ellipse((cx - eye_dx - 6, eye_y - 6, cx - eye_dx + 6, eye_y + 6), fill=(25, 25, 25))
        draw.ellipse((cx + eye_dx - 6, eye_y - 6, cx + eye_dx + 6, eye_y + 6), fill=(25, 25, 25))
    else:
        draw.ellipse((cx - eye_dx - 4, eye_y - 4, cx - eye_dx + 4, eye_y + 4), fill=(25, 25, 25))
        draw.ellipse((cx + eye_dx - 4, eye_y - 4, cx + eye_dx + 4, eye_y + 4), fill=(25, 25, 25))


def scene_story(topic):
    return [
        {
            "title": topic,
            "caption": "Bas 10 second ke liye...",
            "mood": "surprise",
            "dialogue": f"{topic} dekh ke laga, bas das second ka kaam hai. Itna bhi kya ho jayega?",
            "phone": True,
        },
        {
            "title": "PLAN",
            "caption": "FULL CONTROL 😎",
            "mood": "normal",
            "dialogue": "Maine confidence se bola: tension hi kya hai? Sab mere control mein hai.",
        },
        {
            "title": "PROBLEM",
            "caption": "Oh... ye nahi socha tha.",
            "mood": "panic",
            "dialogue": "Phir ek chhoti si problem aayi. Aur us problem ne poore plan ko welcome bol diya.",
        },
        {
            "title": "CHAOS",
            "caption": "PLAN = GONE 😂",
            "mood": "run",
            "dialogue": "Ab main idhar udhar bhaag raha tha, jaise solution nahi, Olympics ka trial chal raha ho.",
        },
        {
            "title": "PLOT TWIST",
            "caption": "ASLI PROBLEM = MAIN",
            "mood": "sad",
            "dialogue": "Tab samajh aaya: problem situation nahi thi. Meri overconfidence hi villain thi.",
        },
        {
            "title": "PUNCHLINE",
            "caption": "BACKUP PLAN RAKHO! 😂",
            "mood": "celebrate",
            "dialogue": "Agli baar hero banne se pehle backup plan. Warna stickman bhi phas jayega, boss.",
        },
    ]


def render_frame(scene_idx, scene, local):
    img = Image.new("RGB", (W, H), (247, 249, 252))
    draw = ImageDraw.Draw(img)

    # Scene-specific tint without heavy visual clutter.
    tints = [
        (247, 249, 252),
        (255, 249, 235),
        (240, 249, 255),
        (252, 242, 247),
        (245, 245, 255),
        (242, 250, 243),
    ]
    img.paste(tints[scene_idx - 1], (0, 0, W, H))
    draw = ImageDraw.Draw(img)

    # Kinetic top bar.
    draw.rectangle((0, 0, W, 105), fill=(30, 30, 30))
    draw.text((28, 30), f"STICKMAN STORY   {scene_idx}/6", font=SMALL, fill="white")

    t = local / max(1, FRAMES_PER_SCENE - 1)

    # Simple simulated camera movement.
    zoom = 1.0 + 0.07 * math.sin(t * math.pi)
    cx = 360 + int(35 * math.sin(t * math.tau))
    ground = 890

    center_text(draw, scene["title"], 145, TITLE, 620)
    draw_stickman(draw, cx, ground, t, scene["mood"], zoom, bounce=8)

    if scene.get("phone"):
        draw_phone(draw, cx + 80, 610, 0.85)
        draw_exclamation(draw, 505, 565, 60)

    if scene_idx == 3:
        draw_exclamation(draw, 120, 610, 80)
    if scene_idx == 4:
        for n in range(5):
            yy = 650 + n * 42
            draw.line((70, yy, 230, yy), fill=(130, 130, 130), width=5)
    if scene_idx == 5:
        draw.text((300, 600), "…", font=pick_font(FONT_BOLD, 90), fill=(80, 80, 80))

    # Caption card.
    card = (55, 995, 665, 1140)
    draw.rounded_rectangle(card, radius=28, fill=(255, 255, 255), outline=(45, 45, 45), width=4)
    center_text(draw, scene["caption"], 1033, CAPTION, 560)

    # Progress bar.
    progress = ((scene_idx - 1) + t) / SCENES
    draw.rounded_rectangle((55, 1175, 665, 1192), radius=8, fill=(205, 205, 205))
    draw.rounded_rectangle((55, 1175, 55 + int(610 * progress), 1192), radius=8, fill=(25, 25, 25))
    draw.text((30, 1210), "Original stickman entertainment prototype", font=TINY, fill=(100, 100, 100))
    return img


async def choose_voice():
    voices = await edge_tts.list_voices()
    candidates = [
        "hi-IN-SwaraNeural",
        "hi-IN-KunalNeural",
        "hi-IN-MadhurNeural",
        "hi-IN-AaravNeural",
        "hi-IN-AnanyaNeural",
    ]
    available = {v["ShortName"] for v in voices}
    for name in candidates:
        if name in available:
            return name
    hindi = [v["ShortName"] for v in voices if v.get("Locale") == "hi-IN"]
    if hindi:
        return hindi[0]
    raise RuntimeError("No hi-IN Edge TTS voice is currently available.")


async def make_voice(scene_list):
    VOICE_DIR.mkdir(parents=True, exist_ok=True)
    voice = await choose_voice()

    for i, scene in enumerate(scene_list, start=1):
        communicate = edge_tts.Communicate(
            scene["dialogue"],
            voice=voice,
            rate="+10%",
            pitch="+2Hz",
            volume="+0%",
        )
        await communicate.save(str(VOICE_DIR / f"scene-{i}.mp3"))

    wav_parts = []
    for i in range(1, len(scene_list) + 1):
        src = VOICE_DIR / f"scene-{i}.mp3"
        dst = VOICE_DIR / f"scene-{i}.wav"
        subprocess.run(
            [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(src),
                "-af", f"apad,atrim=duration={SCENE_SECONDS}",
                "-ar", "48000", "-ac", "1", str(dst),
            ],
            check=True,
        )
        wav_parts.append(dst)

    with wave.open(str(VOICE), "wb") as out:
        with wave.open(str(wav_parts[0]), "rb") as first:
            out.setnchannels(first.getnchannels())
            out.setsampwidth(first.getsampwidth())
            out.setframerate(first.getframerate())
        for part in wav_parts:
            with wave.open(str(part), "rb") as wf:
                out.writeframes(wf.readframes(wf.getnframes()))


def render_video():
    FRAMES.mkdir(parents=True, exist_ok=True)
    story = scene_story(TOPIC)
    (BUILD / "story.json").write_text(json.dumps(story, ensure_ascii=False, indent=2), encoding="utf-8")

    for frame_no in range(FRAMES_PER_SCENE * SCENES):
        scene_idx = frame_no // FRAMES_PER_SCENE + 1
        local = frame_no % FRAMES_PER_SCENE
        render_frame(scene_idx, story[scene_idx - 1], local).save(
            FRAMES / f"frame-{frame_no:05d}.png", optimize=True
        )

    subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-framerate", str(FPS),
            "-i", str(FRAMES / "frame-%05d.png"),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(VIDEO),
        ],
        check=True,
    )
    return story


def mux():
    subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(VIDEO),
            "-i", str(VOICE),
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "128k",
            "-shortest",
            "-movflags", "+faststart",
            str(OUT),
        ],
        check=True,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True)
    args = parser.parse_args()

    global TOPIC
    TOPIC = args.topic.strip()[:90]
    if not TOPIC:
        raise SystemExit("Topic cannot be empty.")
    if shutil.which("ffmpeg") is None:
        raise SystemExit("FFmpeg is required.")

    BUILD.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(FRAMES, ignore_errors=True)
    shutil.rmtree(VOICE_DIR, ignore_errors=True)

    story = render_video()
    asyncio.run(make_voice(story))
    mux()

    if not OUT.exists() or OUT.stat().st_size < 20000:
        raise RuntimeError("Final video was not created correctly.")

    print(f"Created: {OUT}")
    print(f"Voice scenes: {len(story)}")
    print("TTS backend: Edge online TTS, Hindi voice selected dynamically")


if __name__ == "__main__":
    main()
