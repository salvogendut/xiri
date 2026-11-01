#!/usr/bin/env python3
"""Independently check original IRIX signal records and their fixture bytes."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import struct
import tarfile

ROOT = Path(__file__).resolve().parent.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def elf_word(raw, address):
    assert raw[:6] == b'\x7fELF\x01\x02'
    offset = struct.unpack_from('>I', raw, 28)[0]
    size, count = struct.unpack_from('>HH', raw, 42)
    for i in range(count):
        kind, start, va, _, length = struct.unpack_from('>IIIII', raw, offset + i * size)
        if kind == 1 and va <= address and address + 4 <= va + length:
            return struct.unpack_from('>I', raw, start + address - va)[0]
    raise AssertionError('address outside file-backed ELF segment')


def registration(data, w, symbols):
    s = symbols
    signo, new, old = s['SIGNUM'], s['SET_KIND'], s['OLD_KIND']
    invalid = not 1 <= signo <= 64
    input_fault = new in [2, 4, 5]
    forbidden_set = signo in [9, 23] and new != 1
    error = 14 if input_fault else 22 if invalid or forbidden_set else 14 if old in [2, 4, 5, 6] else 0
    query_error = 22 if invalid else 0
    assert w[16:19] == [error, 0xfeedface, int(bool(error))]
    assert w[19:22] == [query_error, 0xfeedface, int(bool(query_error))]
    # This shell environment inherits NOCLDSTOP for SIGCHLD; it is not a
    # claim about the default disposition of every original IRIX process.
    previous = [0x20000 if signo == 18 else 0, 0, 0, 0, 0, 0]
    changed = error == 0 and new != 1
    action = [s['FLAGS'] & 0x1f, w[11] if s['HANDLER'] == 3 else s['HANDLER'],
              s['MASK0'] & 0xffbffeff, s['MASK1'], 0, 0] if changed else previous
    previous_bytes = struct.pack('>6I', *previous)
    oldbuf = data[256:296]
    if not error and old in [0, 3]:
        start = 5 if old == 3 else 4
        assert oldbuf[:start] == b'\xa5' * start
        assert oldbuf[start:start + 24] == previous_bytes
        assert oldbuf[start + 32:] == b'\xa5' * (40 - start - 32)
    else:
        assert oldbuf == b'\xa5' * 40
    querybuf = data[1920:1960]
    if invalid:
        assert querybuf == b'\xa5' * 40
    else:
        assert querybuf[:4] == querybuf[36:] == b'\xa5' * 4
        assert list(struct.unpack_from('>6I', querybuf, 4)) == action
    boundary = bytearray(b'\x5a' * 32)
    request = struct.pack('>8I', s['FLAGS'], w[11] if s['HANDLER'] == 3 else s['HANDLER'],
                          s['MASK0'], s['MASK1'], s['MASK2'], s['MASK3'], 0x12345678, 0x87654321)
    if new == 4:
        boundary[-4:] = request[:4]
    elif new == 5:
        boundary[4:] = request[:28]
    copy_bytes = 32 if not error and old in [0, 3] else 0
    if not input_fault and not invalid and not forbidden_set:
        if old == 4:
            boundary[-4:] = previous_bytes[:4]
            copy_bytes = 4
        elif old == 5:
            boundary[4:28] = previous_bytes
            # These are the caller's explicit reserved input bytes in this
            # fixture. Future native serializers need not reproduce padding.
            boundary[28:] = request[24:28]
            copy_bytes = 28
    assert data[448:480] == boundary
    # Reserved action words and unrelated kernel frame padding are excluded
    # from the public contract and retained only in the private raw archive.
    if action[1] == w[11]:
        action[1] = 'fixture handler'
    return dict(registration=w[16:19], query=w[19:22], action_after=action if not invalid else None,
                old_copyout_bytes=copy_bytes, disposition_changed=changed, guards_verified=True)


def decode(data, case, identity, elf):
    assert len(data) == 2048
    w = list(struct.unpack('>512I', data))
    s = case['symbols']
    assert w[:4] == [0x58534947, s['CASE'], s['KIND'], s['FLAGS']]
    assert w[4:8] == [identity] * 4 and 1 < w[8] < 0x80000000
    assert w[10] == s['SIGNUM'] and w[13] == 4096
    assert w[509:511] == [s['FPU'], s['RETURN_TEST']]
    assert w[48:55] == [0, 0xfeedface, 0, 0x4000, 0, 0, 0]
    # Verify actual MIPS III SD opcodes, not o32 GAS's register-pair macro.
    for i in range(32):
        register = 0 if i == 26 else i
        assert elf_word(elf, w[12] + 8 + i * 4) == 0xff400000 | (register << 16) | (i * 8)
    for offset in range(136, 256, 4):
        if elf_word(elf, w[12] + offset) == 0x0000000c:
            expected = 1000 if '-indirect-' in case['name'] else 1088
            assert elf_word(elf, w[12] + offset - 4) == 0x24020000 | expected
            break
    else:
        raise AssertionError('missing trampoline sigreturn')
    result = dict(name=case['name'], identity=identity, kind=s['KIND'],
                  **registration(data, w, s), handler_count=w[15])
    if not s['KIND']:
        assert w[15] == 0 and not any(w[128:480])
        return result
    assert w[16:22] == [0, 0xfeedface, 0] * 2
    assert w[15] == 1 and w[22:25] == [0, 0xfeedface, 0]
    for start in [32, 39, 45]:
        assert w[start:start + 3] == [0, 0xfeedface, 0]
    entry = struct.unpack_from('>32Q', data, 512)
    siginfo = bool(s['FLAGS'] & 8)
    tagged = s['SIGNUM'] | (0x80000000 if siginfo else 0)
    assert entry[4] & 0xffffffff == tagged
    assert entry[7] == w[11] and entry[6] == entry[29]
    alignment = 16 if case['abi'] == 'n32' else 8
    assert 0x10000 < entry[6] < 0x80000000 and entry[6] % alignment == 0
    ctx = data[768:1792]
    if siginfo:
        n32 = case['abi'] == 'n32'
        regbase, width, count = (40, 8, 37) if n32 else (40, 4, 36)
        regs = struct.unpack_from('>' + ('Q' if n32 else 'I') * count, ctx, regbase)
        saved_pc, saved_sp = regs[35], regs[29]
        saved_mask = list(struct.unpack_from('>4I', ctx, 8))
        frame = dict(form='ucontext', flags=struct.unpack_from('>I', ctx)[0],
                     greg_offset=regbase, greg_bytes=width, greg_count=count,
                     fp_offset=336 if n32 else 184, fp_csr_offset=592 if n32 else 312,
                     siginfo_offset=entry[5] - entry[6])
        assert frame['siginfo_offset'] == (800 if n32 else 512)
        assert regs[0] == 0 and regs[2] == 0 and regs[3] & 0xffffffff == 0xfeedface and regs[7] == 0
        assert frame['flags'] == (15 if s['FPU'] else 7)
        info = w[448:480]
        assert info[:3] == [s['SIGNUM'], 1 if s['KIND'] == 2 else 0, 0]
        assert info[3] == (w[25] if s['KIND'] == 2 else w[8])
        assert info[4] == (0 if s['KIND'] == 2 else identity)
        if s['KIND'] == 2:
            assert info[5] == 37
        assert ctx[frame['siginfo_offset']:frame['siginfo_offset'] + 128] == data[1792:1920]
    else:
        regs = struct.unpack_from('>32Q', ctx, 16)
        saved_pc = struct.unpack_from('>Q', ctx, 8)[0]
        saved_sp = regs[29]
        saved_mask = list(struct.unpack_from('>4I', ctx, 584))
        frame = dict(form='sigcontext', regmask=struct.unpack_from('>I', ctx)[0],
                     greg_offset=16, greg_bytes=8, greg_count=32,
                     fp_offset=272, fp_csr_offset=532,
                     fp_present=bool(struct.unpack_from('>I', ctx, 528)[0]))
        assert entry[5] == 0 and not any(w[448:480])
        assert regs[0] == 0 and regs[2] == 0 and regs[3] & 0xffffffff == 0xfeedface and regs[7] == 0
        assert frame['regmask'] == 0xffffffff and frame['fp_present'] == bool(s['FPU'])
    assert saved_mask == [0x4000, 0, 0, 0]
    assert saved_sp > entry[29] and saved_sp < 0x80000000
    assert elf_word(elf, saved_pc - 4) == 0x0000000c
    frame.update(stack_bytes=saved_sp - entry[29], alignment=alignment, saved_mask=saved_mask,
                 active_mask=w[35:39], handler_action=w[56:62])
    active = 0x4000 | s['MASK0'] | (0 if s['FLAGS'] & 16 else 1 << (s['SIGNUM'] - 1))
    assert w[35:39] == [active, 0, 0, 0]
    assert w[56:62] == [s['FLAGS'], 0 if s['FLAGS'] & 2 else w[11], s['MASK0'], 0, 0, 0]
    if frame['handler_action'][1]:
        frame['handler_action'][1] = 'fixture handler'
    if s['FPU']:
        expected = [0x11223344, 0x55667788, 0x10203040, 0x50607080,
                    0x89abcdef, 0x01234567, 0x88776655, 0x44332211, 2]
        assert w[490:499] == w[500:509] == expected
        assert struct.unpack_from('>I', ctx, frame['fp_csr_offset'])[0] == 2
        fp = frame['fp_offset']
        stride = 8 if not siginfo or case['abi'] == 'n32' else 4
        for number, expected_double in zip([0, 2, 20, 22], [0x1122334455667788, 0x1020304050607080, 0x89abcdef01234567, 0x8877665544332211]):
            if case['abi'] == 'n32':
                assert struct.unpack_from('>Q', ctx, fp + number * stride)[0] == expected_double
            else:
                # o32 FR=0 exposes the low half as the even FPR and the high
                # half as the odd FPR, including in the 64-bit legacy slots.
                form = '>Q' if stride == 8 else '>I'
                low = struct.unpack_from(form, ctx, fp + number * stride)[0]
                high = struct.unpack_from(form, ctx, fp + (number + 1) * stride)[0]
                assert (high << 32) | low == expected_double
        frame['fpu_restored'] = True
    if s['RETURN_TEST']:
        result['bad_sigreturn'] = w[120:123]
        assert w[120:123] == [14, 0xfeedface, 1]
    if s['KIND'] == 2:
        assert w[26:29] == [0, 0xfeedface, 0]
        if s['REAP']:
            assert w[42:45] == [0, 37 << 8, 0]
            assert w[80:86] == [18, 1, 0, w[25], 0, 37]
            assert w[29:32] == [10, 0xfeedface, 1]
        else:
            assert w[29:32] == [0, 37 << 8, 0]
        result['child_reaped_in_handler'] = bool(s['REAP'])
    result['frame'] = frame
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('run', type=Path)
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    run = json.loads((args.run/'result.json').read_text())
    assert run['status'] == 'observed' and run['scope'] == 'full' and run['clean_shutdown']
    manifest = run['manifest']
    assert len(manifest['cases']) == len(manifest['files']) == 240
    assert manifest['identities'] == [[0] * 4, [1234] * 4]
    assert run['selected_cases'] == [c['name'] for c in manifest['cases']]
    assert run['harness_sha256'] == sha(ROOT/'scripts/probe-irix-reference-signal.py')
    for path, digest in manifest['sources'].items():
        assert sha(ROOT/path) == digest, path
    for name, info in manifest['files'].items():
        assert sha(args.run/'fixtures'/name) == info['sha256']
    assert set(run['checked_files']) == set(manifest['files'])
    assert run['seed_result_sha256'] == sha(ROOT/run['seed']/'result.json')
    seed = json.loads((ROOT/run['seed']/'result.json').read_text())
    assert seed['status'] == 'observed' and seed['clean_shutdown']
    assert seed['firmware_sha256'] == run['firmware_sha256']
    decoded = []
    with tarfile.open(args.run/'outputs.tgz') as archive:
        status = {n: int(rc) for n, rc in re.findall(r'^CASE (\S+) (\d+)$', archive.extractfile('status.txt').read().decode(), re.M)}
        assert len(status) == len(run['observations']) == len(manifest['cases']) * 2
        for case in manifest['cases']:
            elf = (args.run/'fixtures'/case['name']).read_bytes()
            for identity in [0, 1]:
                name = case['name'] + '-' + str(identity)
                assert status[name] == 0 and not archive.extractfile(name+'.err').read()
                data = archive.extractfile(name+'.out').read()
                observation, = [o for o in run['observations'] if o['name'] == name]
                assert observation == dict(name=name, identity=identity, exit=0, stdout_hex=data.hex(), stderr='')
                try:
                    decoded.append(decode(data, case, 1234 if identity else 0, elf))
                except AssertionError as error:
                    raise AssertionError(name) from error
    report = dict(schema=1, status='original-signal-reference', kernel_implementation=False,
                  executions=len(decoded), delivery_executions=sum(d['kind'] != 0 for d in decoded),
                  fpu_executions=sum(d.get('frame', {}).get('fpu_restored', False) for d in decoded),
                  child_executions=sum(d['kind'] == 2 for d in decoded),
                  handler_reaps=sum(d.get('child_reaped_in_handler', False) for d in decoded),
                  bad_sigreturn_executions=sum('bad_sigreturn' in d for d in decoded),
                  registration_results=dict(Counter(str(d['registration']) for d in decoded)),
                  qualifier_sha256=sha(Path(__file__)), run=dict(directory=str(args.run),
                      result_sha256=sha(args.run/'result.json'), archive_sha256=sha(args.run/'outputs.tgz'),
                      serial_sha256=sha(args.run/'serial.log'), clean_shutdown=True),
                  provenance={k: run[k] for k in ['started_utc', 'identity', 'mode', 'harness_sha256',
                      'emulator_sha256', 'firmware_sha256', 'raw_disk_size', 'raw_disk_validation',
                      'seed', 'seed_result_sha256', 'seed_nvram_sha256']},
                  tools=manifest['tools'], sources=manifest['sources'], fixtures=manifest['files'],
                  limitations=['Original IRIX CI reference only; no NetBSD signal implementation.',
                      'No alternate stack, nested delivery, syscall restart or disposition lifecycle coverage.',
                      'No corrupt valid-context or real-time delivery coverage.',
                      'Wait-any covers one already exited child, not no-event, multi-child or tracing behavior.',
                      'Reserved action words, frame padding and raw FPU ownership values are not contracts.'],
                  observations=decoded)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print('Verified', len(decoded), 'original signal executions')


if __name__ == '__main__':
    main()
