#!/usr/bin/env python3
"""Write the native reader's plan from a verified workstation import ledger."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from xiri_lab import sha256
from xiri_lab.irix_import import PREFIX, resolve_link, validate_parents


def plan(ledger, profile):
    if ledger['status'] != 'payload-verified' or ledger['profile_sha256'] != sha256(profile):
        raise ValueError('expected a verified import of the matching profile')
    files = ledger['files']
    defaults = json.loads(profile.read_text())['default_components']
    selected = {p for p, row in files.items() if row['component'] in defaults}
    required = {}
    for dependency in ledger['dependencies']:
        required.setdefault(dependency['source'], []).append(dependency['selected'])
    queue = sorted(selected)
    for p in queue:
        row = files[p]
        needs = list(required.get(row['source'], []))
        for field in ('interpreter', 'canonical_path'):
            if field in row and p.startswith(PREFIX + '/'):
                needs.append(row[field])
        needs.extend(row.get('elf', {}).get('interpreter', []))
        for name in needs:
            dest = PREFIX + name
            if dest not in selected:
                selected.add(dest)
                queue.append(dest)
    rows = {p: files[p] for p in selected}
    saver = json.loads((profile.parent / f"irix-{ledger['release']}-xlock-savers-v1.json").read_text())
    if saver['release'] != ledger['release'] or saver['donor'] != ledger['donor']:
        raise ValueError('Screen Saver and desktop donors differ')
    for name, entry in saver['paths'].items():
        dest = PREFIX + name
        if dest in rows and rows[dest]['sha256'] != entry['sha256']:
            raise ValueError('Screen Saver digest mismatch: ' + name)
        mode = '0444' if '/savers/defaults/' in name else '0555'
        rows[dest] = dict(entry, source=name, mode=mode)
    validate_parents(rows)
    for p, row in sorted(rows.items()):
        kind = row['type']
        if kind == 'symlink' and '/iconcatalog/pages/' in p:
            target = resolve_link(row['source'], row['target'])
            if PREFIX + target not in rows:
                continue
        source = row['source']
        dest = '' if p == PREFIX + source else p
        value = row.get('sha256', row.get('target', ''))
        fields = [kind[0], row['mode'], source, dest, value]
        if any('|' in v or '\n' in v or '\r' in v for v in fields):
            raise ValueError(f'unrepresentable path in {p}')
        yield '|'.join(fields)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    args = parser.parse_args()
    ledger = json.loads(args.manifest.read_text())
    print('\n'.join(plan(ledger, ROOT / 'profiles' / (ledger['profile'] + '.json'))))
