"""Check an Indy framebuffer, mixer readback and stereo PCM after each mute transition."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from live import measure, verify

# Open Audio Panel with mute already on, reproducing the original report.
STATES = (
    ('initial', 'on'),
    ('native_off', 'off'),
    ('panel_on', 'on'),
    ('native_off_again', 'off'),
    ('native_on', 'on'),
    ('same_native_on', 'on'),
    ('panel_off', 'off'),
)


def checkbox(ppm, x, y):
    """Count red check-mark pixels inside the SGI Mute box."""
    header = re.match(rb'P6\s+(?:#[^\n]*\n\s*)*(\d+)\s+(\d+)\s+255\s', ppm)
    if not header:
        raise ValueError('Expected a binary RGB Prismatic framebuffer')
    width, height = map(int, header.groups())
    pixels = memoryview(ppm)[header.end():]
    if len(pixels) != width * height * 3 or not (7 <= x < width-7 and 7 <= y < height-7):
        raise ValueError('Invalid framebuffer size or checkbox coordinates')
    crop = b''.join(pixels[3*(row*width+x-7):3*(row*width+x+8)] for row in range(y-7, y+8))
    colors = zip(crop[::3], crop[1::3], crop[2::3])
    red = sum(r > 120 and r > 2*g and r > 2*b for r, g, b in colors)
    return dict(red_pixels=red, crop_sha256=hashlib.sha256(crop).hexdigest())


def check(directory, x, y):
    results = {}
    player = None
    for name, mute in STATES:
        gain, switch, pid = (directory / (name + '.txt')).read_text().split()
        if player is None:
            player = int(pid)
        if player <= 0 or int(pid) != player or gain != '64,128' or switch != mute:
            raise ValueError(f'{name}: mixer or player mismatch: {gain}, {switch}, PID {pid}')
        frame = checkbox((directory / (name + '.ppm')).read_bytes(), x, y)
        red = frame['red_pixels']
        if (mute == 'on' and red < 4) or (mute == 'off' and red != 0):
            raise ValueError(f'{name}: mute={mute}, found {red} red check-mark pixels')
        samples = measure((directory / (name + '.pcm')).read_bytes())
        results[name] = dict(mute=mute, **frame, **samples)

    # Cover every recorded interval, including the repeated native write.
    for details in results.values():
        muted = details if details['mute'] == 'on' else results['initial']
        restored = details if details['mute'] == 'off' else results['panel_off']
        verify(dict(playing=results['native_off'], muted=muted, restored=restored))
    return dict(player_pid=player, gain=[64, 128], checkbox_center=[x, y], states=results)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('x', type=int, help='Framebuffer X coordinate of the checkbox center')
    parser.add_argument('y', type=int, help='Framebuffer Y coordinate of the checkbox center')
    args = parser.parse_args()
    print(json.dumps(check(args.directory, args.x, args.y), indent=2))
