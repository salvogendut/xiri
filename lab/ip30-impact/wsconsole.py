"""Qualify the Octane wsdisplay console and its serial recovery path."""
import json
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
from types import SimpleNamespace

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.append(str(ROOT / 'lab/ip28-kernel'))
from xiri_lab import load_probe, sha256
import frame as console_frame


def glyphs(netbsd):
    font = (netbsd / 'sys/dev/wsfont/vt220l8x16.h').read_text()
    rows = bytes(int(row, 16) for row in re.findall(r'^\s*(0x[0-9a-fA-F]{2}),', font, re.M))
    if len(rows) != 256 * 16:
        raise ValueError('unexpected vt220l8x16 font data')
    return {tuple(rows[c*16:c*16+16]): chr(c) for c in range(32, 127)}


def screen_lines(path, font):
    with Image.open(path) as image:
        if image.size != (1280, 1024):
            raise ValueError(f'unexpected console scanout {image.size}')
        image = image.convert('RGB')
        gray = image.convert('L')
        # The pixel just outside the text grid stays at the panel colour.
        background = 0
        left, top, _, _ = console_frame.PANEL
        margin = (left - 1, top - 1)
        if image.getpixel(margin) == (96, 96, 112):
            background = gray.getpixel(margin)
            gray = gray.crop(console_frame.PANEL)
        stride = gray.width // 8
        bitmap = gray.point(lambda v: 255 if v != background else 0, '1').tobytes()
    return [''.join(font.get(tuple(bitmap[start+x:start+x+16*stride:stride]), '?')
                    for x in range(stride)).rstrip()
            for start in range(0, len(bitmap), 16 * stride)]


def capture(lab, ci, path, font, expected, *, reference=None, marker_row=None, timeout=20):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        reply = subprocess.run([ci, '--json', '--socket', lab.socket_path,
                                'screenshot', path], capture_output=True, text=True,
                               check=True, timeout=10)
        if json.loads(reply.stdout).get('fresh') is True:
            with Image.open(path) as image:
                if image.size != console_frame.DISPLAY:
                    time.sleep(.15)
                    continue
            lines = screen_lines(path, font)
            if (all(any(s in line for line in lines) for s in expected)
                    and (marker_row is None or expected[0] in lines[marker_row])
                    and (reference is None or console_frame.check(reference, path)['passed'])):
                return expected
        time.sleep(0.15)
    raise ValueError(f'{path.name}: scanout did not match expected console and text {expected}')


def framed_capture(lab, ci, out, netbsd, name, expected):
    reference = console_frame.load_reference(netbsd / 'xiri/graphics/sgiconsole.png')
    path = out / (name + '.png')
    capture(lab, ci, path, glyphs(netbsd), expected, reference=reference)
    return dict(console_frame.check(reference, path), visible_text=expected)


def check_restored_console(lab, ci, out, netbsd, font):
    lab.send('sh /cdrom/frame.sh')
    restored = framed_capture(
        lab, ci, out, netbsd, 'after-xorg', ['Octane console restored'])
    reference = console_frame.load_reference(netbsd / 'xiri/graphics/sgiconsole.png')
    before, after = out / 'frame-before-scroll.png', out / 'frame-after-scroll.png'
    for path, row in ((before, 1), (after, 0)):
        lab.send('')
        capture(lab, ci, path, font, ['Xiri scroll marker'], reference=reference, marker_row=row)
    lab.send('')
    lab.wait(r'# ', 30)
    scroll = console_frame.check_scroll_captures(reference, before, after)
    if not scroll['passed']:
        raise ValueError('scroll changed the border or lost the marker')
    return restored, scroll


def run(args):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', args.kernel.name):
        raise ValueError('kernel name must use letters, digits, dot, dash or underscore')
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    graphics = args.board != 'none'
    font = glyphs(args.netbsd) if graphics else {}
    probe = load_probe()
    probe.TOOLBOX = []
    probe.IRIS = args.emulator.resolve() / 'iris'
    probe.CI = args.emulator.resolve() / 'iris-ci'
    flash = args.firmware / 'flash.bin'
    nvram = args.firmware / 'nvram.bin'
    inputs = {str(p.resolve()): sha256(p) for p in
              (probe.IRIS, probe.CI, args.kernel, args.disk, flash, nvram)}
    if args.desktop:
        for item in (args.desktop, args.vendor_asa):
            inputs[str(item.resolve())] = sha256(item)
    shutil.copyfile(flash, out / 'flash.bin')
    shutil.copyfile(nvram, out / 'nvram.bin')
    disk = out / ('disk' + args.disk.suffix)
    subprocess.run(['cp', '--reflink=auto', '--sparse=always', '--', args.disk, disk], check=True)
    config = f'''nvram = "nvram.bin"
banks = [512, 0, 0, 0]
headless = true
no_audio = true
ci = true
nat_subnet = "192.168.231.0/24"
[machine]
profile = "octane_ip30"
cpu = "r10000"
cpus = 1
[octane]
flash = "flash.bin"
[graphics]
board = {json.dumps(args.board)}
[scsi.1]
path = {json.dumps(str(disk))}
overlay = true
[network]
mode = "nat"
tftp_dir = {json.dumps(str(args.kernel.resolve().parent))}
'''
    if args.xorg or args.desktop:
        if args.desktop:
            import desktop
            media = desktop.prepare(out, args.desktop, args.vendor_asa)
        else:
            import xorg
            media = xorg.prepare(out)
        config += '[scsi.4]\ncdrom = true\npath = ' + json.dumps(str(media)) + '\n'
    lab = probe.Lab(SimpleNamespace(mode='ci', debugger=False), out, config_text=config,
                    working_directory=out, scsi1_from_config=True)
    result = dict(board=args.board, inputs=inputs, status='incomplete')
    def interrupt(signum, frame):
        raise KeyboardInterrupt
    old_handler = signal.signal(signal.SIGTERM, interrupt)
    try:
        lab.start(boot=False)
        if 'Press any key' in lab.wait(r'Option\?|Press any key to continue', 120)[0]:
            lab.send('')
            lab.wait(r'Option\?', 60)
        lab.send('5')
        lab.wait(r'\n>> ', 30)
        lab.send(f'boot -f bootp():{args.kernel.name} --s')
        lab.wait('Enter pathname of shell', 240)
        serial = lab.serial_text()
        if 'XIRI_IP30_M3D2_READY isp=2 scsibus=2' not in serial or re.search(
                r'XIRI_IP30_\w+_FAILED|panic:|HQ4 FIFO timeout', serial):
            raise ValueError('native platform check failed before the shell')
        result['scsi_ready'] = True
        kernels = ['XIRI_IP30_DESKTOP']
        if not args.desktop:
            kernels.append('XIRI_IP30_HQ4_XORG')
            if not args.xorg:
                kernels.append('XIRI_IP30_HQ4_WSDISPLAY')
        if not any(f'({ident})' in serial for ident in kernels):
            raise ValueError('unexpected kernel identity')
        boards = re.findall(r'ip30gfxprobe0: (\d+) IMPACT board\(s\)', serial)
        display = re.search(r'wsdisplay0 at hq4fb0(?: kbdmux \d+)?: console', serial)
        if boards != [str(int(graphics))] or bool(display) != graphics:
            raise ValueError('unexpected graphics attachment')
        if graphics:
            result['boot_scanout'] = capture(lab, probe.CI, out/'boot.png', font,
                                             ['root on sd0a', 'Enter pathname of shell'])
        lab.send('')
        lab.wait(r'\n# ', 30)
        lab.send('/sbin/mount')
        lab.wait(r'on / type ffs \(read-only[^\n]*\n', 30)
        lab.wait(r'# ', 30)
        lab.send("printf 'Octane %s ready\\n' console > /dev/console")
        lab.wait(r'\nOctane console ready\n', 30)
        lab.wait(r'# ', 30)
        if graphics:
            result['shell_scanout'] = capture(lab, probe.CI, out/'shell.png', font,
                                              ['Octane console ready', 'on / type ffs (read-only'])
        if args.xorg:
            result['xorg'] = xorg.run(lab, probe.CI, out)
            if args.check_frame:
                result['restored_console'], result['scroll'] = check_restored_console(
                    lab, probe.CI, out, args.netbsd, font)
        if args.desktop:
            result['desktop'] = desktop.run(lab, probe.CI, out)
        lab.send('shutdown -h now')
        lab.wait('unmounting done', 90)
        lab.wait(r'Option\?', 30)
        result.update(clean_shutdown=True, read_only_root=True, status='passed')
    except BaseException as exc:
        result.update(status='failed', error=f'{type(exc).__name__}: {exc}')
        raise
    finally:
        try:
            lab.close()
        except Exception as exc:
            result.update(status='cleanup-failed', cleanup_error=str(exc))
            raise
        finally:
            signal.signal(signal.SIGTERM, old_handler)
            result['emulator_stopped'] = lab.process is None or lab.process.poll() is not None
            result['originals_unchanged'] = all(sha256(p) == h for p, h in inputs.items())
            if not result['emulator_stopped'] or not result['originals_unchanged']:
                result['status'] = 'cleanup-failed'
            (out/'result.json').write_text(json.dumps(result, indent=2) + '\n')
    if result['status'] != 'passed':
        raise RuntimeError(result['status'])
    checks = '4Dwm, winterm, logout' if args.desktop else 'console, native shell'
    print(f'{args.board}: {checks} and clean halt passed')
