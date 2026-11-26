#!/usr/bin/env python3
"""Generate the stereo source or check the four S16LE stereo SDL captures."""
import argparse
import json
import subprocess
import wave
from pathlib import Path

import numpy as np

TONES = ((440, 733), (611, 457), (349, 997))
HOST_RATE = 48000


def fixture(path, rate=44100, channel=None):
    t = np.arange(rate) / rate
    with wave.open(str(path), 'wb') as wav:
        wav.setparams((2, 2, rate, 0, 'NONE', ''))
        for pair in TONES:
            samples = np.column_stack([np.sin(2*np.pi*f*t) for f in pair])
            if channel is not None:
                samples[:, 1-channel] = 0
            wav.writeframes(np.rint(18000 * samples).astype('<i2').tobytes())


def load(path):
    pcm = np.fromfile(path, dtype='<i2')
    if not pcm.size or pcm.size % 2:
        raise ValueError(f'{path} is empty or ends mid-frame')
    return pcm.reshape(-1, 2).astype(float)


def stereo(pcm):
    # 100 ms has ten-hertz FFT bins. Sub-bin interpolation distinguishes
    # a correct 44.1 -> 48 kHz conversion from playing at the wrong rate.
    frames = HOST_RATE // 10
    window = np.hanning(frames)[:, None]
    matches = []
    for block in range(0, len(pcm) - frames + 1, frames):
        samples = pcm[block:block + frames]
        spectrum = np.abs(np.fft.rfft(samples * window, axis=0))
        bins = np.argmax(spectrum, axis=0)
        if min(bins) < 2 or max(bins) + 1 >= len(spectrum):
            continue
        channels = np.arange(2)
        a, b, c = np.log(np.maximum(1e-9, np.array(
            [spectrum[bins + delta, channels] for delta in (-1, 0, 1)])))
        hz = (bins + .5 * (a-c) / (a-2*b+c)) * HOST_RATE / frames
        for idx, pair in enumerate(TONES):
            if np.max(np.abs(hz-pair)) <= 7 and np.min(b) > np.log(5000):
                matches.append((idx, hz, np.max(np.abs(samples), axis=0)))
    order = [idx for i, (idx, _, _) in enumerate(matches)
             if i == 0 or idx != matches[i-1][0]]
    if order != [0, 1, 2]:
        raise ValueError(f'Stereo tone order {order}, expected three successive pairs')
    result = []
    for idx in range(3):
        hits = [(hz, peak) for who, hz, peak in matches if who == idx]
        if not 7 <= len(hits) <= 12:
            raise ValueError(f'Observed {len(hits)} matching 100 ms blocks for {TONES[idx]}')
        hz, peaks = map(np.array, zip(*hits))
        result.append(dict(hz=np.median(hz, axis=0).round(1).tolist(),
                           matched_100ms_blocks=len(hits),
                           peak=np.max(peaks, axis=0).astype(int).tolist()))
    return result


def effect_score(capture, source):
    raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(source),
                                   '-ar', str(HOST_RATE), '-ac', '1', '-f', 's16le', '-'])
    signal = np.frombuffer(raw, '<i2').astype(float)
    size = 512
    start = int(np.argmax(np.convolve(signal**2, np.ones(size), 'valid')))
    ref = signal[start:start+size]
    ref = ref-ref.mean()
    if not np.linalg.norm(ref) or len(capture) < size:
        raise ValueError('Silent or incomplete effect reference or capture')
    result = []
    for x in capture.T:
        energy = np.convolve(x*x, np.ones(size), 'valid')
        energy -= np.convolve(x, np.ones(size), 'valid')**2 / size
        score = np.correlate(x, ref, 'valid') / np.maximum(
            1., np.sqrt(np.maximum(0, energy)) * np.linalg.norm(ref))
        result.append(round(float(np.max(score)), 4))
    if min(result) < .92:
        raise ValueError(f'AIFF channel correlations {result}')
    return result


def check(directory, source, extra=False):
    full = stereo(load(directory/'stereo.pcm'))
    restored = stereo(load(directory/'restored.pcm'))
    silent = int(np.max(np.abs(load(directory/'muted.pcm'))))
    if silent:
        raise ValueError(f'SGI master gain at negative infinity produced peak {silent}')
    for base, after in zip(full, restored):
        left, right = np.array(after['peak']) / base['peak']
        if not all(6500 <= peak <= 11500 for peak in base['peak']):
            raise ValueError(f"Unexpected level for 18000-count source at master 128,128: {base['peak']}")
        if not (.4 < left < .6 and .9 < right < 1.1):
            raise ValueError(f'Unexpected channel gains after 64,128 restore: {left}, {right}')
    result = dict(stereo=full, muted_peak=silent, restored=restored,
                  effect_correlation=effect_score(load(directory/'effect.pcm'), source))
    if extra:
        result['native_48khz'] = stereo(load(directory/'native48.pcm'))
        result['concurrent_ports'] = stereo(load(directory/'overlap.pcm'))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    generator = sub.add_parser('generate')
    generator.add_argument('wave', type=Path)
    generator.add_argument('--rate', type=int, choices=(44100, 48000), default=44100)
    generator.add_argument('--channel', type=int, choices=(0, 1))
    verify = sub.add_parser('check')
    verify.add_argument('directory', type=Path)
    verify.add_argument('donor_aiff', type=Path)
    verify.add_argument('--extra', action='store_true', help='also check 48 kHz and concurrent ports')
    args = parser.parse_args()
    if args.action == 'generate':
        fixture(args.wave, args.rate, args.channel)
    else:
        print(json.dumps(check(args.directory, args.donor_aiff, args.extra), indent=2))
