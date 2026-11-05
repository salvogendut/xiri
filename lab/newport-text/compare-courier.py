#!/usr/bin/env python3
"""Compare unpacked Latin-1 PCF glyphs without depending on file metadata."""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import PcfFontFile, __version__ as pillow_version


class LatinPCF(PcfFontFile.PcfFontFile):
    def _load_encoding(self):
        # Pillow's decoder indexes from zero even when first_col is 32.
        # These fonts use one Latin-1 row; retain its actual character codes.
        stream, _, u16, _ = self._getformat(PcfFontFile.PCF_BDF_ENCODINGS)
        first, last, row0, row1, _ = [u16(stream.read(2)) for _ in range(5)]
        if row0 != 0 or row1 != 0 or not 0 <= first <= last <= 255:
            raise ValueError('expected a single Latin-1 PCF encoding row')
        indices = [u16(stream.read(2)) for _ in range(last-first+1)]
        return [indices[c-first] if first <= c <= last and indices[c-first] != 65535
                else None for c in range(256)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('native', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    with args.reference.open('rb') as source:
        reference = LatinPCF(source)
    with args.native.open('rb') as source:
        native = LatinPCF(source)
    report = dict(pillow_version=pillow_version,
        source_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in (args.reference, args.native)},
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        reference_glyphs=sum(g is not None for g in reference.glyph),
        native_glyphs=sum(g is not None for g in native.glyph),
        matched=[], different=[], native_only=[], reference_only=[])
    for code, (a, b) in enumerate(zip(reference.glyph, native.glyph)):
        if a is None and b is None:
            continue
        if a is None:
            report['native_only'].append(code)
        elif b is None:
            report['reference_only'].append(code)
        elif a[:3] == b[:3] and a[3].tobytes() == b[3].tobytes():
            report['matched'].append(code)
        else:
            report['different'].append(code)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: len(v) if isinstance(v, list) else v
                     for k, v in report.items() if k != 'source_sha256'}, indent=2))


if __name__ == '__main__':
    main()
