"""Generate original completion chimes without third-party recordings."""

from array import array
import math
from pathlib import Path
import sys
import wave

ROOT = Path(__file__).resolve().parents[1] / "web/src/components/tomato"
RATE = 22050


def chime(seconds):
    samples = array("h")
    notes = (523.25, 659.25, 783.99, 1046.50)
    for frame in range(RATE * seconds):
        time = frame / RATE
        value = 0
        for index in range(int(time / .55) + 1):
            age = time - index * .55
            if age > 2:
                continue
            hz = notes[index % len(notes)]
            envelope = min(1, age / .02) * math.exp(-age * 3)
            value += .18 * envelope * (math.sin(math.tau * hz * age) +
                                       .2 * math.sin(math.tau * hz * 2 * age))
        fade = min(1, (seconds - time) / .5)
        samples.append(round(value * fade * 32767))
    if sys.byteorder != "little":
        samples.byteswap()
    return samples


if __name__ == "__main__":
    ROOT.mkdir(parents=True, exist_ok=True)
    for name, seconds in (("S01.wav", 6), ("M01.wav", 18)):
        with wave.open(str(ROOT / name), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(RATE)
            output.writeframes(chime(seconds).tobytes())
        print(f"Created {name}")
