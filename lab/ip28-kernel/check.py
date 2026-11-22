#!/usr/bin/env python3
"""Qualify a native IP28 kernel on a private overlay, then halt and stop IRIS.

The disk is read through a private copy-on-write overlay. Serial B provides
administration; optional checks qualify the graphical console and desktop.
"""
import argparse
import hashlib
import shutil
import json
import os
from pathlib import Path
import re
import resource
import signal
import socket
import subprocess
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iris", type=Path, required=True)
    parser.add_argument("--disk", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--kernel", default="netbsd")
    parser.add_argument("--kernel-sha256", help="Expected installed /netbsd.ip28 checksum on a disk boot")
    parser.add_argument("--tftp", type=Path, help="Direct PROM kernel TFTP directory; otherwise boot the disk header")
    media_group = parser.add_mutually_exclusive_group()
    media_group.add_argument("--media", type=Path, help="Read-only ISO with netbsd and ip28boot for installation")
    media_group.add_argument("--fixture-media", type=Path, help="Mount/check this test ISO without reinstalling the kernel/loader")
    parser.add_argument("--firmware-dir", type=Path, help="Use saved nvram/nveeprom and boot without resetting PROM variables")
    parser.add_argument("--overlay-dir", type=Path, help="Reuse a prepared private disk overlay")
    parser.add_argument("--machine", choices=("ip28", "indy-r4400", "indy-r5000"), default="ip28")
    parser.add_argument("--irix-module", help="Load this matching module and run the installed IRIX sh")
    parser.add_argument("--check-command", action="append", default=[],
                        help="Additional bounded guest shell check before shutdown (repeatable)")
    parser.add_argument("--xorg", action="store_true",
                        help="Run check-xorg.sh from mounted media and qualify PS/2 input/scanout")
    parser.add_argument("--desktop", action="store_true",
                        help="Run the installed Xiri user desktop on IMPACT after the native checks")
    parser.add_argument("--multiuser", action="store_true", help="Boot through rc.d and log in on serial B")
    parser.add_argument("--xdm", choices=("full", "greeter", "latency", "copy"), help="Check xdm, user desktops, desktop latency or overlap-safe window copies")
    parser.add_argument("--autoboot", action="store_true", help="Use saved firmware's automatic disk boot without PROM commands")
    parser.add_argument("--graphical-console", action="store_true", help="Use console=g with saved automatic-boot firmware; retain serial B login")
    parser.add_argument("--console-check", action="store_true", help="Exercise graphical text and debugger input before xdm checks")
    parser.add_argument("--frame-reference", type=Path, help="Check the framed 8x16 console against sgiconsole.png")
    parser.add_argument("--command-timeout", type=int, default=120)
    parser.add_argument("--display-bench", action="store_true",
                        help="Time visible fills and pixmap copies during the --xorg probe")
    args = parser.parse_args()
    if args.display_bench and (not args.xorg or not args.fixture_media):
        parser.error("--display-bench requires --xorg and --fixture-media")
    if args.xdm:
        args.multiuser = True
        if args.desktop or args.xorg:
            parser.error("xdm owns Xorg; do not combine it with manual display checks")
    if args.autoboot and (not args.firmware_dir or not args.multiuser):
        parser.error("--autoboot requires --firmware-dir and a multiuser boot")
    if args.graphical_console and not args.autoboot:
        parser.error("--graphical-console requires --autoboot and saved firmware")
    if args.console_check and not args.graphical_console:
        parser.error("--console-check requires --graphical-console")
    if args.frame_reference and not args.console_check:
        parser.error("--frame-reference requires --console-check")
    if args.xdm == "copy" and (args.machine != "ip28" or not args.fixture_media):
        parser.error("--xdm copy requires IP28 and --fixture-media")
    media = args.media or args.fixture_media
    if args.xdm == "full" and not media:
        parser.error("--xdm full requires fixture media containing type-ready.c")
    if args.xdm == "latency" and not (args.fixture_media and args.graphical_console):
        parser.error("--xdm latency requires --fixture-media and --graphical-console")
    if args.autoboot and args.tftp:
        parser.error("--autoboot qualifies disk boot, without TFTP")
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(__file__, out / "probe-used.py")
    if args.xdm:
        helper = {"latency": "desktop_latency", "copy": "window_copy"}.get(args.xdm, "xdm")
        shutil.copyfile(Path(__file__).with_name(helper + ".py"), out / (helper + "-used.py"))
    def sha(path):
        with path.open("rb") as stream:
            return hashlib.file_digest(stream, "sha256").hexdigest()

    disk_sha256 = sha(args.disk)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    # IP28's fixed EEPROM layout. The PROM fills in other defaults.
    nv = bytearray(256)
    nv[1] = 9 if args.machine == "ip28" else 8
    for at, value in [(2, "d"), (116, "9600"), (121, "0"), (122, "GMT0"),
                      (178, "N"), (232, "0"), (235, "0"), (236, "y"),
                      (239, "y"), (242, "1")]:
        nv[at:at + len(value)] = value.encode()
    nv[250:] = bytes.fromhex("080069123456")
    checksum = 0xa5
    for i in range(0, 256, 2):
        checksum ^= nv[i + 1] ^ (nv[i] if i else 0)
        checksum = ((checksum << 1) | (checksum >> 7)) & 255
    nv[0] = checksum
    (out / "nveeprom.bin").write_bytes(nv)
    if args.machine != "ip28":
        battery = bytearray(8192)
        battery[64:320] = nv
        (out / "nvram.bin").write_bytes(battery)
    if args.firmware_dir:
        for name in ("nvram.bin", "nveeprom.bin"):
            shutil.copyfile(args.firmware_dir / name, out / name)
    if args.graphical_console:
        nv = bytearray((out / "nveeprom.bin").read_bytes())
        nv[2] = ord("g")
        checksum = 0xa5
        for i in range(0, 256, 2):
            checksum ^= nv[i + 1] ^ (nv[i] if i else 0)
            checksum = ((checksum << 1) | (checksum >> 7)) & 255
        nv[0] = checksum
        (out / "nveeprom.bin").write_bytes(nv)
    firmware_seed_matches = bool(args.firmware_dir) and all(
        (out / name).read_bytes() == (args.firmware_dir / name).read_bytes()
        for name in ("nvram.bin", "nveeprom.bin"))
    # Reserve the three host ports until the configuration is written.
    ports = [socket.socket() for _ in range(3)]
    for port in ports:
        port.bind(("127.0.0.1", 0))
    sock = out / "ci.sock"
    cfg = f'''prom = "(embedded)"
nvram = "nvram.bin"
nveeprom = "nveeprom.bin"
banks = [512, 512, 0, 0]
headless = false
ci = true
ci_display = true
ci_socket = {json.dumps(str(sock))}
no_audio = true
serial_log = "serial.log"
scsi_deferred_int = true
monitor_port = {ports[0].getsockname()[1]}
serial_port_a = {ports[1].getsockname()[1]}
serial_port_b = {ports[2].getsockname()[1]}
nat_subnet = "192.168.0.0/24"
[machine]
profile = "indigo2_ip28"
cpu = "r10000"
[graphics]
board = "highimpact"
heads = 1
resolution = "guest"
raster = "wgpu"
gpu_backend = "vulkan"
[scsi.1]
path = {json.dumps(str(args.disk.resolve()))}
overlay = true
[network]
mode = "nat"
mac = "08:00:69:12:34:56"
'''
    if args.machine != "ip28":
        cfg = cfg.replace('banks = [512, 512, 0, 0]', 'banks = [128, 128, 0, 0]')
        cfg = cfg.replace('profile = "indigo2_ip28"', 'profile = "indy_ip24"')
        cfg = cfg.replace('cpu = "r10000"', 'cpu = ' + json.dumps(args.machine.split('-')[1]))
        cfg = cfg.replace('board = "highimpact"', 'board = "newport"')
        cfg = cfg.replace('raster = "wgpu"\n', '').replace('gpu_backend = "vulkan"\n', '')
        if args.machine == "indy-r5000" and args.xdm == "latency":
            cfg = cfg.replace('cpu = "r5000"', 'cpu = "r5000"\ncache = "shadow"')
    if media:
        cfg += f'[scsi.4]\npath = {json.dumps(str(media.resolve()))}\ncdrom = true\n'
    # tftp_dir belongs to the network table, not the optional CD-ROM.
    if args.tftp:
        cfg = cfg.replace('[network]\n', '[network]\ntftp_dir = ' + json.dumps(str(args.tftp.resolve())) + '\n')
    (out / "iris.toml").write_text(cfg)
    for port in ports:
        port.close()

    def rpc(cmd, **values):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(30)
            connection.connect(str(sock))
            connection.sendall((json.dumps({"cmd": cmd, "args": values}) + "\n").encode())
            result = json.loads(connection.makefile().readline())
        if not result.get("ok"):
            raise RuntimeError(result)
        return result.get("data")

    def monitor(commands):
        port = int(re.search(r"monitor_port = (\d+)", cfg)[1])
        with socket.create_connection(("127.0.0.1", port), timeout=15) as mon:
            def receive():
                data = b""
                while not re.search(rb"(^|\n)> $", data):
                    part = mon.recv(65536)
                    if not part:
                        break
                    data += part
                return data.decode("latin1")
            receive()
            result = {}
            for cmd in commands:
                mon.sendall((cmd + "\n").encode())
                result[cmd] = receive()
            return result

    def capture(name):
        path = out / (name + ".png")
        subprocess.run([str(args.iris.resolve().with_name("iris-ci")),
                        "--socket", str(sock), "screenshot", str(path)],
                       check=True, timeout=30, stdout=subprocess.DEVNULL)
        return path

    transcript = ""
    boot_captures = []
    boot_complete = False


    def wait(pattern, start=0, timeout=120):
        nonlocal transcript
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if args.graphical_console and not boot_complete:
                elapsed = time.monotonic() - started
                times = [8, 15, 25, 40, 60, 90, 130, 170]
                if len(boot_captures) < len(times) and elapsed >= times[len(boot_captures)]:
                    boot_captures.append(str(capture("boot-%03d" % times[len(boot_captures)])))
            part = rpc("serial-read") or ""
            if part:
                transcript += part
                (out / "driver.log").write_text(transcript)
            if re.search(pattern, transcript[start:]):
                return
            if process.poll() is not None:
                raise RuntimeError("IRIS exited before the expected response")
            time.sleep(0.2)
        raise TimeoutError(transcript[-2000:])

    def command(text):
        start = len(transcript)
        rpc("serial-send", data=text + "\r")
        wait(r">>\s", start)

    env = dict(os.environ, IRIS_NO_IDLE="1", IRIS_CHD_DIFF_DIR=str((args.overlay_dir or out).resolve()))
    result = {"disk": str(args.disk.resolve()), "kernel": args.kernel,
              "loader_transport": "tftp" if args.tftp else "scsi-volume-header",
              "multiuser": args.multiuser, "firmware_autoboot": args.autoboot,
              "graphical_console": args.graphical_console,
              "firmware_seed_matches": firmware_seed_matches,
              "machine": args.machine, "disk_sha256": disk_sha256,
              "script_sha256": sha(Path(__file__)), "passed": False}
    def interrupted(signum, frame):
        raise RuntimeError("Interrupted by signal " + str(signum))

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    started = time.monotonic()
    with (out / "emulator.log").open("w") as log:
        process = subprocess.Popen([str(args.iris.resolve()), "--config", str(out / "iris.toml")],
                                   cwd=out, env=env, stdin=subprocess.DEVNULL,
                                   stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        result["pid"] = process.pid
        try:
            deadline = time.monotonic() + 60
            while not sock.exists():
                if process.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError("IRIS control socket unavailable")
                time.sleep(0.2)
            rpc("start")
            start = len(transcript)
            if not args.autoboot:
                wait("Enter Command Monitor")
                command("5")
                if not args.firmware_dir:
                    command("setenv SystemPartition dksc(0,1,8)")
                    command("setenv OSLoader boot")
                    command("setenv OSLoadPartition dksc(0,1,0)")
                    command("setenv OSLoadFilename " + args.kernel)
                    command("setenv OSLoadOptions " + ("auto" if args.multiuser else "single"))
                    if args.multiuser:
                        command("setenv AutoLoad Yes")
                    command("setenv netaddr 192.168.0.2")
                start = len(transcript)
                boot_command = "boot -f bootp():" + args.kernel if args.tftp else "boot"
                rpc("serial-send", data=boot_command + "\r")
            wait(r"login: |Enter pathname of shell|(?<![\w.])panic:|Exception:|Stopped in pid|root device(?: \([^\r\n]+\))?:", start, timeout=180)
            if "root device" in transcript[start:]:
                for answer, prompt in (("sd0a", "dump device"), ("none", "file system"), ("ffs", "init path")):
                    step = len(transcript)
                    rpc("serial-send", data=answer + "\r")
                    wait(prompt + r"|(?<![\w.])panic:|Exception:|Stopped in pid", step)
                    if prompt not in transcript[step:]:
                        raise RuntimeError(transcript[step:])
                step = len(transcript)
                rpc("serial-send", data="\r")
                wait(r"Enter pathname of shell|(?<![\w.])panic:|Exception:|Stopped in pid", step)
            body = transcript[start:]
            if args.multiuser:
                if "login: " not in body:
                    raise RuntimeError(body[-4000:])
                rpc("serial-send", data="root\r")
                wait(r"(?:^|[\r\n])[^\r\n]*# ", len(transcript))
            else:
                if "Enter pathname of shell" not in body:
                    raise RuntimeError(body[-4000:])
                rpc("serial-send", data="\r")
                wait(r"(?:^|[\r\n])# ", start)
            result["boot_captures"] = boot_captures
            boot_complete = True
            if args.graphical_console:
                capture("boot-console")
            start_cmd = len(transcript)
            rpc("serial-send", data="uname -a; sysctl hw.model hw.ncpu; mount; /bin/echo XIRI_IP28_NATIVE_SHELL\r")
            wait(r"(?:^|[\r\n])XIRI_IP28_NATIVE_SHELL\r?\n", start_cmd)
            def shell(command, check=True):
                step = len(transcript)
                rpc("serial-send", data=command + "; printf '\\nXIRI_RC_%s\\n' \"$?\"\r")
                wait(r"(?:^|[\r\n])XIRI_RC_[0-9]+\r?\n|(?<![\w.])panic:" + ("" if args.console_check else "|Stopped in pid"), step,
                     timeout=args.command_timeout)
                body = transcript[step:]
                if check and not re.search(r"(?:^|[\r\n])XIRI_RC_0\r?\n", body):
                    raise RuntimeError(body[-4000:])
                return body
            result["identity"] = shell("uname -a; sysctl hw.model hw.ncpu hw.physmem64; mount")
            expected_model = "hw.model = SGI-IP28" if args.machine == "ip28" else "hw.model = SGI-IP22"
            if expected_model not in result["identity"]:
                raise RuntimeError("Unexpected machine identity")
            if args.kernel_sha256:
                result["installed_kernel"] = shell("/usr/bin/sha256 /netbsd.ip28")
                if "SHA256 (/netbsd.ip28) = " + args.kernel_sha256 not in result["installed_kernel"]:
                    raise RuntimeError("Installed kernel checksum mismatch")
            shell("/sbin/mount -u -w /")
            result["storage"] = shell("/bin/dd if=/bin/sh of=/ip28-test.tmp bs=64k && /usr/bin/cmp /bin/sh /ip28-test.tmp && /usr/bin/sha256 /ip28-test.tmp && /bin/rm /ip28-test.tmp && /bin/sync")
            result["timers"] = shell("/bin/date -u; /bin/sleep 2; /bin/date -u")
            result["processes"] = shell("/bin/sh -c 'i=0; while [ $i -lt 32 ]; do /bin/echo IP28_EXEC >/dev/null || exit; i=$((i+1)); done'")
            result["network"] = shell("/sbin/ifconfig sq0 inet 192.168.0.2 netmask 255.255.255.0 up && /sbin/ifconfig -w 20 && /sbin/ping -n -c 3 -w 5 192.168.0.1")
            result["network_state"] = shell("/sbin/ifconfig sq0; /usr/bin/netstat -in; /usr/sbin/arp -an")
            if media:
                shell("mkdir -p /cdrom && mount -t cd9660 -o ro /dev/cd0a /cdrom")
                shell("cd /cdrom && sha256 -c SHA256 && cd /")
            if args.media:
                result["installation"] = shell("install -m 444 /cdrom/netbsd /netbsd.ip28 && install -m 444 /cdrom/ip28boot /usr/mdec/ip28boot && /usr/mdec/sgivol -q -w boot /usr/mdec/ip28boot /dev/rsd0c && sha256 /netbsd.ip28 /usr/mdec/ip28boot && umount /cdrom && sync")
            if args.irix_module:
                import shlex
                shell("/sbin/modload " + shlex.quote(args.irix_module))
                result["irix_shell"] = shell("/emul/irix/bin/sh -c '/bin/echo XIRI_IRIX_SHELL_OK'")
            result["checks"] = [shell(command) for command in args.check_command]
            if args.console_check:
                shutil.copyfile(Path(__file__).with_name("console.py"), out / "console-used.py")
                from console import qualify_console
                result["console"] = {}
                qualify_console(shell, monitor, capture, result["console"], args.frame_reference)
            if args.xdm == "latency":
                from desktop_latency import qualify
                result["desktop_latency"] = {}
                qualify(shell, monitor, rpc, out, result["desktop_latency"])
            elif args.xdm == "copy":
                from window_copy import qualify
                result["window_copy"] = {}
                qualify(shell, monitor, out, result["window_copy"])
            elif args.xdm:
                from xdm import qualify
                result["xdm"] = {}
                qualify(shell, monitor, capture, args.xdm, result["xdm"])
            if args.xorg:
                result["xorg"] = shell("sh /cdrom/check-xorg.sh")
                # The Xlib probe has keyboard focus; exercise the actual PS/2 path.
                result["input_commands"] = monitor(["key type Xiri_123", "key Return",
                    "ps2 mouse 10 5 0", "ps2 mouse 0 0 1", "ps2 mouse 0 0 0",
                    "ps2 mouse 0 0 4", "ps2 mouse 0 0 0",
                    "ps2 mouse 0 0 2", "ps2 mouse 0 0 0"])
                result["input"] = shell("sleep 2; cat /var/tmp/ip28-xorg/probe.log; (set -e; grep -q TEXT_PASS /var/tmp/ip28-xorg/probe.log; grep -q 'KEY_UP Return' /var/tmp/ip28-xorg/probe.log; grep -q MOTION /var/tmp/ip28-xorg/probe.log; for b in 1 2 3; do grep -q \"BUTTON_DOWN $b \" /var/tmp/ip28-xorg/probe.log; grep -q \"BUTTON_UP $b \" /var/tmp/ip28-xorg/probe.log; done)")
                ci = args.iris.resolve().with_name("iris-ci")
                subprocess.run([str(ci), "--socket", str(sock), "screenshot",
                                str(out / "xorg.png")], check=True, timeout=30)
                result["scanout"] = monitor(["screen info"] +
                    [f"screen pix {100 + 120 * i} 160" for i in range(4)])
                # This image's Xorg allocates 0xfe components, as on Newport.
                for i, color in enumerate(("fe0000", "00fe00", "0000fe", "fefefe")):
                    pixel = result["scanout"][f"screen pix {100 + 120 * i} 160"]
                    got = re.search(r"= ([0-9a-fA-F]{6})", pixel)
                    if not got or got[1].lower() != color:
                        raise RuntimeError("Incorrect IMPACT scanout: " + pixel)
                if args.display_bench:
                    shutil.copyfile(Path(__file__).with_name("display_bench.py"), out / "display-bench-used.py")
                    from display_bench import qualify as qualify_display
                    result["display_bench"] = {}
                    qualify_display(shell, monitor, rpc, capture, result["display_bench"])
                result["xorg_shutdown"] = shell("kill $(cat /var/tmp/ip28-xorg/probe-pid); kill $(cat /var/tmp/ip28-xorg/xpid); sleep 2; ! pgrep -x Xorg")
            if args.desktop:
                result["desktop"] = shell("sh /cdrom/check-desktop.sh")
                ci = args.iris.resolve().with_name("iris-ci")
                subprocess.run([str(ci), "--socket", str(sock), "screenshot",
                                str(out / "desktop.png")], check=True, timeout=30)
                result["desktop_shutdown"] = shell("touch $(cat /var/tmp/ip28-desktop/job)/logout; i=0; while pgrep -x Xorg >/dev/null; do i=$((i+1)); test $i -lt 60 || break; sleep 1; done; ! pgrep -x Xorg")
            result["dmesg"] = shell("dmesg")
            if args.graphical_console and not re.search(r"wsdisplay0.*console", result["dmesg"]):
                raise RuntimeError("Native graphics console missing from kernel log")
            if re.search(r"command FIFO timeout|(?<![\w.])panic:|WARNING: module error", result["dmesg"]):
                raise RuntimeError("Driver or module error in kernel log")
            halt_start = len(transcript)
            rpc("serial-send", data=("/sbin/shutdown -h now" if args.multiuser else "/sbin/halt") + "\r")
            if args.graphical_console:
                # Graphical PROM output is intentionally absent from serial B.
                # Require sustained execution in ROM, then retain the menu PNG.
                deadline = time.monotonic() + 180
                samples = []
                while time.monotonic() < deadline:
                    transcript += rpc("serial-read") or ""
                    regs = monitor(["regs"])["regs"]
                    match = re.search(r"PC: 0x([0-9a-fA-F]+)", regs)
                    pc = int(match[1], 16) & 0x1fffffff if match else 0
                    if 0x1fc00000 <= pc < 0x1fc80000:
                        samples.append(regs)
                        if len(samples) == 3:
                            break
                    else:
                        samples = []
                    time.sleep(2)
                if len(samples) != 3:
                    raise RuntimeError("Shutdown did not return to the PROM")
                result["shutdown_prom_samples"] = samples
                result["shutdown_png"] = str(capture("shutdown-prom"))
                result["shutdown"] = transcript[halt_start:]
            else:
                wait(r"System Maintenance Menu|(?<![\w.])panic:|Stopped in pid", halt_start, timeout=180)
                result["shutdown"] = transcript[halt_start:]
                if "System Maintenance Menu" not in result["shutdown"] or "halting..." not in result["shutdown"]:
                    raise RuntimeError(result["shutdown"])
            result.update(passed=True, evidence=transcript[start:])
        except Exception as error:
            result["error"] = str(error)
            if args.xdm:
                try:
                    args.command_timeout = 10
                    result["failure_diagnostics"] = shell("tail -60 /var/log/xdm.log; ps -ax -o pid,ppid,uid,comm; dmesg", check=False)
                except Exception:
                    pass
        finally:
            if not result["passed"] and (args.xorg or args.desktop or args.xdm or args.graphical_console):
                try:
                    subprocess.run([str(args.iris.resolve().with_name("iris-ci")),
                                    "--socket", str(sock), "screenshot",
                                    str(out / "failure.png")], check=True, timeout=30)
                except (OSError, subprocess.SubprocessError):
                    pass
            if not result["passed"] and "shell" in locals():
                try:
                    rpc("serial-send", data="\x03")
                    time.sleep(0.5)
                    rpc("serial-send", data=("/sbin/shutdown -h now" if args.multiuser else "/sbin/halt") + "\r")
                    deadline = time.monotonic() + 45
                    while time.monotonic() < deadline:
                        regs = monitor(["regs"])["regs"]
                        match = re.search(r"PC: 0x([0-9a-fA-F]+)", regs)
                        pc = int(match[1], 16) & 0x1fffffff if match else 0
                        if 0x1fc00000 <= pc < 0x1fc80000:
                            result["failure_cleanup_returned_to_prom"] = True
                            break
                        time.sleep(1)
                except Exception as error:
                    result["failure_cleanup_error"] = str(error)
            try:
                port = int(re.search(r"monitor_port = (\d+)", cfg)[1])
                with socket.create_connection(("127.0.0.1", port), timeout=8) as mon:
                    def receive():
                        data = b""
                        while not re.search(rb"(^|\n)> $", data):
                            part = mon.recv(65536)
                            if not part:
                                break
                            data += part
                        return data.decode("latin1")
                    receive()
                    snapshot = {}
                    for cmd in ("stop", "regs", "cop0", "dis pc 12", "dt 12", "mc regs", "seeq status", "hpc3 status", "net status all"):
                        mon.sendall((cmd + "\n").encode())
                        snapshot[cmd] = receive()
                    (out / "monitor.json").write_text(json.dumps(snapshot, indent=2) + "\n")
            except Exception as error:
                result["monitor_error"] = str(error)
            try:
                rpc("quit")
            except (OSError, ValueError, RuntimeError):
                pass
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=10)
            result["base_unchanged"] = sha(args.disk) == disk_sha256
            if not result["base_unchanged"]:
                result.update(passed=False, error="Base disk changed")
            result.update(exit_code=process.returncode, elapsed_seconds=round(time.monotonic() - started, 2))
            (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result.get(key) for key in
                      ("passed", "machine", "kernel", "elapsed_seconds", "error")}, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
