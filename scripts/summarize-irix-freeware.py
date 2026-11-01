#!/usr/bin/env python3
"""Validate retained read-only metadata and summarize the supplied CD sets."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / '.work/irix-freeware'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    metadata = json.loads((WORK / 'metadata.json').read_text())
    for path, info in metadata.items():
        local = WORK / 'metadata' / path.lstrip('/')
        assert local.stat().st_size == info['bytes'] and sha(local) == info['sha256']
    packages, zero = [], []
    for path in sorted(p for p in metadata if p.endswith('.idb')):
        descriptor = path[:-4]
        assert descriptor in metadata
        item = dict(name=Path(descriptor).name, cd=int(path.split('/')[2][3:]),
                    descriptor=metadata[descriptor], inventory=metadata[path])
        for p in [descriptor, path]:
            data = (WORK / 'metadata' / p.lstrip('/')).read_bytes()
            if data and not any(data):
                zero.append(p)
        content = (WORK / 'metadata' / path.lstrip('/')).read_bytes()
        item['catalog_registration_hook'] = b'iconcatalogedit' in content
        item['zero_filled_metadata'] = descriptor in zero or path in zero
        packages.append(item)
    counts = {str(cd): sum(p['cd'] == cd for p in packages) for cd in range(1, 5)}
    assert counts == {'1': 129, '2': 79, '3': 140, '4': 144}
    assert len({p['name'] for p in packages}) == 489
    raw = json.loads((WORK / 'media/freeware.raw.json').read_text())
    assert raw['bytes'] == (WORK / 'media/freeware.raw').stat().st_size == 100663296000
    chd_hashes = [line.split()[0] for line in (WORK / 'chd.sha256').read_text().splitlines()]
    assert chd_hashes == ['6da9a2efe74eccedf4ba1a75e21849099e650460b75f14bac635f8409d19edb8'] * 2
    report = dict(schema=1, status='read-only-inventory', runtime_qualification=False,
        media=dict(filename='irix-sgi-freeware-cdroms.chd', bytes=8577503232,
                   sha256=chd_hashes[0], format='uncompressed CHD v5 hard disk',
                   raw_conversion=raw, filesystem='XFS', partition='/dev/sda1',
                   partition_offset_bytes=136314880, mount_options='ro,norecovery',
                   overlays_inspected=False),
        release='SGI Freeware, May 2004', release_evidence='/cds/cd-1/dist/inst.README',
        paths=3597, metadata_files=len(metadata), package_records=len(packages),
        unique_packages=489, packages_per_cd=counts,
        catalog_hook_package_records=sum(p['catalog_registration_hook'] for p in packages),
        zero_filled_metadata=zero, selected_package='fw_xmahjongg', selected_version='3.6.1',
        selected_catalog_page='Freeware', packages=packages,
        evidence_sha256={str(p.relative_to(ROOT)): sha(p) for p in [
            WORK / 'metadata.json', WORK / 'media-paths.txt', WORK / 'extract.log',
            WORK / 'sparse-stream.py', WORK / 'download-metadata.py',
            WORK / 'inspect-media.py', WORK / 'inspect-installed.py',
            ROOT / '.work/target-netbsd64/release/chd-extract']},
        summarizer_sha256=sha(Path(__file__)),
        limitations=['Inventory only: package payloads are not fully validated or installed.',
                    'Four metadata files read as all-zero; exclude ncurses and nedit pending investigation.',
                    'Prismatic overlays and the secondary XFS partition were not inspected.'])
    output = ROOT / 'docs/results/2026-11-01-irix-freeware.json'
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(f'{len(packages)} package records, 489 unique; {len(zero)} zero-filled metadata files')


if __name__ == '__main__':
    main()
