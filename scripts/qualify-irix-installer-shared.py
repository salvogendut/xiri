#!/usr/bin/env python3
"""Verify original-inst progress beyond mmap and identify its next boundary."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import struct
import subprocess

ROOT = Path(__file__).resolve().parent.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


tcp = module('tcp', 'scripts/probe-irix-tcp.py')
runtime = module('runtime', 'scripts/probe-irix-runtime.py')


def pairs(raw):
    lines = raw.splitlines(True)
    # The observer retains head/tail. Short captures contain the full trace twice.
    if len(lines) % 2 == 0 and lines[:len(lines)//2] == lines[len(lines)//2:]:
        raw = ''.join(lines[:len(lines)//2])
    result, pending = [], None
    for match in re.finditer(r'MISC\s+(irix_o32|irix_ret):\n(?:(?:\t| {8})[^\n]*\n)+', raw):
        text = tcp.trace_records(match[0], match[1], True)[0]
        values = {k: int(v, 0) for k, v in re.findall(r'(\w+)=(0x[0-9a-f]+|\d+)', text)}
        if match[1] == 'irix_o32':
            pending = values
        elif pending and pending['syscall'] == values['syscall']:
            result.append(dict(call=pending, result=values))
            pending = None
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('run', type=Path)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    run = json.loads((a.run / 'result.json').read_text())
    pin = json.loads((ROOT / 'lab/irix-mmap-shared/baseline.json').read_text())
    assert run['status'] == 'observed' and run['clean_shutdown'] and run['pin'] == pin
    assert run['seed_result_sha256'] == sha(ROOT / run['seed'] / 'result.json')
    for path, digest in run['sources'].items():
        assert sha(ROOT / path) == digest, path
    manifest_path = ROOT / 'lab/irix-installer/manifest.json'
    manifest = json.loads(manifest_path.read_text())
    assert run['manifest_sha256'] == sha(manifest_path)
    assert run['inputs_sha256'] == sha(ROOT / 'lab/irix-installer/inputs.json')
    for path, info in manifest['files'].items():
        assert sha(ROOT / '.work/irix-freeware/installed' / path.lstrip('/')) == info['sha256']
    assert (a.run / 'media/root.env').read_text().splitlines()[0] == 'HOME=/'
    assert len(run['controls']) == 4
    assert {(c['phase'], c['uid']) for c in run['controls']} == {(phase, uid) for phase in ['before', 'after'] for uid in [0, 1234]}
    normal = dict(errno_bytes=0, errno=0, exit=0, signal=0, killed=0, stdout='', stderr='')
    assert all(c['actual'] == dict(normal, exit=37, stdout='XIRI_ABI_PROBE\n') and c['group_absent'] for c in run['controls'])
    assert '\nxiritest:1234:100:/usr/people/xiritest:/bin/ksh\n1234 700\n' in run['home_setup']
    assert 'XIRI_USER created' in run['home_setup'] and 'XIRI_USER existing' in run['home_setup']
    for kind, output in [('native', 'XIRI_HOME_NATIVE\n'), ('foreign', 'XIRI_SHARED_HOME\n')]:
        raw = run['shared_home'][kind]
        assert runtime.observation(raw) == dict(normal, stdout=output) and 'GROUP absent=1' in raw
    assert '\n1234\n' in run['shared_home']['owner']
    assert [c['name'] for c in run['cases']] == ['hardware', 'distribution']
    warnings = 'Internal program error: SIGBUS not handled for mmap.\nInternal program error: SIGSEGV not handled for mmap.\n'
    expected = {
        'hardware': dict(normal, stdout='CPUARCH=\n\nCPUBOARD=\nMODE=32bit\nGFXBOARD=SERVER\nSUBGR=SERVER\n',
            stderr=warnings + 'WARNING: Unrecognized cpu hardware type.  See the "hardware" help topic for details.\nWARNING: Unrecognized cpu architecture type.  See the "hardware" help topic for details.\n'),
        'distribution': dict(normal, stdout='FATAL ERROR: Unable to start inst: Failed to create target directories:\n\tUnable to fork sub command: Function not implemented\n', stderr=warnings),
    }
    traces = {}
    for c in run['cases']:
        name = c['name']
        assert c['runner_rc'] == 0 and c['group_absent'] and c['actual'] == expected[name]
        assert sha(a.run / (name + '.log')) == c['log_sha256']
        assert sha(a.run / (name + '.kdump')) == c['trace_sha256']
        raw = (a.run / (name + '.kdump')).read_text()
        assert 'PSIG  SIGSEGV' not in raw and 'PSIG  SIGBUS' not in raw
        assert 'NAMI  "/dev/zero"' in raw
        events = pairs(raw)
        mmap = [x for x in events if x['call']['syscall'] == 1134 and x['call']['a1'] == 0x100000]
        assert len(mmap) == 1
        request = mmap[0]['call']; result = mmap[0]['result']
        assert [request[k] for k in ['a0', 'a1', 'a2', 'a3']] == [0, 0x100000, 3, 0x141]
        assert result['a3'] == 0 and 0 < result['v0'] < 0x80000000 and result['v0'] % 8192 == 0
        sigactions = [x for x in events if x['call']['syscall'] == 1162 and x['call']['a0'] in [10, 11]]
        assert len(sigactions) == 2 and all(x['result'] == dict(syscall=1162, v0=89, a3=1) for x in sigactions)
        traces[name] = dict(installer_mmap=mmap[0], signal_registration=sigactions,
            unsupported=[x for x in events if x['result']['v0'] == 89 and x['result']['a3'] == 1])
        if name == 'hardware':
            assert 'machfile"' in raw
            file_maps = [x for x in events if x['call']['syscall'] == 1134 and x['call']['a1'] == 5025]
            assert len(file_maps) == 1 and file_maps[0]['call']['a2'] == 1 and file_maps[0]['call']['a3'] == 1 and file_maps[0]['result']['a3'] == 0
            traces[name]['machfile_mmap'] = file_maps[0]
        else:
            spawns = [x for x in events if x['call']['syscall'] == 1129]
            assert len(spawns) == 1
            spawn = spawns[0]
            assert spawn['call']['pc'] == 0xfa75038 and spawn['call']['a0'] == 0xfa750a8 and spawn['call']['a1'] == 0x3000040
            assert spawn['result'] == dict(syscall=1129, v0=89, a3=1)
            index = events.index(spawn)
            assert [x['call']['syscall'] for x in events[index - 2:index]] == [1042, 1042]
            assert all(x['result']['a3'] == 0 for x in events[index - 2:index])
            assert not any(x['call']['syscall'] == 1002 for x in events)
            assert 'NAMI  "/cdrom/dist' not in raw
            traces[name]['subcommand_spawn'] = spawn
    library = '/usr/lib32/libc.so.1'
    data = (ROOT / '.work/irix-freeware/installed' / library.lstrip('/')).read_bytes()
    pc = 0xfa75038
    segment = next(s for s in manifest['files'][library]['loads'] if s['address'] <= pc < s['address'] + s['file_bytes'])
    offset = segment['offset'] + pc - segment['address']
    assert struct.unpack_from('>I', data, offset)[0] == 0x0000000c
    disassembly = a.run / 'libc-subcommand-disassembly.txt'
    assert '<_nsproc+' in disassembly.read_text() and 'fa75038:' in disassembly.read_text()
    revision = '5aca2679d78276864d2980a08314887b2058fb2c'
    evidence = []
    for path in ['sys/compat/irix/irix_syscall.h', 'sys/compat/irix/irix_prctl.h']:
        content = subprocess.check_output(['git', '-C', str(ROOT.parent / 'NetBSD-nixbench'), 'show', revision + ':' + path])
        evidence.append(dict(revision=revision, path=path, sha256=hashlib.sha256(content).hexdigest()))
        if path.endswith('irix_syscall.h'):
            assert re.search(rb'IRIX_SYS_sproc\s+129', content)
        else:
            for flag, value in [('SADDR', 0x40), ('BLOCK', 0x1000000), ('NOLIBC', 0x2000000)]:
                match = re.search(rb'IRIX_PR_' + flag.encode() + rb'\s+(0x[0-9a-fA-F]+)', content)
                assert match and int(match[1], 16) == value
    report = dict(schema=1, status='installer-subcommand-sproc-boundary', installation_success=False,
        hardware_report_printed=True, hardware_identification_complete=False, distribution_read=False,
        qualifier_sha256=sha(Path(__file__)), trace_decoder_sha256=sha(ROOT / 'scripts/probe-irix-tcp.py'),
        pin=pin, source_evidence=evidence, manifest_sha256=run['manifest_sha256'], inputs_sha256=run['inputs_sha256'],
        root_session_home='/', native_home='/usr/people/xiritest', native_write_foreign_read=True,
        graphical_login_qualified=False, native_controls=4, cases=run['cases'], traces=traces,
        subcommand=dict(syscall=1129, name='sproc', flags='0x03000040',
            decoded_flags=['PR_SADDR', 'PR_BLOCK', 'PR_NOLIBC'], library=library,
            trap_pc='0x0fa75038', child_entry='0x0fa750a8', trap_bytes_match=True,
            disassembly_sha256=sha(disassembly), error=89),
        run=dict(directory=str(a.run), result_sha256=sha(a.run / 'result.json'),
            serial_sha256=sha(a.run / 'serial.log'), clean_shutdown=True, sources=run['sources']),
        limitations=['Exit zero is not installation success: the dry run emits FATAL ERROR before distribution reading.',
            'sproc shared-address-space/blocking semantics require measurement; substituting fork would not establish them.',
            'Signal-handler registration, hardware queries, time and creat also remain unsupported in this trace.',
            'No new graphical application success or screenshot is claimed.'])
    a.output.write_text(json.dumps(report, indent=2) + '\n')
    print('Verified original inst mmap progress, hardware output and sproc 1129 boundary')


if __name__ == '__main__':
    main()
