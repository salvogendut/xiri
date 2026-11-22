#!/usr/bin/env python3
"""Check actual IMPACT scanout against the Xlib probe's last displayed frame.

Requires Pillow. This reads the emulator PNG, independently of XGetImage's
software framebuffer readback, including all 8,928 final atlas pixels.
"""
import hashlib
import json
from pathlib import Path
import sys

from PIL import Image


def check(path):
    frame = Image.open(path).convert("RGB")
    assert frame.size == (1280, 1024), frame.size
    failures = []
    checked = 0
    for i, color in enumerate(((254, 0, 0), (0, 254, 0), (0, 0, 254), (254, 254, 254))):
        for y in (160, 280, 380, 460):
            point = (100 + 120 * i, y)
            actual = frame.getpixel(point)
            checked += 1
            if actual != color:
                failures.append(dict(point=point, expected=color, actual=actual))
    for y in range(93):
        for x in range(96):
            sx, sy = 1009 + x, 87 + y
            expected = ((11 * sx + 7 * sy) & 255, (5 * sx + sy) & 255,
                        (sx + 3 * sy) & 255)
            point = (560 + x, 240 + y)
            actual = frame.getpixel(point)
            checked += 1
            if actual != expected:
                failures.append(dict(point=point, expected=expected, actual=actual))
    return dict(passed=not failures, size=frame.size, checked_pixels=checked,
                mismatches=len(failures), examples=failures[:8],
                png_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest())


if __name__ == "__main__":
    result = check(sys.argv[1])
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passed"] else 1)
