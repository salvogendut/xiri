#!/usr/bin/env python3
"""Verify pthread initialization and subsequent desktop session-directory failures."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import tomllib

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('tcp', ROOT / 'scripts/probe-irix-tcp.py')
tcp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tcp)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fields(record):
    return {k: int(v, 0) for k, v in re.findall(r'(\w+)=(0x[0-9a-f]+|\d+)', record)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runs', nargs='+', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--png', type=Path, required=True)
    args = parser.parse_args()
    manifest_path = ROOT / 'lab/irix-desktop-components/manifest.json'
    manifest = json.loads(manifest_path.read_text())
    pin = json.loads((ROOT / 'lab/irix-init-threads/baseline.json').read_text())
    assert len(manifest['files']) == 38 and len(manifest['resources']) == 16
    assert not manifest['unresolved']
    assert sha(ROOT / 'scripts/inventory-irix-desktop-components.py') == manifest['script_sha256']
    assert sha(ROOT / 'scripts/inventory-irix-desktop.py') == manifest['elf_parser_sha256']
    report = dict(schema=1, status='initialization-cleared-session-directory-boundary',
                  desktop_success=False, qualifier_sha256=sha(Path(__file__)),
                  trace_decoder_sha256=sha(ROOT / 'scripts/probe-irix-tcp.py'),
                  manifest_sha256=sha(manifest_path), pin=pin, runs=[])
    # Bind the public NetBSD sources used to interpret the observations to
    # their historical commits, independently of the current fork checkout.
    report['source_evidence'] = []
    for revision, paths in [
        (pin['source_revision'], ['sys/compat/irix_o32/irix_o32.c',
                                 'sys/compat/irix_o32/irix_errno.h', 'sys/sys/proc.h',
                                 'sys/kern/kern_lwp.c', 'sys/kern/kern_sig.c']),
        ('5aca2679d78276864d2980a08314887b2058fb2c', [
            'sys/compat/irix/irix_resource.h', 'sys/compat/irix/irix_resource.c',
            'sys/compat/irix/irix_syscall.h', 'sys/compat/irix/irix_mman.h',
            'sys/compat/irix/irix_prctl.h']),
    ]:
        for path in paths:
            content = subprocess.check_output(['git', '-C', str(ROOT.parent / 'NetBSD-nixbench'),
                                               'show', revision + ':' + path])
            report['source_evidence'].append(dict(repository='NetBSD-xiri',
                revision=revision, path=path, sha256=hashlib.sha256(content).hexdigest()))
    modes = set()
    for directory in args.runs:
        run_pin = pin
        result = json.loads((directory / 'result.json').read_text())
        assert result['status'] == 'observed' and result['clean_shutdown']
        assert result['native_x11_after'] and result['pin'] == run_pin
        assert not result['diagnostic_baseline']
        assert result['manifest_sha256'] == sha(manifest_path)
        modes.add(result['mode'])
        config_path = directory / 'iris.toml'
        config = tomllib.loads(config_path.read_text())
        assert config['ci'] == (result['mode'] == 'ci')
        assert config['headless'] is False
        assert config['graphics']['board'] == 'newport'
        command_path = directory / 'emulator-command.json'
        command = json.loads(command_path.read_text())
        assert ('xvfb-run' in command) == (result['mode'] == 'ordinary')
        for path, digest in result['sources'].items():
            assert sha(ROOT / path) == digest, path
        seed = ROOT / result['seed'] / 'result.json'
        assert sha(seed) == result['seed_result_sha256']
        expected_staged = json.loads(seed.read_text())['staged']
        for path, info in {**manifest['files'], **manifest['resources']}.items():
            expected_staged['/emul/irix' + path] = info['sha256']
        assert result['staged'] == expected_staged
        assert len(result['controls']) == 2
        assert {c['phase'] for c in result['controls']} == {'before', 'after'}
        for control in result['controls']:
            assert control['actual'] == dict(errno_bytes=0, errno=0, exit=37,
                signal=0, killed=0, stdout='XIRI_ABI_PROBE\n', stderr='')
        guard = result['guard']
        assert guard['exit'] == -1 and guard['signal'] == 9
        assert guard['killed'] == guard['absent'] == guard['valid'] == 1
        assert guard['elapsed_ms'] >= 120000
        baseline = result['baseline']
        shell_passed = ('TYPE_STATUS=0\n' in baseline['typing'] and
                        baseline['marker'] == 'XIRI_DESKTOP_COMPONENTS_SHELL_OK\n')
        handoff = dict(re.findall(r'(\w+)=(\S+)', baseline['handoff']))
        assert all(handoff[k] == '1234' for k in ['uid', 'euid', 'gid', 'egid'])
        assert handoff['pid'] == handoff['sid'] == handoff['pgid'] == handoff['tpgid']
        assert handoff['groups'] == '0' and handoff['tty'].startswith('/dev/pts/')
        if shell_passed:
            assert baseline['marker_owner'] == '1234' and 'viewable=1' in baseline['type_output']
        else:
            assert 'TYPE_STATUS=5\n' in baseline['typing']
            assert not baseline['marker'] and not baseline['marker_owner']
            assert baseline['type_output'] == 'terminal not viewable at usable geometry\n'
            assert '983x72' in baseline['before_tree']
        assert handoff['rows'] == '24' and handoff['cols'] == '80'
        window_passed = ('WMCHECK_STATUS=0\n' in baseline['wmcheck'] and
                         'WM_CHECK passed\n' in baseline['wmcheck'])
        assert baseline['passed'] == (window_passed and shell_passed)
        attempts = [fields(line) for line in baseline['wmcheck'].splitlines()
                    if line.startswith('WM_FOCUS_ATTEMPT ')]
        assert attempts and len(attempts) <= 20
        assert [item['n'] for item in attempts] == list(range(len(attempts)))
        if window_passed:
            assert attempts[-1]['matched'] == 1
            assert 'WM_KEY delivered=1\n' in baseline['wmcheck']
            drag = re.search(r'WM_DRAG dx=(-?\d+) dy=(-?\d+)', baseline['wmcheck'])
            assert drag and abs(int(drag[1])-50) <= 3 and abs(int(drag[2])-30) <= 3
        else:
            # Preserve an unsuccessful interaction check as a failure.
            assert 'WMCHECK_STATUS=5\n' in baseline['wmcheck']
            assert len(attempts) == 20 and all(a['matched'] == 0 for a in attempts)
        assert '"Toolchest":' in result['tree'] and '"winterm":' in result['tree']
        assert sha(directory / 'desktop.xwd') == result['frame_sha256']
        assert result['tree'] == (directory / 'desktop.tree').read_text()
        assert result['processes_before_cleanup'] == (directory / 'desktop.ps').read_text()
        components = []
        assert [c['name'] for c in result['components']] == [
            'bgicons', 'fm-background', 'iconcatalog', 'fm-home']
        for component in result['components']:
            trace = directory / (component['name'] + '.kdump')
            assert sha(trace) == component['trace_sha256']
            raw = trace.read_text()
            # Decode ordered events, not separately zipped call/return lists.
            # Head/tail captures overlap and can start/end inside a record.
            events = []
            dropped = []
            for match in re.finditer(r'MISC\s+(irix_o32|irix_ret):\n(?:(?:\t| {8})[^\n]*\n)+', raw):
                try:
                    values = fields(tcp.trace_records(match[0], match[1], True)[0])
                except RuntimeError:
                    line = raw[:match.start()].count('\n') + 1
                    assert line <= 4000 <= line + match[0].count('\n') or match.end() == len(raw)
                    dropped.append(line)
                    events.append((None, {}))
                    continue
                events.append((match[1], values))
            pending = None
            pairs = []
            for kind, values in events:
                if kind == 'irix_o32':
                    pending = values
                elif kind == 'irix_ret' and pending and pending['syscall'] == values['syscall']:
                    pairs.append(dict(call=pending, result=values))
                    pending = None
                else:
                    pending = None
            initializations = [p for p in pairs if p['call']['syscall'] == 1130 and p['call']['a0'] == 20]
            assert initializations and all(p['result'] == dict(syscall=1130, v0=0, a3=0) for p in initializations)
            mkdir = [p for p in pairs if p['call']['syscall'] == 1080]
            assert mkdir and all(p['call']['a1'] == 0o755 and p['result'] == dict(syscall=1080, v0=89, a3=1) for p in mkdir)
            assert 'NAMI  "/tmp/xiri-home/.desktop-xiri-indy"' in raw
            assert 'NAMI  "/emul/irix/usr/lib32/libpthread.so"' in raw
            assert 'PSIG  SIGSEGV' not in raw and not component['stdout']
            waits = [p for p in pairs if p['call']['syscall'] == 1170]
            if component['name'] == 'bgicons':
                assert component['exit_status'] == '1' and component['stderr'] == 'Function not implemented\n'
            elif component['name'].startswith('fm-'):
                assert component['exit_status'] == '255' and not component['stderr']
                assert waits and all(p['call']['a3'] == 3 and p['result'] == dict(syscall=1170, v0=22, a3=1) for p in waits)
            else:
                assert not component['exit_status'] and not component['stderr']
                assert '"fatalErrorDialog_popup" "IconCatalog"' in result['tree']
            observation = dict(component, initialization_passed=True,
                initializations=initializations, mkdir=mkdir, waits=waits,
                truncated_record_lines=dropped, last_complete_pairs=pairs[-7:],
                boundary='mkdir ENOSYS; Icon Catalog session-directory error; fm waitsys(options=3) EINVAL')
            components.append(observation)
        report['runs'].append(dict(
            directory=str(directory), mode=result['mode'], pin=run_pin,
            result_sha256=sha(directory / 'result.json'), serial_sha256=sha(directory / 'serial.log'),
            config_sha256=sha(config_path), emulator_command_sha256=sha(command_path),
            sources=result['sources'], staged=result['staged'], seed=result['seed'],
            seed_result_sha256=result['seed_result_sha256'], components=components,
            window_check=baseline['wmcheck'], window_check_passed=window_passed,
            focus_attempts=attempts, marker_owner=baseline['marker_owner'],
            type_output=baseline['type_output'],
            shell_handoff=baseline['handoff'], shell_marker=baseline['marker'],
            shell_check_passed=shell_passed, controls=result['controls'], guard=guard,
            native_x11_after=True, clean_shutdown=True, frame_sha256=result['frame_sha256'],
            guest_trace_info=result['trace_info']))
    assert modes == {'ci', 'ordinary'}
    assert any(r['shell_check_passed'] and r['mode'] == 'ci' for r in report['runs'])
    frame = args.runs[0] / 'desktop.xwd'
    args.png.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['magick', str(frame), str(args.png)], check=True)
    pixels = lambda path: subprocess.check_output(['magick', str(path), '-depth', '8', 'rgba:-'])
    original = pixels(frame)
    assert len(original) == 1024 * 768 * 4 and pixels(args.png) == original
    report['screenshot'] = dict(path=str(args.png), sha256=sha(args.png),
        source=str(frame), pixels_match_xwd=True,
        kind='diagnostic: Icon Catalog session-directory fatal dialog')
    report['limits'] = [
        'No new desktop component is usable; a rendered fatal dialog is not desktop success.',
        'Failed shell geometry checks remain failures; successful retries do not qualify startup repeatability.',
        'Per-PID captures contain first/last 4000 lines, overlap, and may truncate records; lists are observations, not event counts.',
        'mkdir failure is observed; child traces and the complete dependency chain after fixing it remain open.',
        'fm waitsys(options=3) returns EINVAL; no claim that this is the sole reason its parent exits.',
        'fmserv, artwork, filetype rules, catalog pages and delayed services remain unqualified.',
        'Session saving is disabled; no general pthread, normal-exit, Newport or physical-hardware claims.',
    ]
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print('Pthread initialization cleared; shell checks:', [r['shell_check_passed'] for r in report['runs']], '; full desktop still blocked')


if __name__ == '__main__':
    main()
