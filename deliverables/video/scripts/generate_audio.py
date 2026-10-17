from __future__ import annotations

import wave
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
AUDIO = ROOT / "audio"
RATE = 48_000


def write_stereo(path: Path, samples: np.ndarray) -> None:
    samples = np.clip(samples, -0.98, 0.98)
    pcm = (samples * 32767).astype("<i2")
    with wave.open(str(path), "wb") as target:
        target.setnchannels(2)
        target.setsampwidth(2)
        target.setframerate(RATE)
        target.writeframes(pcm.tobytes())


def fade_envelope(length: int, fade_seconds: float = 1.8) -> np.ndarray:
    envelope = np.ones(length, dtype=np.float32)
    fade = min(int(fade_seconds * RATE), length // 2)
    if fade:
        ramp = np.sin(np.linspace(0, np.pi / 2, fade, dtype=np.float32)) ** 2
        envelope[:fade] = ramp
        envelope[-fade:] = ramp[::-1]
    return envelope


def generate_music(duration: float = 150.0) -> np.ndarray:
    total = int(duration * RATE)
    left = np.zeros(total, dtype=np.float32)
    right = np.zeros(total, dtype=np.float32)
    progression = (
        (130.81, 164.81, 196.00, 246.94),
        (110.00, 130.81, 164.81, 196.00),
        (87.31, 130.81, 164.81, 220.00),
        (98.00, 146.83, 196.00, 220.00),
    )
    chord_seconds = 12.0
    chord_samples = int(chord_seconds * RATE)
    for index, start in enumerate(range(0, total, chord_samples)):
        end = min(start + chord_samples, total)
        length = end - start
        t = np.arange(length, dtype=np.float32) / RATE
        env = fade_envelope(length)
        chord = progression[index % len(progression)]
        for voice, frequency in enumerate(chord):
            phase = voice * 0.43 + index * 0.17
            tone_l = np.sin(2 * np.pi * frequency * t + phase)
            tone_r = np.sin(2 * np.pi * (frequency * 1.0012) * t + phase + 0.08)
            harmonic_l = 0.22 * np.sin(2 * np.pi * frequency * 2 * t + phase / 2)
            harmonic_r = 0.22 * np.sin(2 * np.pi * frequency * 2.002 * t + phase / 2)
            weight = 0.010 if voice < 3 else 0.006
            left[start:end] += (tone_l + harmonic_l) * env * weight
            right[start:end] += (tone_r + harmonic_r) * env * weight

    melody = (392.00, 440.00, 523.25, 440.00, 349.23, 392.00, 493.88, 392.00)
    note_seconds = 0.9
    note_samples = int(note_seconds * RATE)
    for index, start_seconds in enumerate(np.arange(3.0, duration, 6.0)):
        start = int(start_seconds * RATE)
        end = min(start + note_samples, total)
        length = end - start
        t = np.arange(length, dtype=np.float32) / RATE
        frequency = melody[index % len(melody)]
        env = np.exp(-4.6 * t) * np.minimum(1.0, t / 0.035)
        note = (
            np.sin(2 * np.pi * frequency * t)
            + 0.34 * np.sin(2 * np.pi * frequency * 2 * t)
            + 0.12 * np.sin(2 * np.pi * frequency * 3 * t)
        ) * env * 0.035
        if index % 2:
            left[start:end] += note * 0.55
            right[start:end] += note
        else:
            left[start:end] += note
            right[start:end] += note * 0.55

    master = np.column_stack((left, right))
    master *= np.linspace(0.0, 1.0, int(2.0 * RATE), dtype=np.float32).tolist() + [1.0] * (total - int(2.0 * RATE)) if False else 1.0
    fade = int(2.0 * RATE)
    master[:fade] *= np.linspace(0.0, 1.0, fade, dtype=np.float32)[:, None]
    master[-fade:] *= np.linspace(1.0, 0.0, fade, dtype=np.float32)[:, None]
    return master


def generate_ring(duration: float = 3.0) -> np.ndarray:
    total = int(duration * RATE)
    t = np.arange(total, dtype=np.float32) / RATE
    gate = ((t % 1.05) < 0.62).astype(np.float32)
    edge = int(0.025 * RATE)
    for start_seconds in np.arange(0, duration, 1.05):
        start = int(start_seconds * RATE)
        stop = min(start + int(0.62 * RATE), total)
        if stop - start > edge * 2:
            gate[start:start + edge] *= np.linspace(0, 1, edge, dtype=np.float32)
            gate[stop - edge:stop] *= np.linspace(1, 0, edge, dtype=np.float32)
    signal = (np.sin(2 * np.pi * 440 * t) + 0.72 * np.sin(2 * np.pi * 480 * t)) * gate * 0.12
    return np.column_stack((signal, signal))


def generate_chime(duration: float = 0.55) -> np.ndarray:
    total = int(duration * RATE)
    t = np.arange(total, dtype=np.float32) / RATE
    env = np.exp(-7.5 * t) * np.minimum(1.0, t / 0.012)
    signal = (np.sin(2 * np.pi * 783.99 * t) + 0.55 * np.sin(2 * np.pi * 1174.66 * t)) * env * 0.10
    return np.column_stack((signal * 0.82, signal))


def main() -> None:
    AUDIO.mkdir(parents=True, exist_ok=True)
    write_stereo(AUDIO / "original-ambient-bed.wav", generate_music())
    write_stereo(AUDIO / "phone-ring.wav", generate_ring())
    write_stereo(AUDIO / "ui-chime.wav", generate_chime())


if __name__ == "__main__":
    main()
