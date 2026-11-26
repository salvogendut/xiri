#!/usr/bin/env python3
"""Verify SDL stereo capture segments against a prepared private donor effect."""
import argparse
import json
from pathlib import Path

import numpy as np


def measure(samples, reference):
    frames = len(reference)
    peak = int(np.max(np.abs(samples)))
    result = {"frames": len(samples), "peak": peak}
    if peak == 0:
        return result
    if len(samples) < frames:
        raise ValueError("SDL capture is shorter than the donor comparison window")
    result["signed_range"] = [int(samples.min()), int(samples.max())]
    correlations = []
    for channel in range(2):
        x = samples[:, channel]
        y = reference[:, channel] - reference[:, channel].mean()
        ones = np.ones(frames)
        sums = np.convolve(x, ones, mode="valid")
        energy = np.convolve(x*x, ones, mode="valid") - sums*sums / frames
        denominator = np.sqrt(np.maximum(0, energy)) * np.linalg.norm(y)
        scores = np.correlate(x, y, "valid") / np.maximum(1, denominator)
        correlations.append(round(float(np.max(scores)), 4))
    result["donor_correlation_left_right"] = correlations
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("donor", type=Path, help="48 kHz stereo signed 16-bit big-endian")
    parser.add_argument("captures", type=Path, help="directory of named .pcm SDL segments")
    args = parser.parse_args()
    donor = np.fromfile(args.donor, dtype=">i2").reshape(-1, 2).astype(float)
    frames = 512
    start = int(np.argmax(np.convolve(donor[:, 0]**2, np.ones(frames), mode="valid")))
    reference = donor[start:start+frames]
    result = {}
    for name in ("full", "scheme_half", "scheme_muted", "restored", "prismatic_half",
                 "prismatic_muted", "prismatic_restored", "native_mixer_zero",
                 "native_mixer_restored"):
        audio = np.fromfile(args.captures / (name+".pcm"), dtype="<i2")
        result[name] = measure(audio.reshape(-1, 2).astype(float), reference)
    print(json.dumps({"donor_window_start": start, "donor_window_frames": frames,
                      "sample": result}, indent=2))
    full = result["full"]["peak"]
    for name, m in result.items():
        if name.endswith(("_muted", "_zero")):
            if m["peak"]:
                raise SystemExit(f"{name} produced nonzero samples")
        else:
            if min(m.get("donor_correlation_left_right", [0])) < 0.85:
                raise SystemExit(f"{name} did not reproduce the donor waveform")
            ratio = m["peak"] / full
            target = 0.5 if name.endswith("_half") else 1.0
            if abs(ratio-target) > 0.06:
                raise SystemExit(f"{name} peak was {ratio:.3f} of full volume")


if __name__ == "__main__":
    main()
