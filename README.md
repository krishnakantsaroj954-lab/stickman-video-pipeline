# Stickman AI Entertainment Video Pipeline

This repo generates original, animated Hindi/Hinglish entertainment Shorts. It is separate from JEE PYQ Master.

## Phase 2

The target is a polished 2D storytelling Short rather than a static slideshow.

Pipeline:

topic -> scripted story beats -> character acting -> scene backgrounds -> camera movement -> neural Hindi voice -> voice-derived timeline -> timed captions -> procedural SFX -> 9:16 H.264/AAC MP4 -> quality gate -> GitHub artifact

### What Phase 2 adds

- Two recurring characters with distinct visual identity and neural Hindi voices.
- Multiple backgrounds and shot types: close, medium, wide and impact/shake.
- Facial expressions and pose changes for confidence, surprise, panic, scolding, sadness and celebration.
- Actual narration duration controls scene timing; captions are derived from that timing instead of fixed 7.5-second blocks.
- Caption chunks animate slightly and remain readable on a phone.
- Procedural impact/whoosh/pop accents are mixed quietly under the dialogue.
- A machine-checkable MP4 gate checks resolution, frame rate, codecs, audio format and audio/video duration drift.
- build/story.json records the selected voices and the measured scene timeline.

## Run

Open **Actions -> Generate Stickman Entertainment Short -> Run workflow**, enter a topic, and download the **stickman-short-phase2** artifact after the workflow passes.

Example topic:

Mummy ke saamne phone chalaate hue pakde jaana

## Quality policy

A green GitHub job only means the technical render gates passed. Visual quality is still judged from the actual rendered artifact. The pipeline does not scrape, copy or reuse another creator's characters, footage or audio.

There is no automatic YouTube publishing and no required paid API key in Phase 2.

## Next upgrade

Phase 3 can add a richer story engine with more scene templates, reusable props, stronger lip-sync cues and optional long-form rendering without changing the core Phase 2 artifact contract.
