#!/usr/bin/env python3
"""Render a polished original 2D stickman entertainment Short.

Phase 2 goals:
- scene-based acting with two characters
- expressive faces and body poses
- camera movement, punch-ins and impact beats
- neural Hindi voices per character
- caption timing derived from actual voice durations
- lightweight procedural SFX/music bed
- deterministic 9:16 MP4 output suitable for Shorts
"""

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

W, H, FPS = 720, 1280, 18
MIN_DURATION = 35
MAX_DURATION = 58

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
FRAMES = BUILD / "frames"
VOICE_DIR = BUILD / "voice"
AUDIO_DIR = BUILD / "audio"
VIDEO_ONLY = BUILD / "video-only.mp4"
VOICE_WAV = AUDIO_DIR / "voice-full.wav"
MIX_WAV = AUDIO_DIR / "final-mix.wav"
OUT = BUILD / "stickman-video.mp4"
STORY_JSON = BUILD / "story.json"

FONT_BOLD = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
]
FONT_REGULAR = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
]

PALETTE = {
    "ink": (24, 24, 28),
    "muted": (95, 96, 104),
    "paper": (248, 249, 252),
    "hero": (40, 110, 220),
    "hero_light": (222, 235, 255),
    "mom": (220, 82, 102),
    "mom_light": (255, 228, 234),
    "accent": (245, 173, 45),
    "danger": (223, 66, 66),
    "green": (48, 158, 99),
}


def font(paths: list[str], size: int):
    for path in paths:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


TITLE = font(FONT_BOLD, 52)
CAPTION = font(FONT_BOLD, 38)
SMALL = font(FONT_REGULAR, 24)
TINY = font(FONT_REGULAR, 20)


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def probe_duration(path: Path) -> float:
    raw = subprocess.check_output(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        text=True,
    )
    return float(raw.strip())


def text_width(draw: ImageDraw.ImageDraw, text: str, fnt) -> int:
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0]


def wrap(draw: ImageDraw.ImageDraw, text: str, fnt, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = word if not current else current + " " + word
        if text_width(draw, trial, fnt) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_centered(draw, text: str, y: int, fnt, max_width: int, fill=PALETTE["ink"]) -> None:
    lines = wrap(draw, text, fnt, max_width)
    line_h = fnt.getbbox("Ag")[3] - fnt.getbbox("Ag")[1] + 8
    for i, line in enumerate(lines):
        x = (W - text_width(draw, line, fnt)) // 2
        draw.text((x, y + i * line_h), line, font=fnt, fill=fill)


def draw_room(draw, style: str) -> None:
    bg = {
        "room": (239, 241, 247),
        "hall": (246, 240, 232),
        "street": (229, 239, 247),
        "classroom": (239, 247, 239),
    }.get(style, PALETTE["paper"])
    draw.rectangle((0, 0, W, H), fill=bg)
    draw.rectangle((0, 920, W, H), fill=(226, 220, 211))

    if style == "room":
        draw.rectangle((70, 185, 650, 545), fill=(215, 233, 246), outline=(45, 62, 77), width=5)
        draw.line((360, 185, 360, 545), fill=(45, 62, 77), width=4)
        draw.line((70, 365, 650, 365), fill=(45, 62, 77), width=4)
        draw.rectangle((90, 610, 630, 885), fill=(205, 180, 165), outline=(79, 65, 58), width=5)
        draw.rounded_rectangle((110, 675, 610, 865), radius=45, fill=(173, 110, 107), outline=(79, 65, 58), width=5)
        draw.rounded_rectangle((135, 715, 320, 840), radius=28, fill=(222, 174, 168))
        draw.rounded_rectangle((400, 715, 585, 840), radius=28, fill=(222, 174, 168))
    elif style == "hall":
        draw.rectangle((545, 180, 670, 800), fill=(191, 157, 119), outline=(93, 73, 55), width=5)
        draw.ellipse((578, 470, 598, 490), fill=(93, 73, 55))
        draw.rectangle((60, 690, 250, 870), fill=(198, 196, 194), outline=(93, 93, 93), width=4)
        draw.rectangle((470, 690, 660, 870), fill=(198, 196, 194), outline=(93, 93, 93), width=4)
    elif style == "street":
        draw.rectangle((0, 760, W, 920), fill=(105, 111, 121))
        for x in range(-80, W + 100, 170):
            draw.rounded_rectangle((x, 830, x + 95, 850), radius=8, fill=(248, 247, 218))
        draw.rectangle((85, 225, 260, 540), fill=(208, 195, 180), outline=(86, 83, 78), width=5)
        draw.rectangle((105, 250, 235, 420), fill=(190, 219, 232))
        draw.polygon((470, 530, 600, 530, 665, 760, 405, 760), fill=(72, 119, 76))
        draw.rectangle((515, 430, 555, 605), fill=(99, 62, 32))
        draw.ellipse((483, 360, 590, 470), fill=(61, 134, 71))
    else:
        draw.rectangle((70, 180, 650, 560), fill=(224, 238, 245), outline=(82, 98, 110), width=5)
        draw.line((70, 365, 650, 365), fill=(82, 98, 110), width=4)
        draw.rectangle((85, 650, 635, 885), fill=(180, 134, 89), outline=(83, 64, 45), width=5)
        draw.rectangle((120, 500, 600, 560), fill=(76, 125, 74))
    draw.rectangle((0, 910, W, 930), fill=(55, 57, 62))


def draw_phone(draw, x: int, y: int, scale: float = 1.0, alert: bool = False) -> None:
    w, h = int(118 * scale), int(208 * scale)
    draw.rounded_rectangle((x, y, x + w, y + h), radius=int(19 * scale), fill=(28, 30, 34), outline=(10, 10, 10), width=4)
    screen = (x + int(10 * scale), y + int(16 * scale), x + w - int(10 * scale), y + h - int(16 * scale))
    draw.rounded_rectangle(screen, radius=int(11 * scale), fill=(226, 242, 252))
    draw.rectangle((screen[0] + 14, screen[1] + 34, screen[2] - 14, screen[1] + 43), fill=(94, 136, 214))
    draw.rectangle((screen[0] + 14, screen[1] + 58, screen[2] - 32, screen[1] + 66), fill=(159, 172, 188))
    draw.rectangle((screen[0] + 14, screen[1] + 82, screen[2] - 44, screen[1] + 90), fill=(159, 172, 188))
    draw.text((screen[0] + 16, screen[1] + 12), "98%", font=TINY, fill=(215, 45, 55) if alert else (60, 70, 80))


def draw_balloon(draw, x, y, text: str, fill, max_width=330) -> None:
    lines = wrap(draw, text, SMALL, max_width - 30)
    line_h = 30
    h = max(74, 28 + len(lines) * line_h)
    w = min(max_width, max(190, max(text_width(draw, line, SMALL) for line in lines) + 38))
    left = x - w // 2
    top = y - h
    draw.rounded_rectangle((left, top, left + w, top + h), radius=24, fill="white", outline=fill, width=4)
    draw.polygon((x - 16, top + h, x + 20, top + h, x + 4, top + h + 24), fill="white", outline=fill)
    for i, line in enumerate(lines):
        draw.text((left + 18, top + 14 + i * line_h), line, font=SMALL, fill=PALETTE["ink"])


def draw_face(draw, cx, cy, mood: str, scale: float) -> None:
    eye_y = int(cy - 12 * scale)
    eye_dx = int(19 * scale)
    dot = max(2, int(4 * scale))

    if mood in {"shock", "panic"}:
        draw.ellipse((cx - eye_dx - dot, eye_y - dot, cx - eye_dx + dot + 4, eye_y + dot + 4), fill=PALETTE["ink"])
        draw.ellipse((cx + eye_dx - dot, eye_y - dot, cx + eye_dx + dot + 4, eye_y + dot + 4), fill=PALETTE["ink"])
    elif mood == "sleepy":
        draw.arc((cx - eye_dx - 8, eye_y - 4, cx - eye_dx + 8, eye_y + 8), 20, 160, fill=PALETTE["ink"], width=max(2, dot))
        draw.arc((cx + eye_dx - 8, eye_y - 4, cx + eye_dx + 8, eye_y + 8), 20, 160, fill=PALETTE["ink"], width=max(2, dot))
    else:
        draw.ellipse((cx - eye_dx - dot, eye_y - dot, cx - eye_dx + dot, eye_y + dot), fill=PALETTE["ink"])
        draw.ellipse((cx + eye_dx - dot, eye_y - dot, cx + eye_dx + dot, eye_y + dot), fill=PALETTE["ink"])

    if mood in {"happy", "proud", "laugh"}:
        draw.arc((cx - 24, eye_y + 10, cx + 24, eye_y + 46), 20, 160, fill=PALETTE["ink"], width=max(2, dot))
    elif mood in {"sad", "tired"}:
        draw.arc((cx - 23, eye_y + 24, cx + 23, eye_y + 58), 195, 345, fill=PALETTE["ink"], width=max(2, dot))
    elif mood in {"shock", "panic"}:
        draw.ellipse((cx - 9, eye_y + 30, cx + 9, eye_y + 48), outline=PALETTE["ink"], width=max(2, dot))
    else:
        draw.line((cx - 13, eye_y + 34, cx + 13, eye_y + 34), fill=PALETTE["ink"], width=max(2, dot))


def draw_character(draw, x: int, ground: int, t: float, role: str, mood: str, scale: float = 1.0) -> None:
    body = PALETTE["hero"] if role == "hero" else PALETTE["mom"]
    light = PALETTE["hero_light"] if role == "hero" else PALETTE["mom_light"]
    phase = t * math.tau

    if mood == "run":
        stride = math.sin(phase * 2.2) * 68
        arms = [(-92, 35 + stride), (92, 40 - stride)]
        legs = [(-78 - stride * 0.35, 6), (78 + stride * 0.35, 8)]
    elif mood == "panic":
        arms = [(-112, -64), (112, -78)]
        legs = [(-88, 4), (88, 8)]
    elif mood == "celebrate":
        arms = [(-112, -105), (112, -105)]
        legs = [(-76, 5), (76, 5)]
    elif mood == "scold":
        arms = [(-82, -4), (112, -44)]
        legs = [(-70, 3), (70, 3)]
    elif mood == "phone":
        arms = [(-84, 28), (54, -6)]
        legs = [(-70, 3), (70, 3)]
    elif mood == "sad":
        arms = [(-78, 44), (78, 44)]
        legs = [(-62, 3), (62, 3)]
    else:
        sway = math.sin(phase) * 10
        arms = [(-86, 35 + sway), (86, 35 - sway)]
        legs = [(-68, 3), (68, 3)]

    torso_top = ground - int(285 * scale)
    hip = ground - int(125 * scale)
    head_y = torso_top - int(102 * scale)
    head_r = int(44 * scale)
    lw = max(3, int(7 * scale))

    draw.ellipse((x - int(55 * scale), ground + 4, x + int(55 * scale), ground + int(24 * scale)), fill=(205, 204, 206))

    for dx, dy in legs:
        draw.line((x, hip, x + int(dx * scale), ground + int(dy * scale)), fill=PALETTE["ink"], width=lw)
    for dx, dy in legs:
        sx = x + int(dx * scale)
        sy = ground + int(dy * scale)
        draw.line((sx - 2, sy, sx + 18, sy), fill=PALETTE["ink"], width=max(2, lw - 1))

    draw.rounded_rectangle(
        (x - int(38 * scale), torso_top, x + int(38 * scale), hip),
        radius=int(22 * scale),
        fill=light,
        outline=body,
        width=max(2, int(4 * scale)),
    )
    draw.line((x, torso_top + 8, x, hip - 12), fill=body, width=max(2, int(3 * scale)))

    for dx, dy in arms:
        draw.line((x, torso_top + int(48 * scale), x + int(dx * scale), torso_top + int(48 * scale) + int(dy * scale)), fill=PALETTE["ink"], width=lw)

    draw.ellipse(
        (x - head_r, head_y - head_r, x + head_r, head_y + head_r),
        fill=(255, 239, 215),
        outline=PALETTE["ink"],
        width=lw,
    )
    hair_y = head_y - int(head_r * 0.72)
    draw.arc((x - head_r, hair_y - 10, x + head_r, hair_y + 50), 190, 350, fill=body, width=max(3, lw))
    draw_face(draw, x, head_y, mood, scale)

    if role == "mom":
        draw.arc((x - int(50 * scale), torso_top - 18, x + int(50 * scale), hip + 34), 205, 330, fill=body, width=max(3, lw))


def story_for(topic: str) -> list[dict]:
    topic = " ".join(topic.split()).strip()
    return [
        {
            "id": "hook",
            "background": "room",
            "shot": "close",
            "role": "narrator",
            "voice": "narrator",
            "mood": "happy",
            "caption": "BAS DO MINUTE…",
            "line": f"{topic} ka sabse dangerous part pata hai? Jab dimaag bolta hai — bas do minute aur.",
            "event": "pop",
        },
        {
            "id": "confidence",
            "background": "room",
            "shot": "medium",
            "role": "hero",
            "voice": "hero",
            "mood": "proud",
            "caption": "FULL CONFIDENCE",
            "line": "Maine bhi wahi socha. Do minute. Full control. Kya hi galat ho sakta hai?",
            "event": "pop",
        },
        {
            "id": "interrupt",
            "background": "room",
            "shot": "wide",
            "role": "mom",
            "voice": "mom",
            "mood": "scold",
            "caption": "KYA KAR RAHE HO?",
            "line": "Do minute? Beta, ye phone tumhare haath mein kab se hai?",
            "event": "hit",
        },
        {
            "id": "excuse",
            "background": "room",
            "shot": "medium",
            "role": "hero",
            "voice": "hero",
            "mood": "shock",
            "caption": "MAIN? PHONE? NAHI TOH…",
            "line": "Maa, actually main phone nahi chala raha tha. Main… research kar raha tha.",
            "event": "whoosh",
        },
        {
            "id": "proof",
            "background": "room",
            "shot": "close",
            "role": "mom",
            "voice": "mom",
            "mood": "laugh",
            "caption": "ACHHA?",
            "line": "Research? Toh ye teen ghante ka screen time kis subject ka tha?",
            "event": "hit",
        },
        {
            "id": "panic",
            "background": "hall",
            "shot": "shake",
            "role": "hero",
            "voice": "hero",
            "mood": "panic",
            "caption": "THREE HOURS?!",
            "line": "Teen ghante?! Impossible. Phone bhi jhoot bolta hai kya?",
            "event": "impact",
        },
        {
            "id": "realisation",
            "background": "hall",
            "shot": "close",
            "role": "narrator",
            "voice": "narrator",
            "mood": "sad",
            "caption": "ASLI PROBLEM…",
            "line": "Aur us moment mujhe samajh aaya: problem phone nahi tha. Overconfidence tha.",
            "event": "whoosh",
        },
        {
            "id": "punchline",
            "background": "street",
            "shot": "wide",
            "role": "hero",
            "voice": "hero",
            "mood": "celebrate",
            "caption": "BACKUP PLAN RAKHO",
            "line": "Agli baar sirf do minute bolne se pehle timer lagaunga. Varna main nahi, mera phone mera boss ban jayega.",
            "event": "celebrate",
        },
    ]


async def choose_voice(locale: str, gender: str, preferred: list[str]) -> str:
    voices = await edge_tts.list_voices()
    available = {v["ShortName"]: v for v in voices}
    for name in preferred:
        if name in available:
            return name
    matching = [
        v["ShortName"]
        for v in voices
        if v.get("Locale") == locale and v.get("Gender") == gender
    ]
    if matching:
        return matching[0]
    hindi = [v["ShortName"] for v in voices if v.get("Locale") == locale]
    if hindi:
        return hindi[0]
    raise RuntimeError("No compatible Hindi voice is available from Edge TTS.")


async def generate_voice_tracks(story: list[dict]) -> tuple[list[float], dict[str, str]]:
    VOICE_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    narrator = await choose_voice(
        "hi-IN", "Male",
        ["hi-IN-AaravNeural", "hi-IN-KunalNeural", "hi-IN-MadhurNeural"],
    )
    hero = await choose_voice(
        "hi-IN", "Male",
        ["hi-IN-MadhurNeural", "hi-IN-KunalNeural", "hi-IN-AaravNeural"],
    )
    mom = await choose_voice(
        "hi-IN", "Female",
        ["hi-IN-SwaraNeural", "hi-IN-AnanyaNeural", "hi-IN-AartiNeural"],
    )
    voice_map = {"narrator": narrator, "hero": hero, "mom": mom}

    durations: list[float] = []
    normalized_wavs: list[Path] = []

    for index, scene in enumerate(story, 1):
        source = VOICE_DIR / f"scene-{index}.mp3"
        wav = VOICE_DIR / f"scene-{index}.wav"
        selected = voice_map[scene["voice"]]
        rate = "+4%" if selected == mom else "+7%"
        await edge_tts.Communicate(
            scene["line"],
            voice=selected,
            rate=rate,
            pitch="+1Hz",
            volume="+0%",
        ).save(str(source))

        run([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(source),
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
            "-ar", "48000", "-ac", "1",
            str(wav),
        ])
        durations.append(probe_duration(wav))
        normalized_wavs.append(wav)

    concat_list = AUDIO_DIR / "concat.txt"
    concat_list.write_text(
        "".join(f"file '{p.as_posix()}'\n" for p in normalized_wavs),
        encoding="utf-8",
    )
    run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le",
        str(VOICE_WAV),
    ])

    return durations, voice_map


def make_caption_chunks(text: str, duration: float) -> list[tuple[float, float, str]]:
    words = text.split()
    if not words:
        return []
    chunk_size = 4 if len(words) > 12 else 3
    chunks = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
    weights = [max(1, len(c.replace(" ", ""))) for c in chunks]
    total = sum(weights)
    t = 0.0
    output = []
    for weight, chunk in zip(weights, chunks):
        span = duration * weight / total
        output.append((t, min(duration, t + span), chunk))
        t += span
    return output


def draw_caption(draw, text: str, progress: float) -> None:
    scale = 1.0 + 0.05 * math.sin(progress * math.pi)
    fnt = font(FONT_BOLD, int(36 * scale))
    lines = wrap(draw, text, fnt, 580)
    line_h = 43
    h = 36 + line_h * len(lines)
    left, top, right, bottom = 48, 1000, 672, 1000 + h
    draw.rounded_rectangle((left, top, right, bottom), radius=30, fill="white", outline=PALETTE["ink"], width=4)
    for i, line in enumerate(lines):
        draw.text(((W - text_width(draw, line, fnt)) // 2, top + 16 + i * line_h), line, font=fnt, fill=PALETTE["ink"])


def render_character_shot(draw, scene: dict, local: float, duration: float) -> None:
    t = local / max(duration, 0.001)
    shot = scene["shot"]
    role = scene["role"] if scene["role"] in {"hero", "mom"} else "hero"

    if shot == "wide":
        hero_x = int(235 + 55 * math.sin(t * math.pi))
        other_x = int(490 - 35 * math.sin(t * math.pi))
        draw_character(draw, hero_x, 900, t, "hero", "phone" if scene["id"] == "interrupt" else "normal", 0.92)
        draw_character(draw, other_x, 900, t + 0.2, "mom", "scold" if scene["id"] in {"interrupt", "proof"} else "normal", 0.96)
        if scene["id"] == "interrupt":
            draw_phone(draw, 198, 630, 0.72, alert=True)
        return

    if shot == "shake":
        shake = int(13 * math.sin(t * math.tau * 6))
        draw_character(draw, 360 + shake, 900, t * 2.0, role, scene["mood"], 1.08)
        draw_exclamation(draw, 95, 555, 70)
        draw_exclamation(draw, 530, 610, 70)
        return

    x = 420 if role == "hero" else 300
    ground = 900
    scale = 1.04
    if shot == "close":
        x = 360
        ground = 950
        scale = 1.22
    drift = int(18 * math.sin(t * math.tau))
    draw_character(draw, x + drift, ground, t, role, scene["mood"], scale)

    if scene["id"] == "confidence":
        draw_balloon(draw, 420, 560, "FULL CONTROL", PALETTE["hero"], 270)
    elif scene["id"] == "proof":
        draw_balloon(draw, 340, 550, "ACHHA?", PALETTE["mom"], 260)
    elif scene["id"] == "excuse":
        draw_phone(draw, 355, 660, 0.72, alert=True)


def draw_exclamation(draw, x: int, y: int, size: int = 80) -> None:
    fnt = font(FONT_BOLD, size)
    draw.text((x, y), "!!!", font=fnt, fill=PALETTE["danger"])


def render_frame(scene: dict, local: float, duration: float, scene_number: int, total_scenes: int) -> Image.Image:
    img = Image.new("RGB", (W, H), PALETTE["paper"])
    draw = ImageDraw.Draw(img)
    draw_room(draw, scene["background"])

    t = local / max(duration, 0.001)

    title_alpha = max(0.0, 1.0 - t * 3.0)
    if title_alpha > 0.02:
        draw.rounded_rectangle((38, 46, 682, 132), radius=28, fill=(255, 255, 255), outline=PALETTE["ink"], width=3)
        draw_centered(draw, scene["caption"], 66, CAPTION, 590)

    render_character_shot(draw, scene, local, duration)

    if scene["id"] == "hook":
        draw_phone(draw, 472, 575, 0.82, alert=True)
        draw_exclamation(draw, 530, 520, 60)
    elif scene["id"] == "panic":
        for n in range(5):
            y = 620 + n * 44
            draw.line((62, y, 210, y), fill=(150, 150, 150), width=5)
    elif scene["id"] == "realisation":
        draw.text((320, 565), "...", font=font(FONT_BOLD, 96), fill=PALETTE["muted"])

    chunks = make_caption_chunks(scene["line"], duration)
    active = chunks[-1][2] if chunks else ""
    for start, end, text in chunks:
        if start <= local <= end:
            progress = (local - start) / max(end - start, 0.001)
            active = text
            draw_caption(draw, text, progress)
            break
    if not active:
        draw_caption(draw, active, 1.0)

    total_progress = (scene_number - 1 + t) / total_scenes
    draw.rounded_rectangle((46, 1180, 674, 1194), radius=8, fill=(206, 207, 212))
    draw.rounded_rectangle(
        (46, 1180, 46 + int(628 * total_progress), 1194),
        radius=8,
        fill=PALETTE["ink"],
    )
    draw.text((50, 1210), f"ORIGINAL SHORT  •  {scene_number}/{total_scenes}", font=TINY, fill=PALETTE["muted"])
    return img


def write_frames(story: list[dict], durations: list[float]) -> None:
    FRAMES.mkdir(parents=True, exist_ok=True)
    frame_index = 0
    total_scenes = len(story)
    for scene_number, (scene, duration) in enumerate(zip(story, durations), 1):
        count = max(1, math.ceil(duration * FPS))
        for local_index in range(count):
            local = local_index / FPS
            frame = render_frame(scene, local, duration, scene_number, total_scenes)
            frame.save(FRAMES / f"frame-{frame_index:06d}.png", optimize=True)
            frame_index += 1


def render_video() -> None:
    run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-framerate", str(FPS),
        "-i", str(FRAMES / "frame-%06d.png"),
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(VIDEO_ONLY),
    ])


def read_pcm(path: Path) -> tuple[array, int, int, int]:
    with wave.open(str(path), "rb") as wf:
        channels = wf.getnchannels()
        rate = wf.getframerate()
        width = wf.getsampwidth()
        if channels != 1 or width != 2 or rate != 48000:
            raise RuntimeError("Audio normalization produced unexpected WAV format")
        return array("h", wf.readframes(wf.getnframes())), rate, channels, width


def mix_audio(story: list[dict], durations: list[float]) -> None:
    samples, rate, channels, width = read_pcm(VOICE_WAV)
    out = array("h", samples)
    cursor_seconds = 0.0

    def add_tone(start: float, seconds: float, frequency: float, gain: float) -> None:
        begin = int(start * rate)
        length = min(int(seconds * rate), max(0, len(out) - begin))
        if length <= 0:
            return
        for i in range(length):
            env = 1.0 - (i / max(length, 1))
            value = math.sin(2 * math.pi * frequency * i / rate) * 32767 * gain * env
            out[begin + i] = max(-32768, min(32767, int(out[begin + i] + value)))

    for scene, dur in zip(story, durations):
        if scene["event"] in {"pop", "whoosh"}:
            add_tone(cursor_seconds, 0.10, 650, 0.08)
        elif scene["event"] == "hit":
            add_tone(cursor_seconds, 0.12, 115, 0.12)
        elif scene["event"] == "impact":
            add_tone(cursor_seconds, 0.16, 75, 0.16)
        elif scene["event"] == "celebrate":
            add_tone(cursor_seconds, 0.15, 760, 0.10)
            add_tone(cursor_seconds + 0.09, 0.14, 920, 0.08)
        cursor_seconds += dur

    with wave.open(str(MIX_WAV), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(width)
        wf.setframerate(rate)
        wf.writeframes(out.tobytes())


def mux() -> None:
    duration = probe_duration(VIDEO_ONLY)
    run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(VIDEO_ONLY),
        "-i", str(MIX_WAV),
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
        "-t", f"{duration:.3f}",
        "-movflags", "+faststart",
        str(OUT),
    ])


async def build(topic: str) -> None:
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise SystemExit("FFmpeg and ffprobe are required.")

    shutil.rmtree(FRAMES, ignore_errors=True)
    shutil.rmtree(VOICE_DIR, ignore_errors=True)
    shutil.rmtree(AUDIO_DIR, ignore_errors=True)
    BUILD.mkdir(parents=True, exist_ok=True)

    story = story_for(topic)
    durations, voice_map = await generate_voice_tracks(story)

    timeline = []
    offset = 0.0
    for scene, duration in zip(story, durations):
        timeline.append({
            "id": scene["id"],
            "start_seconds": round(offset, 3),
            "duration_seconds": round(duration, 3),
            "end_seconds": round(offset + duration, 3),
            "caption": scene["caption"],
            "speaker": scene["voice"],
            "voice": voice_map[scene["voice"]],
            "event": scene["event"],
        })
        offset += duration

    total = sum(durations)
    if not MIN_DURATION <= total <= MAX_DURATION:
        raise RuntimeError(f"Generated narration is {total:.2f}s; expected {MIN_DURATION}-{MAX_DURATION}s.")

    STORY_JSON.write_text(
        json.dumps(
            {
                "phase": 2,
                "topic": topic,
                "format": {"width": W, "height": H, "fps": FPS},
                "timeline": timeline,
                "voice_map": voice_map,
                "quality_target": "cinematic original 2D entertainment short",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    write_frames(story, durations)
    render_video()
    mix_audio(story, durations)
    mux()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True)
    args = parser.parse_args()
    topic = " ".join(args.topic.split()).strip()
    if not topic:
        raise SystemExit("Topic cannot be empty.")
    asyncio.run(build(topic))
    if not OUT.exists() or OUT.stat().st_size < 30000:
        raise RuntimeError("Final video was not created correctly.")
    print(f"Created: {OUT}")
    print(f"Size: {OUT.stat().st_size} bytes")
    print(f"Timeline: {STORY_JSON}")


if __name__ == "__main__":
    main()
