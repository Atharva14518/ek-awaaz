# Ek Awaaz demo video — project-aligned edit

## Runtime

- Master: exactly 2:30
- Social cut: exactly 0:20
- Master format: 1920×1080, 30 fps, H.264 video, AAC audio
- Social format: 1080×1920, 30 fps, H.264 video, AAC audio

## Workflow adaptations

- The edit shows the real application running in `DEMO_MODE` with real actions disabled.
- “Official emergency channel” claims were removed because that integration is not implemented in this build.
- The dispatcher sequence uses the real in-app action timeline: demo ambulance, family, police, and location-link steps.
- Correction handling uses the real Baner flyover → tunnel-side correction from the deterministic accident scenario.
- Silent mode uses the real phrase-trigger and keypad-style flow already implemented by the project.
- The report scene uses a report generated during the recorded live session, with its real timestamp.
- No public emergency number, personal number, API key, email, or unrelated browser tab appears in the delivered media.

## Audio and accessibility

- Narration uses the installed Rishi Indian-English voice at an unhurried pace.
- The ambient score and UI tones were generated specifically for this edit and do not use third-party music.
- The captioned master includes burned-in Poppins captions with a high-contrast dark backing.
- A separate `.srt` is included for platforms that support selectable captions.

## Reproducibility

- Live captures are in `../raw/`.
- Graphics and contact sheets are in `../frames/`.
- `../scripts/build_video.sh` rebuilds the master and social cut.
- `../scripts/generate_audio.py` recreates the original music and sound effects.
- `../scripts/make_graphics.py` recreates title cards and the thumbnail.
