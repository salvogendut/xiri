#!/usr/bin/env python3
"""Qualify a native IP28 kernel on a private overlay, then halt and stop IRIS.

The disk is read through a private copy-on-write overlay. A serial PROM console
is intentional: this qualifies native boot and I/O, not an IMPACT desktop.
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
    parser.add_argument("--media", type=Path, help="Read-only ISO with netbsd and ip28boot for installation")
    parser.add_argument("--firmware-dir", type=Path, help="Use saved nvram/nveeprom and boot without resetting PROM variables")
    parser.add_argument("--overlay-dir", type=Path, help="Reuse a prepared private disk overlay")
    parser.add_argument("--machine", choices=("ip28", "indy-r4400", "indy-r5000"), default="ip28")
    parser.add_argument("--irix-module", help="Indy regression only: load this existing module and run IRIX sh")
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(__file__, out / "probe-used.py")
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
    if args.media:
        cfg += f'[scsi.4]\npath = {json.dumps(str(args.media.resolve()))}\ncdrom = true\n'
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

    transcript = ""

    def wait(pattern, start=0, timeout=120):
        nonlocal transcript
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
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
            wait("Enter Command Monitor")
            command("5")
            if not args.firmware_dir:
                command("setenv SystemPartition dksc(0,1,8)")
                command("setenv OSLoader boot")
                command("setenv OSLoadPartition dksc(0,1,0)")
                command("setenv OSLoadFilename " + args.kernel)
                command("setenv OSLoadOptions single")
                command("setenv netaddr 192.168.0.2")
            start = len(transcript)
            boot_command = "boot -f bootp():" + args.kernel if args.tftp else "boot"
            rpc("serial-send", data=boot_command + "\r")
            wait(r"Enter pathname of shell|panic:|Exception:|Stopped in pid|root device(?: \([^\r\n]+\))?:", start)
            if "root device" in transcript[start:]:
                for answer, prompt in (("sd0a", "dump device"), ("none", "file system"), ("ffs", "init path")):
                    step = len(transcript)
                    rpc("serial-send", data=answer + "\r")
                    wait(prompt + r"|panic:|Exception:|Stopped in pid", step)
                    if prompt not in transcript[step:]:
                        raise RuntimeError(transcript[step:])
                step = len(transcript)
                rpc("serial-send", data="\r")
                wait(r"Enter pathname of shell|panic:|Exception:|Stopped in pid", step)
            body = transcript[start:]
            if "Enter pathname of shell" not in body:
                raise RuntimeError(body[-4000:])
            rpc("serial-send", data="\r")
            wait(r"(?:^|\n)# ", start)
            start_cmd = len(transcript)
            rpc("serial-send", data="uname -a; sysctl hw.model hw.ncpu; mount; /bin/echo XIRI_IP28_NATIVE_SHELL\r")
            wait(r"(?:^|[\r\n])XIRI_IP28_NATIVE_SHELL\r?\n", start_cmd)
            def shell(command, check=True):
                step = len(transcript)
                rpc("serial-send", data=command + "; printf '\\nXIRI_RC_%s\\n' \"$?\"\r")
                wait(r"(?:^|[\r\n])XIRI_RC_[0-9]+\r?\n|panic:|Stopped in pid", step)
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
            if args.media:
                shell("mkdir -p /cdrom && mount -t cd9660 -o ro /dev/cd0a /cdrom")
                shell("cd /cdrom && sha256 -c SHA256 && cd /")
                result["installation"] = shell("install -m 444 /cdrom/netbsd /netbsd.ip28 && install -m 444 /cdrom/ip28boot /usr/mdec/ip28boot && /usr/mdec/sgivol -q -w boot /usr/mdec/ip28boot /dev/rsd0c && sha256 /netbsd.ip28 /usr/mdec/ip28boot && umount /cdrom && sync")
            if args.irix_module:
                import shlex
                shell("/sbin/modload " + shlex.quote(args.irix_module))
                result["irix_shell"] = shell("/emul/irix/bin/sh -c '/bin/echo XIRI_IRIX_SHELL_OK'")
            halt_start = len(transcript)
            rpc("serial-send", data="/sbin/halt\r")
            wait(r"System Maintenance Menu|panic:|Stopped in pid", halt_start)
            result["shutdown"] = transcript[halt_start:]
            if "System Maintenance Menu" not in result["shutdown"] or "halting..." not in result["shutdown"]:
                raise RuntimeError(result["shutdown"])
            result.update(passed=True, evidence=transcript[start:])
        except Exception as error:
            result["error"] = str(error)
        finally:
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
