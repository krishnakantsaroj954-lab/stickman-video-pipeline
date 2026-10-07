import argparse
import json
import shutil
import subprocess
from pathlib import Path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('video')
    path = Path(ap.parse_args().video)
    if not path.exists() or path.stat().st_size < 20000:
        raise SystemExit('FAIL: MP4 missing or too small')
    if not shutil.which('ffprobe'):
        raise SystemExit('FAIL: ffprobe missing')
    raw = subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-show_entries','stream=codec_type,codec_name,width,height','-of','json',str(path)], text=True)
    data = json.loads(raw)
    streams = data.get('streams', [])
    video = next((s for s in streams if s.get('codec_type') == 'video'), None)
    audio = next((s for s in streams if s.get('codec_type') == 'audio'), None)
    duration = float((data.get('format') or {}).get('duration') or 0)
    errors = []
    if not video: errors.append('video stream missing')
    elif int(video.get('width',0)) != 720 or int(video.get('height',0)) != 1280: errors.append('wrong resolution')
    if not audio: errors.append('audio stream missing')
    if duration < 40 or duration > 50: errors.append('unexpected duration')
    report = {'status':'FAIL' if errors else 'PASS','duration_seconds':round(duration,2),'errors':errors}
    Path('quality-report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    if errors: raise SystemExit(1)

if __name__ == '__main__': main()
