# Ek Awaaz — revised premium edit

- Main film: 2:30, 1920×1080, 30 fps, H.264 with AAC audio.
- Narration: Microsoft en-IN-NeerjaExpressiveNeural, Indian-English female voice, generated with the user's approval. This is synthesized narration, not a human recording. The earlier macOS Rishi voice is no longer used.
- Script rewritten into shorter conversational sentences, with natural pauses; trailing silence trimmed and small timing corrections where needed.
- Animated waveform titles, staggered workflow cards, a branching listener/dispatcher explainer, editorial callouts, subtle 1.5% camera pushes, and half-second slide/dissolve transitions.
- Actual original screen recordings remain the app visuals. Editorial diagrams are explanatory graphics, not fabricated application screens.
- Outreach in the recording is clearly marked simulated. No phone calls or emergency contacts were made for this revision. No real caller audio is included.
- Captions use speech-service word timing rather than estimated scene timings. SRT sidecars and a clean, caption-free main export are included.
- Original ambient music is ducked beneath narration; subtle, newly synthesized transition sounds mark chapter changes.
- The separate portrait cut is recomposed at 1080×1920, not cropped from the widescreen export.
- Version-one files and raw recordings are preserved.

## Rebuild

From the project root, use `deliverables/video/.voice-env/bin/python` with these scripts:

1. `deliverables/video/scripts/voice_v2.py` — online narration generation (requires network).
2. `deliverables/video/scripts/render_v2.py --scenes --join` — main visuals.
3. `deliverables/video/scripts/finish_v2.py` — audio, aligned captions, main exports.
4. `deliverables/video/scripts/social_v2.py` — portrait cut and thumbnail.

All new media is under `deliverables/video/v2` or the versioned files in `deliverables/video/final`.
