#!/usr/bin/env python3
"""Verify reproduced desktop startup blockers, without claiming desktop success."""
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
    parser.add_argument('runs', nargs=2, type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    manifest_path = ROOT / 'lab/irix-desktop-components/manifest.json'
    manifest = json.loads(manifest_path.read_text())
    pin = json.loads((ROOT / 'lab/irix-prda/baseline.json').read_text())
    assert len(manifest['files']) == 38 and len(manifest['resources']) == 16
    assert not manifest['unresolved']
    assert sha(ROOT / 'scripts/inventory-irix-desktop-components.py') == manifest['script_sha256']
    assert sha(ROOT / 'scripts/inventory-irix-desktop.py') == manifest['elf_parser_sha256']
    report = dict(schema=1, status='startup-blockers-reproduced',
                  desktop_success=False, qualifier_sha256=sha(Path(__file__)),
                  trace_decoder_sha256=sha(ROOT / 'scripts/probe-irix-tcp.py'),
                  manifest_sha256=sha(manifest_path), pin=pin, runs=[])
    # Bind the public NetBSD sources used to interpret the observations to
    # their historical commits, independently of the current fork checkout.
    report['source_evidence'] = []
    for revision, paths in [
        (pin['source_revision'], ['sys/compat/irix_o32/irix_o32.c',
                                 'sys/compat/irix_o32/irix_errno.h']),
        ('5aca2679d78276864d2980a08314887b2058fb2c', [
            'sys/compat/irix/irix_resource.h', 'sys/compat/irix/irix_resource.c',
            'sys/compat/irix/irix_syscall.h']),
    ]:
        for path in paths:
            content = subprocess.check_output(['git', '-C', str(ROOT.parent / 'NetBSD-nixbench'),
                                               'show', revision + ':' + path])
            report['source_evidence'].append(dict(repository='NetBSD-xiri',
                revision=revision, path=path, sha256=hashlib.sha256(content).hexdigest()))
    modes = set()
    for directory in args.runs:
        result = json.loads((directory / 'result.json').read_text())
        assert result['status'] == 'observed' and result['clean_shutdown']
        assert result['native_x11_after'] and result['pin'] == pin
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
        assert shell_passed
        window_passed = ('WMCHECK_STATUS=0\n' in baseline['wmcheck'] and
                         'WM_CHECK passed\n' in baseline['wmcheck'])
        assert baseline['passed'] == (window_passed and shell_passed)
        # A failed native focus check remains a failure in this observation
        # record. These runs are not added to the earlier successful matrix.
        if not window_passed:
            assert 'WMCHECK_STATUS=5\n' in baseline['wmcheck']
            assert 'matched=0\n' in baseline['wmcheck']
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
            calls = list(map(fields, tcp.trace_records(raw, 'irix_o32', True)))
            returns = list(map(fields, tcp.trace_records(raw, 'irix_ret', True)))
            observation = dict(component)
            if component['name'] == 'bgicons':
                assert component['exit_status'] == '2' and not calls
                assert 'Cannot execute ELF binary /emul/irix/usr/sbin/bgicons\n' in component['stderr']
                data = manifest['files']['/usr/sbin/bgicons']['loads'][1]
                assert data['alignment'] == 4096 < pin['page_bytes']
                assert data['address'] % pin['page_bytes'] == data['offset'] % pin['page_bytes'] == 0
                observation['boundary'] = 'exec rejection; ELF data p_align below current executable validator minimum'
                observation['data_segment'] = data
                observation['errno_captured'] = False
            else:
                assert component['exit_status'] == '139' and not component['stdout']
                assert component['stderr'] == "PANIC pt_bootstrap() Couldn't get initial rlimits - {0x0, 0x0}\n"
                assert calls[-2]['syscall'] == 1148 and calls[-2]['a0'] == 8
                assert returns[-2] == dict(syscall=1148, v0=89, a3=1)
                assert calls[-1]['syscall'] == 1004 and calls[-1]['a0'] == 2
                assert returns[-1] == dict(syscall=1004, v0=63, a3=0)
                assert 'PSIG  SIGSEGV SIG_DFL' in raw
                assert 'NAMI  "/emul/irix/usr/lib32/libpthread.so"' in raw
                observation['boundary'] = 'getrlimit(RLIMIT_PTHREAD) returns IRIX ENOSYS before pthread bootstrap panic and SIGSEGV'
                observation['last_calls'] = calls[-3:]
                observation['last_returns'] = returns[-3:]
            components.append(observation)
        report['runs'].append(dict(directory=str(directory), mode=result['mode'],
            result_sha256=sha(directory / 'result.json'), serial_sha256=sha(directory / 'serial.log'),
            config_sha256=sha(config_path), emulator_command_sha256=sha(command_path),
            sources=result['sources'], staged=result['staged'], seed=result['seed'],
            seed_result_sha256=result['seed_result_sha256'], components=components,
            window_check=baseline['wmcheck'], window_check_passed=window_passed,
            shell_handoff=baseline['handoff'], shell_marker=baseline['marker'],
            shell_check_passed=shell_passed, controls=result['controls'], guard=guard,
            native_x11_after=True, clean_shutdown=True, frame_sha256=result['frame_sha256'],
            guest_trace_info=result['trace_info']))
    assert modes == {'ci', 'ordinary'}
    report['limits'] = [
        'No new desktop component reaches a usable window; full desktop remains unqualified.',
        'Any failed baseline window check is retained separately from successful shell input.',
        'Per-PID captures contain first/last 4000 lines, with overlap for short traces; they are not event counts.',
        'bgicons errno was not recorded; the shell rejection and the incompatible ELF header are separate evidence.',
        'fmserv is staged as a dependency candidate, not directly exercised.',
        'Static closure excludes delayed modules; artwork, filetype rules, catalog pages and services remain unqualified.',
        'Session saving is disabled; no new signal/thread, normal-exit, Newport or physical-hardware claims.',
    ]
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print('Desktop startup blockers reproduced in both modes; full desktop remains unqualified')


if __name__ == '__main__':
    main()
