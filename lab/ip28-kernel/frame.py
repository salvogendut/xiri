#!/usr/bin/env python3
"""Compare an IMPACT console capture with the Indy's original framed artwork."""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageChops

DISPLAY = (1280, 1024)
PANEL = (288, 176, 992, 848)


def load_reference(path):
    with Image.open(path) as artwork:
        if artwork.size != (1282, 1024):
            raise ValueError("expected a 1282x1024 source image")
        return artwork.convert("RGB").crop((0, 0, *DISPLAY))


def check(reference, path):
    with Image.open(path) as image:
        if image.size != DISPLAY:
            raise ValueError(f"{path} has size {image.size}")
        frame = image.convert("RGB")
    diff = ImageChops.difference(frame, reference)
    # Count a pixel once even if more than one RGB channel differs.
    r, g, b = diff.split()
    mask = ImageChops.lighter(ImageChops.lighter(r, g), b)
    panel = mask.crop(PANEL)
    text_pixels = panel.width * panel.height - panel.histogram()[0]
    mask.paste(0, PANEL)
    outside = frame.width * frame.height - panel.width * panel.height
    mismatches = mask.width * mask.height - mask.histogram()[0]
    return dict(image=path.name, outside_pixels=outside, outside_mismatches=mismatches,
                changed_panel_pixels=text_pixels,
                passed=mismatches == 0 and 100 < text_pixels < panel.width * panel.height // 2)


def check_scroll(shell, capture, reference):
    # Put the marker on the second row and the cursor on the last. One LF
    # must move the marker up exactly one row without disturbing the border.
    shell(r"printf '\033[2J\033[2;1HXiri scroll marker\033[42;1H' > /dev/ttyE0")
    before = capture("frame-before-scroll")
    shell(r"printf '\n' > /dev/ttyE0")
    after = capture("frame-after-scroll")
    left, top, right, _ = PANEL
    row1 = (left, top, right, top + 16)
    row2 = (left, top + 16, right, top + 32)
    with Image.open(before) as a, Image.open(after) as b:
        old, new = a.convert("RGB"), b.convert("RGB")
        marker = old.crop(row2)
        moved = (marker.tobytes() != reference.crop(row2).tobytes() and
                 old.crop(row1).tobytes() == reference.crop(row1).tobytes() and
                 new.crop(row1).tobytes() == marker.tobytes() and
                 new.crop(row2).tobytes() == reference.crop(row2).tobytes())
    frames = [check(reference, before), check(reference, after)]
    return dict(marker_moved=moved, captures=frames,
                passed=moved and all(r["passed"] for r in frames))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path, help="NetBSD fork's xiri/graphics/sgiconsole.png")
    parser.add_argument("captures", type=Path, nargs="+")
    args = parser.parse_args()
    reference = load_reference(args.reference)
    results = [check(reference, path) for path in args.captures]
    print(json.dumps(results, indent=2))
    return 0 if all(r["passed"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
