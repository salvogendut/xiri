#!/usr/bin/env python3
"""Verify installer startup/fault evidence and shared native-home checks."""
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('fault', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    pin = json.loads((ROOT / 'lab/irix-pipe/baseline.json').read_text())
    manifest_path = ROOT / 'lab/irix-installer/manifest.json'
    manifest = json.loads(manifest_path.read_text())
    records = []
    for directory in [args.run, args.fault]:
        result = json.loads((directory / 'result.json').read_text())
        assert result['status'] == 'observed' and result['clean_shutdown'] and result['pin'] == pin
        for path, digest in result['sources'].items():
            assert sha(ROOT / path) == digest, path
        assert sha(ROOT / result['seed'] / 'result.json') == result['seed_result_sha256']
        records.append(result)
    run, fault = records
    assert run['manifest_sha256'] == sha(manifest_path)
    assert run['inputs_sha256'] == sha(ROOT / 'lab/irix-installer/inputs.json')
    for path, info in manifest['files'].items():
        assert sha(ROOT / '.work/irix-freeware/installed' / path.lstrip('/')) == info['sha256']
    assert fault['seed'] == str(args.run)
    assert len(run['controls']) == 4
    assert {(c['phase'], c['uid']) for c in run['controls']} == {
        (phase, uid) for phase in ['before', 'after'] for uid in [0, 1234]}
    normal = dict(errno_bytes=0, errno=0, exit=37, signal=0, killed=0,
                  stdout='XIRI_ABI_PROBE\n', stderr='')
    assert all(c['actual'] == normal and c['group_absent'] for c in run['controls'])
    assert len(fault['controls']) == 6
    for phase in ['before', 'after']:
        group = [c for c in fault['controls'] if c['phase'] == phase]
        assert {c['uid'] for c in group if c['kind'] == 'native'} == {0, 1234}
        for c in group:
            if c['kind'] == 'native':
                assert 'END exit=37 signal=0' in c['raw']
            else:
                match = re.search(r'STOP phase=fault signal=11 code=1 address=00000000 pc=([0-9a-f]+)', c['raw'])
                assert match and int(match[1], 16) == int(c['site'], 16)
                assert 'END exit=-1 signal=9' in c['raw']
    assert '\nxiritest:1234:100:/usr/people/xiritest:/bin/ksh\n1234 700\n' in run['home_setup']
    assert 'XIRI_USER created' in run['home_setup'] and 'XIRI_USER existing' in run['home_setup']
    spec = importlib.util.spec_from_file_location('runtime', ROOT / 'scripts/probe-irix-runtime.py')
    runtime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)
    for kind, output in [('native', 'XIRI_HOME_NATIVE\n'), ('foreign', 'XIRI_SHARED_HOME\n')]:
        raw = run['shared_home'][kind]
        assert runtime.observation(raw) == dict(normal, exit=0, stdout=output)
        assert 'GROUP absent=1' in raw
    assert '\n1234\n' in run['shared_home']['owner']
    assert '\nHOME_PERSISTED\n' in fault['home_after_reboot']
    assert [c['name'] for c in run['cases']] == ['hardware', 'distribution']
    for c in run['cases']:
        assert c['runner_rc'] == 0 and c['group_absent']
        assert c['actual'] == dict(normal, exit=-1, signal=11, stdout='')
        assert sha(args.run / (c['name'] + '.log')) == c['log_sha256']
        assert sha(args.run / (c['name'] + '.kdump')) == c['trace_sha256']
        trace = (args.run / (c['name'] + '.kdump')).read_text()
        assert 'NAMI  "/dev/zero"' in trace and 'PSIG  SIGSEGV SIG_DFL' in trace
    assert len(fault['cases']) == 1 and fault['cases'][0]['uid'] == 0
    trace_path = args.fault / '0.trace'
    assert sha(trace_path) == fault['cases'][0]['trace_sha256']
    trace = trace_path.read_text()
    call = re.search(r'^LOOKUP name=mmap (.*)$', trace, re.M)
    values = {k: int(v, 16) for k, v in re.findall(r'(\w+)=([0-9a-f]+)', call[1])}
    assert values == dict(a0=0, a1=0x100000, a2=3, a3=0x141, a4=3, a5=0, ra=0x43e1984)
    assert 'LOOKUP_RETURN name=mmap v0=0000000000000016 a3=0000000000000001' in trace
    assert 'STOP phase=fault signal=11 code=1 address=ffffffff pc=00000000043e18d4' in trace
    assert 'END exit=-1 signal=9' in trace
    fault_regs = re.search(r'STOP phase=fault[^\n]*\nREGS ([^\n]*)', trace)
    regs = {int(k): int(v, 16) for k, v in re.findall(r'(\d+)=([0-9a-f]+)', fault_regs[1])}
    assert regs[8] == regs[35] == 0xffffffffffffffff
    assert regs[36] & 0x80000000  # MIPS branch-delay exception.
    memory = re.search(r'^MEM pc address=043e18b4 error=0 bytes=128 hex=([0-9a-f]+)$', trace, re.M)
    data = bytes.fromhex(memory[1])
    lib = '/usr/lib32/internal/libinst.so'
    segment = next(p for p in manifest['files'][lib]['loads'] if p['address'] <= 0x43e18b4 < p['address'] + p['file_bytes'])
    offset = segment['offset'] + 0x43e18b4 - segment['address']
    original = (ROOT / '.work/irix-freeware/installed' / lib.lstrip('/')).read_bytes()
    assert original[offset:offset + 128] == data
    assert struct.unpack_from('>II', data, 32) == (0x0320f809, 0xa1000000)
    # jalr t9; sb zero,0(a4): the delay-slot store uses the failed-map pointer.
    disassembly = args.fault / 'libinst-disassembly.txt'
    assert '<vprintf__7iStringGPCcPc+' in disassembly.read_text()
    evidence = []
    for revision, path in [(pin['source_revision'], 'sys/compat/irix_o32/irix_o32.c'),
                           ('5aca2679d78276864d2980a08314887b2058fb2c', 'sys/compat/irix/irix_mman.h')]:
        content = subprocess.check_output(['git', '-C', str(ROOT.parent / 'NetBSD-nixbench'), 'show', revision + ':' + path])
        evidence.append(dict(revision=revision, path=path, sha256=hashlib.sha256(content).hexdigest()))
    report = dict(schema=1, status='installer-startup-mmap-boundary', installation_success=False,
        qualifier_sha256=sha(Path(__file__)), pin=pin, source_evidence=evidence,
        manifest_sha256=sha(manifest_path), inputs_sha256=run['inputs_sha256'],
        home=dict(path='/usr/people/xiritest', uid=1234, primary_gid=100, shell='/bin/ksh',
                  mode='0700', create_and_repeat=True, native_write_foreign_read=True,
                  file_owner=1234, cold_boot_persistence=True, desktop_login_qualified=False,
                  note='Direct shared-file probes use explicit UID/GID 1234; the native account primary GID is users/100.'),
        root_session_home='/', cases=run['cases'],
        fault=dict(mmap=values, error=22, flags=['SHARED', 'AUTOGROW', 'AUTORESRV'],
                   epc='0x043e18d4', instruction_pc='0x043e18d8', instruction='sb zero,0(a4)',
                   branch_delay=True, fault_address='0xffffffff', register8='0xffffffffffffffff',
                   library=lib, function='iStringG::vprintf', original_code_bytes_match=True,
                   disassembly_sha256=sha(disassembly)),
        controls=dict(native_execution=8, native_known_fault=2),
        runs=[dict(directory=str(d), result_sha256=sha(d / 'result.json'), serial_sha256=sha(d / 'serial.log'),
                   clean_shutdown=True, sources=r['sources']) for d, r in zip([args.run, args.fault], records)],
        limitations=['No successful installation, package hooks or GUI installer demonstrated.',
                    'Shared/autogrow mmap semantics require original-IRIX measurement before implementation.',
                    'Native home/file persistence is established; graphical login, catalog launch and removal remain unqualified.'])
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print('Verified: shared home and cold-boot persistence; installer fault after rejected shared/autogrow mmap')


if __name__ == '__main__':
    main()
