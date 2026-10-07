# Stickman AI Entertainment Video Pipeline

This repo is for original funny/relatable stickman entertainment videos. It is separate from JEE PYQ Master.

Phase 1: build one real 45-second YouTube Short from a topic.

Pipeline build revision: 2026-10-07 dependency-fix

Flow: topic -> story -> stickman scenes -> Hindi voice -> captions -> SFX -> 9:16 MP4 -> quality gate -> artifact.

Current prototype uses Pillow + FFmpeg + eSpeak Hindi. The eSpeak track is a real prototype voice, not a claim that a premium AI voice provider is connected.

Rules:
- no fake success
- no automatic YouTube publishing
- no scraping or copying creators
- no reuse of JEE files, Workers or D1

Next phases:
1. Better animation and expressions
2. Better voice/caption/sound quality
3. Checkpoints, retries and targeted reruns
4. Shorts engine with multiple story formats
5. 3-5+ minute long-form engine
6. Controlled batch generation and optional publishing

Definition of done: 720x1280 MP4, about 45 seconds, real audio + video, phone-playable, QC PASS, downloadable artifact.