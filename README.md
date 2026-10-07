# Stickman Video Pipeline

A lightweight, GitHub-Actions-friendly pipeline that turns a topic into a simple educational stickman MP4.

## Current stage

This first stage is intentionally dependency-light and deterministic:

1. Accept a topic.
2. Build a short 4-scene storyboard locally.
3. Draw stickman scenes with Pillow.
4. Render the frames to an MP4 with FFmpeg.
5. Upload the MP4 as a GitHub Actions artifact.

No web scraping, no background services, no repository polling, and no required API keys.

## Run

Open **Actions → Generate Stickman Video → Run workflow**, enter a topic, and download the `stickman-video` artifact from the completed run.

The push-triggered smoke test also runs automatically to verify the pipeline after changes.

## Next stages

After this smoke-test version is proven, AI script generation, voice-over, richer animation, and YouTube publishing can be added as separate optional stages.
