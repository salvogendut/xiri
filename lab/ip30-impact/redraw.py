"""Measure a 4Dwm restack through IMPACT scanout on the shipped xdm desktops."""
import json
import statistics
import time

from PIL import Image


def measure(lab, out):
    # Both restored windows have exposed title bars. Their overlap here is
    # blank below the terminal's identity report and the file manager's icons.
    crop = (248, 282, 304, 40)
    path = out / 'restack-sample.png'
    shot = f'screen shot {path} ' + ' '.join(map(str, crop))
    targets = (('file_manager', (158, 190, 190), '65 12'),
               ('winterm', (0, 0, 62), '635 22'))

    def displayed(rgb):
        reply = lab.monitor_command(shot)
        if 'saved ' not in reply:
            raise RuntimeError(reply)
        with Image.open(path) as im:
            if im.size != crop[2:]:
                raise ValueError(f'unexpected scanout crop size: {im.size}')
            colors = im.convert('RGB').getcolors(im.width * im.height)
            return any(color == rgb and n >= im.width * im.height * .99 for n, color in colors)

    def raise_window(name, color, movement):
        # Position first. The measured interval starts at button-down.
        for delta in ('-1700 -1700', movement):
            lab.monitor_command('ps2 mouse ' + delta + ' 0')
            time.sleep(.3)
        if displayed(color):
            raise RuntimeError(f'{name} is already visible before the click')
        start = time.monotonic()
        lab.monitor_command('ps2 mouse 0 0 1')
        lab.monitor_command('ps2 mouse 0 0 0')
        while time.monotonic() - start < 10:
            if displayed(color):
                return round((time.monotonic() - start) * 1000, 2)
            time.sleep(.01)
        raise TimeoutError(f'{name} did not cover the overlap after the click')

    if not displayed(targets[1][1]):
        raise_window(*targets[1])
    # Warm both restacks before collecting alternate samples.
    for target in targets:
        raise_window(*target)
    samples = {name: [] for name, _, _ in targets}
    for _ in range(7):
        for target in targets:
            samples[target[0]].append(raise_window(*target))
    result = dict(crop=list(crop), minimum_coverage=.99, samples_ms=samples,
                  median_ms={k: statistics.median(v) for k, v in samples.items()})
    (out / 'restack.json').write_text(json.dumps(result, indent=2) + '\n')
    return result
