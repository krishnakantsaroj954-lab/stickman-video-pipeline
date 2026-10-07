# Stickman Video Pipeline

The previous Pillow renderer is frozen as a failed experiment. This branch tests a deterministic headless animation path instead.

Proof path:

story beat -> HTML Canvas scene -> Chromium renders exact frame time -> FFmpeg MP4

The proof is deliberately only 10 seconds. It must produce a real 720x1280 H.264 MP4 before this branch is considered usable.

Only after that proof passes will voice timing, captions, reusable characters, camera shots, SFX and full Shorts generation be added.

No JEE files, Cloudflare Worker, D1 or the old renderer are touched.
