"""Generate the revised public demo narration, with real word timestamps."""
import asyncio
import json
from pathlib import Path

import edge_tts

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'v2' / 'voice'
VOICE = 'en-IN-NeerjaExpressiveNeural'
SEGMENTS = [
    (0.8, 9.8, "In an emergency, one person shouldn't have to make five calls. What if one calm conversation could coordinate the next steps?"),
    (10.6, 19.8, "Meet Ek Awaaz. A voice-first assistant with a simple idea: let the caller speak. Let the system handle the coordination."),
    (20.7, 30.8, "Here's the actual app. A clear starting point, a live console, and an incident report. Let's walk through a simulated road accident."),
    (31.4, 36.8, "Listen, understand, confirm, coordinate. Here's how it works."),
    (37.8, 56.7, "The caller speaks naturally, in Hinglish. A bike accident, with two people injured. Their words appear in the live transcript. Key details are highlighted as they arrive. One conversation, turning into a shared picture."),
    (57.7, 74.7, "Beside the transcript, the incident card takes shape. Location, people, and severity come together. Watch the address update when the caller gives a correction. The latest information matters more than the first guess."),
    (75.6, 86.7, "The caller confirms the incident type and location before coordination begins. See that checkpoint on the timeline? Understanding comes before action."),
    (87.5, 95.7, "Now the work splits. The listener supports the conversation. The dispatcher handles the next steps in parallel."),
    (96.7, 111.7, "In this recorded demo, ambulance and family outreach are simulated, with a location link shown alongside them. Each step has a visible status, so you can follow the handoff instead of wondering what's happening behind the scenes."),
    (112.6, 126.7, "When speaking freely isn't possible, the interaction changes. Silent mode offers discreet prompts and keypad responses. Less pressure on the caller, with a clear path to the next step."),
    (127.7, 142.7, "The incident report brings details and timestamped actions together. This is a prototype, not a live emergency response. No public emergency service was contacted. Every step stays visible."),
    (143.2, 149.8, "Ek Awaaz. One voice, many calls. Built with Bolna."),
]

async def generate(index, start, end, text, semaphore):
    target = OUT / f'{index:02d}.mp3'
    metadata = OUT / f'{index:02d}.json'
    if target.exists() and metadata.exists():
        cached = json.loads(metadata.read_text())
        if cached['text'] == text:
            return cached
    async with semaphore:
        events = []
        for attempt in range(3):
            try:
                with target.open('wb') as output:
                    events = []
                    stream = edge_tts.Communicate(text, VOICE, rate='+4%', boundary='WordBoundary')
                    async for chunk in stream.stream():
                        if chunk['type'] == 'audio':
                            output.write(chunk['data'])
                        elif chunk['type'] == 'WordBoundary':
                            events.append({k: chunk[k] for k in ('offset', 'duration', 'text')})
                break
            except Exception:
                if attempt == 2:
                    raise
                await asyncio.sleep(2)
        result = dict(index=index, start=start, end=end, text=text, voice=VOICE, words=events, audio=str(target))
        metadata.write_text(json.dumps(result, indent=2))
        print(f'Voice {index:02d}: {len(events)} words generated', flush=True)
        return result

async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    semaphore = asyncio.Semaphore(2)
    result = await asyncio.gather(*(generate(i, a, b, t, semaphore) for i, (a, b, t) in enumerate(SEGMENTS)))
    (OUT / 'manifest.json').write_text(json.dumps(result, indent=2))

if __name__ == '__main__':
    asyncio.run(main())
