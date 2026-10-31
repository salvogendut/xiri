#!/usr/bin/env python3
"""Check winterm's fork/child-exec boundary in both emulator modes."""
import argparse
import collections
import hashlib
import importlib.util
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location('tcp', ROOT/'scripts/probe-irix-tcp.py')
TCP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TCP)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def events(text):
    result, pending = [], {}
    # Installed o32 kdump warns on LP64 PSIG payloads and omits the newline
    # after SIG_DFL. Recover the following record boundary, without interpreting
    # that signal payload. The complete binary trace stays on the guest disk.
    text = re.sub(r'(^[^\n]* PSIG[^\n]* SIG_DFL)(?=[ \t]+\d+[ \t]+\d+[ \t]+\S+[ \t]+[A-Z]+)',
                  r'\1\n', text, flags=re.M)
    for block in re.split(r'(?=^[ \t]*\d+\s+\d+\s+\S+\s+[A-Z]+)', text, flags=re.M):
        match = re.match(r'^\s*(\d+)\s+\d+\s+\S+\s+MISC\s+(irix_o32|irix_ret):', block)
        if match:
            pid = int(match[1])
            raw = TCP.trace_records(block, match[2], True)
            assert len(raw) == 1
            fields = {k: int(v, 0) for k, v in re.findall(r'(syscall|pc|v0|a[0-3])=(0x[0-9a-f]+|\d+)', raw[0])}
            if match[2] == 'irix_o32':
                entry = dict(pid=pid, call=fields, ret=None, paths=[])
                result.append(entry)
                pending[pid] = entry
            else:
                assert pid in pending, ('return without captured call', block)
                entry = pending.pop(pid)
                number = entry['call']['syscall']
                assert fields['syscall'] == (entry['call']['a0'] if number == 1000 else number)
                entry['ret'] = fields
        else:
            match = re.match(r'^\s*(\d+)\s+\d+\s+\S+\s+NAMI\s+"([^"]+)"', block)
            if match and int(match[1]) in pending:
                pending[int(match[1])]['paths'].append(match[2])
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('runs', nargs=2, type=Path)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    pin = json.loads((ROOT/'lab/irix-process/baseline.json').read_text())
    report = dict(schema=1, status='window-rendered-child-exec-blocked', pin=pin, runs=[],
                  window_rendering_observed=True,
                  native_shell_input_qualified=False,
                  signal_trace_limitation='Installed o32 kdump cannot decode LP64 PSIG payloads; only record boundaries are recovered. Signal delivery is unqualified.',
                  next_priority='Native exec/session/descriptor setup, signal handlers and terminal attributes before 4Dwm')
    modes = set()
    for directory in a.runs:
        r = json.loads((directory/'result.json').read_text())
        assert r['status'] == 'observed' and r['clean_shutdown'] and r['native_x11_after'] and r['pin'] == pin
        assert r['mode'] not in modes
        modes.add(r['mode'])
        for path, digest in r['sources'].items():
            assert sha(ROOT/path) == digest, path
        for key in ['controls', 'native_font_controls']:
            assert len(r[key]) == 2 and {c['phase'] for c in r[key]} == {'before', 'after'}
            for c in r[key]:
                assert 'Map State: IsViewable' in c['window'] and not c['stderr']
                if key == 'controls':
                    assert c['guards_intact'] and c['entry_exit'] == 37
        for key in ['group_controls', 'native_pty_controls']:
            assert len(r[key]) == 4 and {(c['phase'], c['uid']) for c in r[key]} == {
                (phase, uid) for phase in ['before', 'after'] for uid in [0, 1234]}
            for c in r[key]:
                obs = c['actual']
                assert obs['errno_bytes'] == obs['errno'] == obs['exit'] == obs['signal'] == obs['killed'] == 0 and not obs['stderr']
                if key == 'group_controls':
                    assert c['group_absent'] and obs['stdout'] == 'XIRI_GROUP_CONTROL\n'
                else:
                    assert 'NATIVE_PTY_PASS' in obs['stdout']
        assert len(r['cases']) == 4 and {(c['uid'], c['font']) for c in r['cases']} == {
            (uid, font) for uid in [0, 1234] for font in [None, 'fixed']}
        cases = []
        for c in r['cases']:
            assert c['group_absent'] and 'fault' not in c
            assert '"winterm": ("winterm" "XWsh")' in c['tree']
            assert ('503x520' if c['font'] == 'fixed' else '983x840') in c['tree']
            assert c['actual'] == dict(errno_bytes=0, errno=0, exit=-1, signal=9, killed=1, stdout='',
                stderr="/emul/irix/usr/sbin/xwsh: Function not implemented: can't start command\n")
            path = directory/(c['name']+'.kdump')
            text = path.read_text()
            assert c['trace_scope'] == 'first 2000 parent events, all other processes and all signals'
            full_hashes = dict(re.findall(r'^SHA256 \((winterm\.(?:ktrace|dump))\) = ([0-9a-f]{64})$', c['trace_info'], re.M))
            assert set(full_hashes) == {'winterm.ktrace', 'winterm.dump'}
            line_counts = {name: int(count) for count, name in re.findall(r'^\s*(\d+) (winterm\.(?:dump|capture))$', c['trace_info'], re.M)}
            assert set(line_counts) == {'winterm.dump', 'winterm.capture'}
            assert line_counts['winterm.dump'] >= line_counts['winterm.capture'] == text.count('\n') > 0
            ev = events(text)
            forks = [e for e in ev if e['call']['syscall'] == 1002]
            assert len(forks) == 1 and forks[0]['ret'] and forks[0]['ret']['a3'] == 0
            parent, child = forks[0]['pid'], forks[0]['ret']['v0']
            assert child > 0 and child != parent
            children = [e for e in ev if e['pid'] == child]
            assert children
            masks = [e for e in ev if e['call']['syscall'] == 1164]
            assert masks and all(e['ret'] is None or (e['ret']['v0'] == e['ret']['a3'] == 0) for e in masks)
            slave = [e for e in children if e['call']['syscall'] == 1005 and any('/dev/tty' in p for p in e['paths'])]
            assert len(slave) == 1 and slave[0]['ret'] and slave[0]['ret']['a3'] == 0
            execs = [e for e in children if e['call']['syscall'] == 1059]
            assert len(execs) == 1 and execs[0]['ret']['v0'] == 89 and execs[0]['ret']['a3'] == 1
            exits = [e for e in children if e['call']['syscall'] == 1001]
            assert len(exits) == 1 and exits[0]['call']['a0'] == 0xffffffff
            unsupported = collections.Counter(str(e['call']['syscall']) for e in children
                if e['ret'] and e['ret']['a3'] == 1 and e['ret']['v0'] == 89)
            assert sha(directory/(c['name']+'.xwd')) == c['frame_sha256']
            cases.append(dict(name=c['name'], uid=c['uid'], font=c['font'], actual=c['actual'],
                group_absent=True, parent_pid=parent, child_pid=child, fork=forks[0], slave_open=slave[0],
                child_exec=execs[0], child_exit=exits[0], child_unsupported=dict(unsupported),
                child_events=children, tree=c['tree'], trace_scope=c['trace_scope'], trace_info=c['trace_info'],
                full_trace_hashes=full_hashes, trace_line_counts=line_counts,
                trace_sha256=sha(path), frame_sha256=c['frame_sha256']))
        report['runs'].append(dict(directory=str(directory), mode=r['mode'], clean_shutdown=True,
            result_sha256=sha(directory/'result.json'), sources=r['sources'], cases=cases,
            controls=r['controls'], native_font_controls=r['native_font_controls'],
            native_pty_controls=r['native_pty_controls'], group_controls=r['group_controls']))
    assert modes == {'ci', 'ordinary'}
    ci = next(r for r in report['runs'] if r['mode'] == 'ci')
    frame = Path(ci['directory'])/'0-default.xwd'
    png = ROOT/'docs/results/images/2026-11-01-irix-winterm-window.png'
    pixels = lambda path: subprocess.check_output(['magick', str(path), '-depth', '8', 'rgba:-'])
    assert pixels(frame) == pixels(png)
    report['screenshot'] = dict(path=str(png.relative_to(ROOT)), sha256=sha(png),
        source_frame=str(frame), source_frame_sha256=sha(frame),
        description='Three-second default xwsh window, clipped by the 640x480 viewport; no shell prompt')
    report['qualifier_sha256'] = sha(Path(__file__))
    a.output.write_text(json.dumps(report, indent=2)+'\n')
    print('Eight xwsh starts forked, opened the slave and reached unsupported child exec')


if __name__ == '__main__':
    main()
