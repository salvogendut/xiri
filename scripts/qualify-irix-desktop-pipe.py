#!/usr/bin/env python3
"""Verify desktop observations after native pipe support."""
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
    parser.add_argument('--failed-ci', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--png', type=Path, required=True)
    args = parser.parse_args()
    manifest_path = ROOT / 'lab/irix-desktop-components/manifest.json'
    manifest = json.loads(manifest_path.read_text())
    pin = json.loads((ROOT / 'lab/irix-pipe/baseline.json').read_text())
    assert len(manifest['files']) == 38 and len(manifest['resources']) == 16
    assert not manifest['unresolved']
    assert sha(ROOT / 'scripts/inventory-irix-desktop-components.py') == manifest['script_sha256']
    assert sha(ROOT / 'scripts/inventory-irix-desktop.py') == manifest['elf_parser_sha256']
    report = dict(schema=1, status='file-manager-window-select-error',
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
            'sys/compat/irix/irix_prctl.h', 'sys/compat/irix/syscalls.master']),
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
        control = result['guard_control']
        assert control['exit'] == 37
        assert all(control[k] == 0 for k in ['signal', 'killed'])
        assert control['absent'] == control['valid'] == 1
        assert control['stdout'] == 'XIRI_ABI_PROBE\n' and not control['stderr']
        guard = result['guard']
        assert guard['exit'] == -1 and guard['signal'] == 9
        assert guard['killed'] == guard['absent'] == guard['valid'] == 1
        assert guard['elapsed_ms'] >= 180000
        baseline = result['baseline']
        shell_passed = ('TYPE_STATUS=0\n' in baseline['typing'] and
                        baseline['marker'] == 'XIRI_DESKTOP_COMPONENTS_SHELL_OK\n')
        handoff = dict(re.findall(r'(\w+)=(\S+)', baseline['handoff']))
        if handoff:
            assert all(handoff[k] == '1234' for k in ['uid', 'euid', 'gid', 'egid'])
            assert handoff['pid'] == handoff['sid'] == handoff['pgid'] == handoff['tpgid']
            assert handoff['groups'] == '0' and handoff['tty'].startswith('/dev/pts/')
            assert handoff['rows'] == '24' and handoff['cols'] == '80'
        if shell_passed:
            assert handoff and baseline['marker_owner'] == '1234' and 'viewable=1' in baseline['type_output']
            assert '"winterm":' in result['tree']
        else:
            assert not baseline['marker'] and not baseline['marker_owner']
            if 'TYPE_STATUS=5\n' in baseline['typing']:
                assert handoff and baseline['type_output'] == 'terminal not viewable at usable geometry\n'
                assert '983x72' in baseline['before_tree']
            else:
                assert 'TYPE_STATUS=3\n' in baseline['typing']
                assert not handoff and not baseline['type_output']
                assert '"winterm":' not in baseline['before_tree']
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
        assert '"Toolchest":' in result['tree']
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
            assert all((p['result']['v0'], p['result']['a3']) in
                       [(0, 0), (2, 1), (17, 1)] for p in mkdir)
            assert 'NAMI  "/tmp/xiri-home/.desktop-xiri-indy"' in raw
            assert 'NAMI  "/emul/irix/usr/lib32/libpthread.so"' in raw
            assert not component['stdout']
            if component['name'] != 'fm-background':assert not component['stderr']
            waits = [p for p in pairs if p['call']['syscall'] == 1170]
            pipes = [p for p in pairs if p['call']['syscall'] == 1042]
            sgikopt = [p for p in pairs if p['call']['syscall'] == 1083]
            signals = [line.strip() for line in raw.splitlines() if 'PSIG' in line]
            if component['name'] == 'bgicons':
                assert component['exit_status'] == '0'
                assert mkdir and any(p['result']['a3'] == 0 for p in mkdir)
                assert 'NAMI  "/tmp/xiri-home/.desktophost/xiri-indy/Icons"' in raw
                assert not signals
                boundary = 'helper exits zero after directory creation; no icon contents qualified'
            elif component['name'] == 'fm-background':
                assert not component['exit_status'] and 'PSIG  SIGSEGV' not in raw
                assert 'PSIG  SIGKILL SIG_DFL' in raw
                assert '"FileManager": ("FileManager" "FileManager")' in result['tree']
                selects = [p for p in pairs if p['call']['syscall'] == 1100]
                assert selects and any(p['result'] == dict(syscall=1100, v0=22, a3=1) for p in selects)
                warning = 'Warning: Select failed; error code 22\n'
                count, tail = divmod(len(component['stderr']), len(warning))
                assert count > 0 and component['stderr'] == warning * count + warning[:tail]
                boundary = 'FileManager window renders; repeated select EINVAL; alive until guarded cleanup'
            elif component['name'] == 'fm-home':
                assert component['exit_status'] == '0' and not signals
                assert pipes and all(p['result']['a3'] == 0 for p in pipes)
                boundary = 'home-folder invocation exits zero; browsing and actions unqualified'
            else:
                assert not component['exit_status']
                assert '"Icon Catalog: Blank (Page 1 of 1)":' in result['tree']
                assert 'fatalErrorDialog_popup' not in result['tree']
                assert 'PSIG  SIGSEGV' not in raw and 'PSIG  SIGKILL SIG_DFL' in raw
                assert 'NAMI  "/tmp/xiri-home/.desktop-xiri-indy/iconcatalog/pages/Blank"' in raw
                boundary = 'empty fallback page renders and client remains until guarded cleanup'
            compact = dict(component)
            if compact['stderr']:
                data = compact.pop('stderr').encode()
                compact['stderr_summary'] = dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                    repeated_line=warning.rstrip('\n'), complete_lines=count, trailing_fragment=warning[:tail])
            observation = dict(compact, initialization_passed=True,
                initializations=initializations, mkdir=mkdir, waits=waits,
                pipes=pipes, sgikopt=sgikopt, signals=signals,
                observed_paths=list(dict.fromkeys(re.findall(r'NAMI  "([^"]+)"', raw))),
                truncated_record_lines=dropped, last_complete_pairs=pairs[-7:],
                select_failures=[p for p in pairs if p['call']['syscall'] == 1100 and p['result']['a3']][-8:],
                boundary=boundary)
            components.append(observation)
        report['runs'].append(dict(
            directory=str(directory), mode=result['mode'], pin=run_pin,
            result_sha256=sha(directory / 'result.json'), serial_sha256=sha(directory / 'serial.log'),
            config_sha256=sha(config_path), emulator_command_sha256=sha(command_path),
            sources=result['sources'], staged=result['staged'], seed=result['seed'],
            seed_result_sha256=result['seed_result_sha256'], components=components,
            window_check=baseline['wmcheck'], window_check_passed=window_passed,
            focus_attempts=attempts, marker_owner=baseline['marker_owner'],
            type_output=baseline['type_output'], typing_observation=baseline['typing'],
            frame_capture_passed='BadDrawable' not in baseline['typing'],
            baseline_logs=result['baseline_logs'],
            shell_handoff=baseline['handoff'], shell_marker=baseline['marker'],
            shell_check_passed=shell_passed, controls=result['controls'], guard_control=control, guard=guard,
            native_x11_after=True, clean_shutdown=True, frame_sha256=result['frame_sha256'],
            guest_trace_info=result['trace_info']))
    assert modes == {'ordinary'}
    failed = json.loads((args.failed_ci / 'result.json').read_text())
    assert failed['status'] == 'error' and failed['mode'] == 'ci' and not failed['clean_shutdown']
    assert failed['pin'] == pin and 'timed out after 240s' in failed['error']
    assert not failed['components'] and len(failed['controls']) == 1
    assert failed['controls'][0]['phase'] == 'before'
    for path, digest in failed['sources'].items():assert sha(ROOT / path) == digest
    serial = (args.failed_ci / 'serial.log').read_text()
    assert 'TYPE_STATUS=5' in serial
    report['failed_runs'] = [dict(directory=str(args.failed_ci), status='error', clean_shutdown=False,
        result_sha256=sha(args.failed_ci / 'result.json'), serial_sha256=sha(args.failed_ci / 'serial.log'),
        emulator_log_sha256=sha(args.failed_ci / 'emulator.log'), error=failed['error'],
        native_controls=failed['controls'], guard_control=failed['guard_control'],
        observation='Terminal geometry check failed, then desktop capture timed out; guest did not halt cleanly and emulator was stopped. No frame or client result qualified.')]

    assert any(r['shell_check_passed'] for r in report['runs'])
    chosen = next(r for r in report['runs'] if r['shell_check_passed'] and r['frame_capture_passed'])
    frame = Path(chosen['directory']) / 'desktop.xwd'
    args.png.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['magick', str(frame), str(args.png)], check=True)
    pixels = lambda path: subprocess.check_output(['magick', str(path), '-depth', '8', 'rgba:-'])
    original = pixels(frame)
    assert len(original) == 1024 * 768 * 4 and pixels(args.png) == original
    report['screenshot'] = dict(path=str(args.png), sha256=sha(args.png),
        source=str(frame), pixels_match_xwd=True,
        kind='initial FileManager rendering with Icon Catalog and a working winterm shell')
    defaults = ROOT / '.work/irix-desktop-components/root/usr/lib/X11/app-defaults/IconCatalog'
    default_pin = manifest['resources']['/usr/lib/X11/app-defaults/IconCatalog']
    assert sha(defaults) == default_pin['sha256']
    assert '*dummyPageName: Blank' in defaults.read_text()
    report['catalog'] = dict(defaults_sha256=sha(defaults), dummy_page_name='Blank',
        system_page_data_staged=False, contents_and_actions_qualified=False,
        interpretation='Empty fallback page is consistent with unstaged catalog data; emptiness alone is not a compatibility failure.')
    report['limits'] = [
        'Icon Catalog initial rendering and bgicons zero exit do not qualify populated pages, actions or desktop icons.',
        'System catalog page data is not staged; the original defaults name the dummy page Blank. No claim that page discovery succeeds.',
        'Every failed terminal/window/capture check remains a failure; startup repeatability is not established. The published frame is from a run with a passing shell check.',
        'Per-PID captures contain first/last 4000 lines, overlap, and may truncate records; lists are observations, not event counts.',
        'The bounded fm-home and Icon Catalog traces contain successful pipe calls; fm-background pipe calls are outside its head/tail capture. FileManager renders but loops on select EINVAL.',
        'CI desktop capture times out after TYPE_STATUS=5 and fails clean guest shutdown. The passing ordinary observation does not qualify CI or repeatable startup.',
        'Communication Is Blocked dialog titles occur in the window tree, but the published screenshot does not show them as visible; this is not proof of an active communication error dialog.',
        'Earlier waitsys(options=3) failure remains unqualified; these captures do not establish its resolution.',
        'fmserv, artwork, filetype rules, catalog pages and delayed services remain unqualified.',
        'Session saving is disabled; no general pthread, normal-exit, Newport or physical-hardware claims.',
    ]
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print('FileManager rendering observed; shell checks:', [r['shell_check_passed'] for r in report['runs']], '; full desktop still blocked')


if __name__ == '__main__':
    main()
