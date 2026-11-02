#!/usr/bin/env python3
"""Compare retained seek records with the supplied IRIX 6.5.22m reference."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import tarfile

ROOT = Path(__file__).resolve().parent.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def files(path):
    with tarfile.open(path) as archive:
        return {Path(m.name).name: archive.extractfile(m).read()
                for m in archive.getmembers() if m.isfile()}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('lp64', type=Path)
    p.add_argument('o32', type=Path)
    p.add_argument('--reference', type=Path,
                   default=ROOT/'.work/irix-reference/filetype-runs/ci-sjhhb4l0')
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    reference = a.reference/'seek-final-results.tar'
    expected = files(reference)
    identity = json.loads((a.reference/'result.json').read_text())
    assert identity['clean_shutdown'] and '6.5 6.5.22m' in identity['identity']
    statuses = json.loads((a.reference/'response-final.json').read_text())['output']
    assert len(statuses.splitlines()) == 8
    assert all(line.endswith(' 0') for line in statuses.splitlines())
    runs = []
    for directory, count, pin_name in [(a.lp64, 8, 'baseline.json'),
                                       (a.o32, 4, 'o32-baseline.json')]:
        r = json.loads((directory/'result.json').read_text())
        assert r['status'] == 'observed' and r['clean_shutdown']
        pin = json.loads((ROOT/'lab/irix-filetypes'/pin_name).read_text())
        assert sha(directory/'media/netbsd') == pin['native_kernel_sha256']
        observed = files(directory/'seek-results.tgz')
        cases = []
        for name, data in sorted(observed.items()):
            if not name.endswith(('-lseek-0.out', '-lseek-1234.out')):
                continue
            assert len(data) == 1536 and data == expected[name], name
            words = struct.unpack('>384I', data)
            uid = int(name.removesuffix('.out').rsplit('-', 1)[1])
            assert words[0] == 1024 and words[4] == uid
            assert words[8] == 1047 and words[12] == uid
            assert all(word == 0 for word in words[29*8:])
            binary = name.rsplit('-', 1)[0]
            assert (directory/'media'/binary).read_bytes() == expected[binary]
            cases.append(dict(name=name, sha256=hashlib.sha256(data).hexdigest(),
                              syscall_records=29))
        assert len(cases) == count
        if count == 8:
            wide = json.loads((a.reference/'response-wide.json').read_text())['output']
            assert observed['wide.out'].decode() == wide
            assert (directory/'media/wide-n32').read_bytes() == (a.reference/'wide-n32').read_bytes()
        runs.append(dict(directory=str(directory), pin=pin, cases=cases,
                         result_sha256=sha(directory/'result.json'),
                         archive_sha256=sha(directory/'seek-results.tgz'),
                         serial_sha256=sha(directory/'serial.log'), clean_shutdown=True))
    report = dict(schema=1, status='passed', executions=12, syscall_records=348,
                  reference_directory=str(a.reference), reference_sha256=sha(reference),
                  reference_identity=identity['identity'], reference_clean_shutdown=True,
                  wide_n32_sha256=sha(a.reference/'wide-n32'),
                  wide_n32_output=wide, runs=runs,
                  sources={str(path.relative_to(ROOT)):sha(path) for path in
                           [Path(__file__), ROOT/'lab/irix-lseek/probe.c',
                            ROOT/'lab/irix-lseek/wide.c']})
    a.output.write_text(json.dumps(report, indent=2)+'\n')
    print('Passed 12 executions / 348 raw syscall observations and the n32 wide-offset probe')


if __name__ == '__main__':
    main()
