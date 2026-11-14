#!/usr/bin/env python3
"""Bounded, diskless Octane boot check of an explicitly pinned NetBSD kernel.

The current IP3x build targets O2. This probe does not manufacture an Octane
port or qualify an IRIX payload: it records the firmware/kernel boundary.
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import signal
import time
from types import SimpleNamespace

from xiri_lab import load_probe, sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('kernel-build', 'emulator', 'nvram', 'flash', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--kernel-image', choices=('boot', 'native'), default='boot',
                        help='test the ELF32 PROM wrapper or the underlying ELF64 kernel')
    args = parser.parse_args()
    build, emu, nvram, flash, out = [getattr(args, n).resolve() for n in
        ('kernel_build', 'emulator', 'nvram', 'flash', 'output')]
    kernel = json.loads((build/'module.json').read_text())
    emulator = json.loads((emu/'manifest.json').read_text())
    artifact = kernel['artifacts']['netbsd.boot' if args.kernel_image == 'boot' else 'netbsd']
    boot = build/artifact['path']
    assert sha256(boot) == artifact['sha256']
    assert sha256(emu/'iris') == emulator['iris_sha256']
    assert sha256(emu/'iris-ci') == emulator['ci_sha256']
    assert nvram.stat().st_size == 512 and flash.stat().st_size == 1024*1024
    originals = {str(p): sha256(p) for p in (boot, nvram, flash)}
    out.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(__file__, out/'probe-used.py')
    shutil.copyfile(nvram, out/'nvram.bin')
    shutil.copyfile(flash, out/'flash.bin')
    config = f'''prom = "(embedded)"
nvram = {json.dumps(str(out/'nvram.bin'))}
banks = [512, 0, 0, 0]
headless = true
no_audio = true
ci = true
scsi = {{}}
nat_subnet = "192.168.231.0/24"
[machine]
profile = "octane_ip30"
cpu = "r10000"
cpus = 1
[octane]
flash = {json.dumps(str(out/'flash.bin'))}
[graphics]
board = "none"
[network]
mode = "nat"
tftp_dir = {json.dumps(str(boot.parent))}
'''
    probe = load_probe()
    if not shutil.which('toolbox'):
        probe.TOOLBOX = []
    probe.IRIS, probe.CI = emu/'iris', emu/'iris-ci'
    lab = probe.Lab(SimpleNamespace(mode='ci', debugger=False, boot_timeout=300),
                    out, config_text=config, working_directory=out)
    launch = lab.launch

    def diskless_launch(command, name):
        if name == 'emulator':
            command = list(command)
            index = command.index('--scsi1')
            del command[index:index+2]
        return launch(command, name)

    lab.launch = diskless_launch
    result = dict(schema=1, status='incomplete', scope=__doc__.strip(),
        kernel_build=kernel, emulator=emulator, original_files=originals,
        machine='octane_ip30', cpu='r10000', memory_mb=512, cpus=1,
        kernel_image=args.kernel_image,
        attached_disks=[], vendor_program_executed=False, commands=[],
        script_sha256=sha256(__file__))

    def prom(command):
        result['commands'].append(command)
        lab.send(command)
        lab.wait(r'(?:^|\n)>>? ', 30)

    def interrupted(signum, frame):
        raise RuntimeError('Interrupted by signal '+str(signum))

    signal.signal(signal.SIGTERM, interrupted)
    try:
        lab.start(boot=False)
        menu = lab.wait(r'Option\?|Press any key to continue', 120)
        if 'Press any key' in menu[0]:
            # With no SCSI targets the firmware asks for acknowledgement.
            lab.send('')
            lab.wait(r'Option\?', 60)
        lab.send('5'); lab.wait(r'(?:^|\n)>>? ', 30)
        prom('setenv console d')
        prom('setenv AutoLoad No')
        prom('hinv')
        print('Octane PROM reached; attempting pinned IP3x kernel', flush=True)
        command = 'boot -f bootp():'+boot.name+' --s'
        result['commands'].append(command)
        lab.send(command)
        start = time.monotonic()
        deadline = start+300
        while time.monotonic() < deadline:
            text = lab.serial_text()[lab.offset:]
            if re.search(r'Exception:|PANIC|panic:|Stopped in pid|Error loading|Unable to load|Cannot load|Invalid argument', text):
                result['status'] = 'boot-blocked'
                break
            if re.search(r'Enter pathname of shell|login:', text):
                result['status'] = 'native-prompt-reached'
                break
            if lab.process.poll() is not None:
                result.update(status='boot-blocked', emulator_exit=lab.process.returncode)
                break
            time.sleep(.1)
        else:
            result['status'] = 'boot-timeout'
        result['boot_elapsed_seconds'] = round(time.monotonic()-start, 2)
        result['serial_tail'] = lab.serial_text()[-12000:]
        for command in ('regs', 'ip30', 'ip30 unmapped'):
            result.setdefault('monitor', {})[command] = lab.monitor_command(command)
        print(result['status'], flush=True)
    except BaseException as error:
        result.update(status='probe-failed', error=str(error))
        raise
    finally:
        lab.close()
        result['emulator_stopped'] = lab.process is None or lab.process.poll() is not None
        result['originals_unchanged'] = all(sha256(p) == h for p, h in originals.items())
        (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    main()
