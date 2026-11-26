#!/usr/bin/env python3
"""Generate a continuous stereo tone and compare host PCM before, during and after GUI mute."""
import argparse
import array
import json
import math
from pathlib import Path
import struct
import sys
import wave

RATE = 48000
FREQUENCIES = (440, 730)


def generate(path, seconds):
    if seconds < 1:
        raise ValueError('Expected a positive duration')
    second = b''.join(struct.pack('<hh', *(round(16000 * math.sin(2 * math.pi * hz * t / RATE))
                                          for hz in FREQUENCIES)) for t in range(RATE))
    with wave.open(str(path), 'wb') as stream:
        stream.setparams((2, 2, RATE, 0, 'NONE', 'PCM'))
        for _ in range(seconds):
            stream.writeframesraw(second)


def measure(pcm):
    if len(pcm) < RATE * 2 or len(pcm) % 4:
        raise ValueError('Expected at least half a second of complete stereo S16LE frames')
    samples = array.array('h', pcm)
    if sys.byteorder != 'little':
        samples.byteswap()
    peaks, frequencies = [], []
    for channel in range(2):
        values = samples[channel::2]
        peaks.append(max(map(abs, values)))
        # A disk-driver capture can include silence around an otherwise valid tone.
        rates = []
        for offset in range(0, len(values) - 2399, 2400):
            block = values[offset:offset + 2400]
            crossings = [i for i in range(1, len(block)) if block[i-1] < 0 <= block[i]]
            if len(crossings) >= 12:
                rates.append(RATE * (len(crossings) - 1) / (crossings[-1] - crossings[0]))
        frequencies.append(round(sorted(rates)[len(rates)//2], 1) if rates else 0)
    return dict(frames=len(samples)//2, peaks=peaks, hz=frequencies)


def verify(stages):
    if stages['muted']['peaks'] != [0, 0]:
        raise ValueError('The muted interval contains nonzero samples')
    for phase in ('playing', 'restored'):
        left, right = stages[phase]['peaks']
        if right <= 1000 or not .45 < left/right < .55:
            raise ValueError(f'Unexpected stereo peaks at mixer 64,128 in {phase}: {left}, {right}')
        if any(abs(actual - expected) >= 8 for actual, expected in zip(stages[phase]['hz'], FREQUENCIES)):
            raise ValueError('Unexpected channel frequencies in ' + phase)
    for before, after in zip(stages['playing']['peaks'], stages['restored']['peaks']):
        if abs(before-after) > .05*before:
            raise ValueError('Unmuting did not restore the previous channel level')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    fixture = sub.add_parser('generate')
    fixture.add_argument('wave', type=Path)
    fixture.add_argument('--seconds', type=int, default=180)
    check = sub.add_parser('check')
    check.add_argument('directory', type=Path)
    args = parser.parse_args()
    if args.action == 'generate':
        generate(args.wave, args.seconds)
    else:
        results = {stage: measure((args.directory / (stage + '.pcm')).read_bytes())
                   for stage in ('playing', 'muted', 'restored')}
        verify(results)
        print(json.dumps(results, indent=2))
