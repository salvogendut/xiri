#!/usr/bin/env python3
"""Prepare the default SGI SoundScheme from a single private donor extraction."""
import argparse
from pathlib import Path
import re
import subprocess


def prepare(source, output):
    output.mkdir(parents=True, exist_ok=False)
    database = (source / "schemes/defaultScheme.ss").read_text(encoding="latin-1")
    samples = {}
    rows = []
    for line in database.splitlines():
        match = re.fullmatch(r"\*([A-Za-z0-9_]+)\.soundfile:\s*([\w.-]+)\s*", line)
        if not match:
            continue
        event, sample = match.groups()
        if sample not in samples:
            index = len(samples)
            subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-xerror", "-i",
                            str(source / "soundfiles" / sample), "-map", "0:a:0",
                            "-ac", "2", "-ar", "48000", "-f", "s16be",
                            str(output / f"{index}.pcm")], check=True)
            samples[sample] = index
        rows.append(f"{event} {samples[sample]}\n")
    if not rows:
        raise ValueError("The donor contains no SoundScheme entries")
    (output / "effects").write_text("".join(rows), encoding="ascii")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    prepare(args.source, args.output)
