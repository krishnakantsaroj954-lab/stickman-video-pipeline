import argparse
import json
import shutil
import subprocess
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    path = Path(ap.parse_args().video)

    if not path.exists() or path.stat().st_size < 30000:
        raise SystemExit("FAIL: MP4 missing or too small")
    if not shutil.which("ffprobe"):
        raise SystemExit("FAIL: ffprobe missing")

    raw = subprocess.check_output(
        [
            "ffprobe", "-v", "error",
            "-show_entries",
            "format=duration,size:stream=codec_type,codec_name,width,height,avg_frame_rate,sample_rate,channels,bit_rate,duration",
            "-of", "json",
            str(path),
        ],
        text=True,
    )
    data = json.loads(raw)
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    fmt = data.get("format") or {}

    duration = float(fmt.get("duration") or 0)
    errors = []

    if not video:
        errors.append("video stream missing")
    else:
        if int(video.get("width", 0)) != 720 or int(video.get("height", 0)) != 1280:
            errors.append("wrong resolution")
        if video.get("codec_name") != "h264":
            errors.append("video codec is not H.264")
        fps = video.get("avg_frame_rate", "0/1")
        if fps not in {"18/1", "18/1.0"}:
            errors.append(f"unexpected fps: {fps}")

    if not audio:
        errors.append("audio stream missing")
    else:
        if audio.get("codec_name") != "aac":
            errors.append("audio codec is not AAC")
        if int(audio.get("sample_rate", 0)) != 48000:
            errors.append("audio sample rate is not 48 kHz")
        if int(audio.get("channels", 0)) != 1:
            errors.append("audio is not mono")
        audio_duration = float(audio.get("duration") or 0)
        if abs(audio_duration - duration) > 0.25:
            errors.append(
                f"audio/video duration drift too large: audio={audio_duration:.3f}s video={duration:.3f}s"
            )
        audio_bitrate = int(audio.get("bit_rate", 0) or 0)
        if audio_bitrate < 96000:
            errors.append(f"audio bitrate too low: {audio_bitrate}")

    if not 35 <= duration <= 58:
        errors.append(f"unexpected duration: {duration:.2f}s")

    size_bytes = int(fmt.get("size", path.stat().st_size) or 0)
    report = {
        "status": "FAIL" if errors else "PASS",
        "duration_seconds": round(duration, 3),
        "size_bytes": size_bytes,
        "video": video,
        "audio": audio,
        "errors": errors,
    }

    Path("quality-report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))

    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
