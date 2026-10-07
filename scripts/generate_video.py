#!/usr/bin/env python3
"""Generate a small deterministic stickman educational video."""

from __future__ import annotations

import argparse
import math
import os
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH = 720
HEIGHT = 1280
FPS = 12
SCENE_SECONDS = 11.25
SCENES = 4
TOTAL_FRAMES = FPS * SCENE_SECONDS * SCENES

ROOT = Path(__file__).resolve().parent.parent
FRAMES = ROOT / "build" / "frames"
OUT = ROOT / "build" / "stickman-video.mp4"
VOICE_WAV = ROOT / "build" / "voice.wav"

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
]
REGULAR_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
]

def pick_font(candidates: list[str], size: int):
    for candidate in candidates:
        if os.path.exists(candidate):
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()

TITLE_FONT = pick_font(FONT_CANDIDATES, 54)
BODY_FONT = pick_font(REGULAR_FONT_CANDIDATES, 31)
SMALL_FONT = pick_font(REGULAR_FONT_CANDIDATES, 25)

def wrap_text(draw, text: str, font, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = word if not current else current + " " + word
        box = draw.textbbox((0, 0), trial, font=font)
        if box[2] - box[0] <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines

def centered_text(draw, text: str, y: int, font, max_width: int) -> None:
    lines = wrap_text(draw, text, font, max_width)
    line_gap = 10
    bbox = font.getbbox("Ag")
    line_h = bbox[3] - bbox[1]
    yy = y
    for line in lines:
        box = draw.textbbox((0, 0), line, font=font)
        x = (WIDTH - (box[2] - box[0])) // 2
        draw.text((x, yy), line, font=font, fill=(25, 25, 25))
        yy += line_h + line_gap

def draw_stickman(draw, cx: int, ground_y: int, phase: float, scale: float = 1.0) -> None:
    head_r = int(42 * scale)
    limb = int(105 * scale)
    head_y = ground_y - int(300 * scale)
    hip_y = ground_y - int(130 * scale)
    shoulder_y = ground_y - int(245 * scale)
    sway = int(math.sin(phase) * 12 * scale)
    cx += sway

    width = max(3, int(7 * scale))
    draw.ellipse(
        (cx - head_r, head_y - head_r, cx + head_r, head_y + head_r),
        outline=(30, 30, 30),
        width=width,
    )
    draw.line((cx, shoulder_y, cx, hip_y), fill=(30, 30, 30), width=width + 1)

    arm_angle = math.sin(phase * 1.6) * 0.45
    ax = math.sin(arm_angle) * limb
    ay = math.cos(arm_angle) * limb
    draw.line((cx, shoulder_y, cx - ax, shoulder_y + ay), fill=(30, 30, 30), width=width)
    draw.line((cx, shoulder_y, cx + ax, shoulder_y - ay), fill=(30, 30, 30), width=width)

    leg_swing = math.sin(phase * 1.4) * 0.55
    lx = math.sin(leg_swing) * limb
    draw.line((cx, hip_y, cx - lx, ground_y), fill=(30, 30, 30), width=width)
    draw.line((cx, hip_y, cx + lx, ground_y), fill=(30, 30, 30), width=width)

def draw_scene(index: int, topic: str, frame_in_scene: int) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), (248, 248, 248))
    draw = ImageDraw.Draw(img)

    draw.rectangle((0, 0, WIDTH, 125), fill=(235, 235, 235))
    draw.text((40, 32), f"STICKMAN STORY  •  {index}/4", font=SMALL_FONT, fill=(70, 70, 70))

    titles = [
        f"Today: {topic}",
        "THE PLAN",
        "THE CHAOS",
        "PLOT TWIST",
    ]
    centered_text(draw, titles[index - 1], 165, TITLE_FONT, 630)

    t = frame_in_scene / max(1, FPS * SCENE_SECONDS - 1)
    phase = t * math.tau
    ground = 850

    if index == 1:
        draw_stickman(draw, 360, ground, phase, 1.0)
        draw.rounded_rectangle((120, 940, 600, 1100), radius=24, outline=(80, 80, 80), width=4)
        centered_text(draw, f"{topic} starts innocent... then everything goes sideways.", 975, BODY_FONT, 430)
    elif index == 2:
        draw_stickman(draw, 270, ground, phase, 0.95)
        draw_stickman(draw, 450, ground, phase + math.pi, 0.95)
        draw.line((330, 690, 390, 690), fill=(60, 60, 60), width=8)
        draw.polygon((390, 690, 365, 675, 365, 705), fill=(60, 60, 60))
        draw.rounded_rectangle((80, 940, 640, 1100), radius=24, outline=(80, 80, 80), width=4)
        centered_text(draw, "Step 1: confidence. Step 2: overconfidence. Step 3: panic.", 975, BODY_FONT, 510)
    elif index == 3:
        x = int(160 + 400 * t)
        draw_stickman(draw, x, ground, phase * 1.3, 0.9)
        draw.line((120, 900, 600, 900), fill=(100, 100, 100), width=5)
        draw.rounded_rectangle((90, 940, 630, 1100), radius=24, outline=(80, 80, 80), width=4)
        centered_text(draw, "At this point the original plan has officially left the chat.", 975, BODY_FONT, 490)
    else:
        draw_stickman(draw, 360, ground, phase, 1.0)
        draw.rounded_rectangle((100, 925, 620, 1105), radius=24, outline=(80, 80, 80), width=4)
        centered_text(draw, "Lesson learned: backup plan rakho... hero mat bano.", 955, BODY_FONT, 470)

    footer = "Original stickman entertainment prototype"
    box = draw.textbbox((0, 0), footer, font=SMALL_FONT)
    draw.text(((WIDTH - (box[2] - box[0])) // 2, 1180), footer, font=SMALL_FONT, fill=(100, 100, 100))
    return img

def make_voice(topic: str) -> None:
    if not shutil.which("espeak"):
        raise RuntimeError("eSpeak is required but was not found.")
    narration = (
        f"Aaj ka topic hai {topic}. "
        "Shuru mein sab simple lag raha tha. "
        "Phir ek chhoti si problem aayi aur plan seedha chaos ban gaya. "
        "Main sochta raha, sab control mein hai. "
        "Lekin plot twist ye tha ki problem situation nahi, meri overconfidence thi. "
        "Agli baar backup plan ke bina hero mode nahi."
    )
    subprocess.run(
        ["espeak", "-v", "hi", "-s", "155", "-p", "52", "-a", "150", "-w", str(VOICE_WAV)],
        input=narration,
        text=True,
        check=True,
    )

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", default="Funny topic", help="Topic for the entertainment Short")
    args = parser.parse_args()

    topic = " ".join(args.topic.split()).strip() or "Physics"
    topic = topic[:80].rstrip()

    if FRAMES.exists():
        shutil.rmtree(FRAMES)
    FRAMES.mkdir(parents=True, exist_ok=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)

    for frame_no in range(TOTAL_FRAMES):
        scene = frame_no // (FPS * SCENE_SECONDS) + 1
        local = frame_no % (FPS * SCENE_SECONDS)
        draw_scene(scene, topic, local).save(FRAMES / f"frame-{frame_no:05d}.png", optimize=True)

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg is required but was not found.")

    subprocess.run(
        [
            ffmpeg, "-y",
            "-framerate", str(FPS),
            "-i", str(FRAMES / "frame-%05d.png"),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(OUT),
        ],
        check=True,
    )

    make_voice(topic)
    final = OUT.with_name("stickman-video-final.mp4")
    subprocess.run(
        [
            ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(OUT),
            "-i", str(VOICE_WAV),
            "-filter_complex", "[1:a]apad,volume=1[a]",
            "-map", "0:v:0", "-map", "[a]",
            "-t", str(SCENE_SECONDS * SCENES),
            "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart", str(final),
        ],
        check=True,
    )
    final.replace(OUT)

    if not OUT.exists() or OUT.stat().st_size < 10_000:
        raise RuntimeError("Video was not created correctly.")

    print(f"Created: {OUT}")
    print(f"Size: {OUT.stat().st_size} bytes")

if __name__ == "__main__":
    main()
