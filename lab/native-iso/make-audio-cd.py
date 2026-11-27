#!/usr/bin/env python3
"""Create a two-track audio CD for the Indy media tests (440 Hz, then 880 Hz)."""
import argparse
import math
from pathlib import Path
import struct
import subprocess
import tempfile
import wave


def make_disc(output, chdman):
    output = output.resolve()
    with tempfile.TemporaryDirectory(dir=output.parent) as tmp:
        work = Path(tmp)
        cue = []
        for track, hz in enumerate((440, 880), 1):
            name = f'track{track}.wav'
            samples = [round(8192 * math.sin(2 * math.pi * hz * i / 44100))
                       for i in range(44100)]
            second = b''.join(struct.pack('<hh', sample, sample) for sample in samples)
            with wave.open(str(work / name), 'wb') as wav:
                wav.setparams((2, 2, 44100, 0, 'NONE', ''))
                wav.writeframes(second * 12)
            cue.extend([f'FILE "{name}" WAVE', f'  TRACK {track:02} AUDIO',
                        '    INDEX 01 00:00:00'])
        (work / 'test.cue').write_text('\n'.join(cue) + '\n')
        subprocess.run([chdman, 'createcd', '-i', 'test.cue', '-o', output], cwd=work, check=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--chdman', default='chdman')
    args = parser.parse_args()
    make_disc(args.output, args.chdman)
