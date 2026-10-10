"""Build original, offline synthesized ambience loops using the Python stdlib."""

import array
import math
from pathlib import Path
import random
import sys
import wave

ROOT = Path(__file__).resolve().parents[1] / "web" / "public" / "focus-audio"
RATE = 22050
SECONDS = 24
TAU = 2 * math.pi


def render(kind):
    rng = random.Random(812 + kind)
    samples = []
    low = slow = 0
    notes = [523.25, 659.25, 783.99, 987.77, 880, 783.99, 659.25, 587.33,
             523.25, 783.99, 659.25, 880, 783.99, 587.33, 659.25, 523.25]
    for i in range(RATE * SECONDS):
        t = i / RATE
        white = rng.uniform(-1, 1)
        low += .055 * (white - low)
        slow += .006 * (white - slow)
        if kind == 0:
            value = .3 * low + .028 * white
        elif kind == 1:
            value = 0
            for lag in range(4):
                note_index = math.floor(t / 1.5) - lag
                age = t - note_index * 1.5
                hz = notes[note_index % len(notes)]
                envelope = min(1, age / .014) * math.exp(-age * 2.4)
                value += .12 * envelope * (math.sin(TAU * hz * age) +
                                          .22 * math.sin(TAU * hz * 2.756 * age))
        elif kind == 2:
            value = (.17 * low + .055 * white) * (.82 + .18 * math.sin(TAU * t / 12))
        elif kind == 3:
            value = .075 * (white - low) * (.85 + .15 * math.cos(TAU * t / 8))
        elif kind == 4:
            ripple = math.sin(TAU * (360 * t + 8 * math.sin(TAU * t / 3)))
            value = .24 * low + .03 * white + .011 * ripple * (1 + math.sin(TAU * t * 4))
        elif kind == 5:
            swell = .22 + .78 * ((1 - math.cos(TAU * t / 8)) / 2) ** 1.6
            value = (.48 * low + .035 * white) * swell
        elif kind == 6:
            value = (.7 * slow + .12 * low) * (.7 + .3 * math.sin(TAU * t / 12))
        else:
            age = t % 1
            hz = 1450 if int(t) % 2 else 1050
            value = .18 * math.sin(TAU * hz * age) * math.exp(-age * 130) * min(1, age / .001)
        samples.append(value)
    # Rotate a short wrap-around crossfade into the loop to suppress boundary clicks.
    overlap = int(RATE * .12)
    blend = [samples[-overlap + i] * (1 - i / overlap) + samples[i] * (i / overlap)
             for i in range(overlap)]
    samples = blend + samples[overlap:-overlap]
    peak = max(abs(value) for value in samples)
    gain = min(1.4, .7 / peak)
    pcm = array.array("h", (round(value * gain * 32767) for value in samples))
    if sys.byteorder != "little":
        pcm.byteswap()
    return pcm.tobytes()


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    for kind, name in enumerate(["quiet", "music-box", "forest-rain", "rain", "stream", "ocean", "wind", "clock"]):
        with wave.open(str(ROOT / f"{name}.wav"), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(RATE)
            output.writeframes(render(kind))
        print(f"Created {name}.wav")


if __name__ == "__main__":
    main()
