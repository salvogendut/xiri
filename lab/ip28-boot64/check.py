#!/usr/bin/env python3
"""Run one IP28 loader check in a private IRIS directory, then stop IRIS.

The disk is read through a private copy-on-write overlay. A serial PROM console
is intentional: this checks the standalone loader, not the graphical desktop.
"""
import argparse
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
    parser.add_argument("--kernel", default="xiri-ip28-probe")
    parser.add_argument("--tftp", type=Path, help="Directory containing ip28boot; otherwise boot the disk header")
    parser.add_argument("--expect", choices=("handoff", "wrong-address"), default="handoff")
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    # IP28's fixed EEPROM layout. The PROM fills in other defaults.
    nv = bytearray(256)
    nv[1] = 9
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
    if args.tftp:
        cfg += f'tftp_dir = {json.dumps(str(args.tftp.resolve()))}\n'
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

    env = dict(os.environ, IRIS_NO_IDLE="1", IRIS_CHD_DIFF_DIR=str(out))
    result = {"disk": str(args.disk.resolve()), "kernel": args.kernel,
              "loader_transport": "tftp" if args.tftp else "scsi-volume-header",
              "expected": args.expect, "passed": False}
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
            command("setenv OSLoadPartition scsi(0)disk(1)rdisk(0)partition(0)")
            command("setenv OSLoadFilename " + args.kernel)
            command("setenv OSLoadOptions auto")
            command("setenv netaddr 192.168.0.2")
            start = len(transcript)
            loader = "bootp():ip28boot" if args.tftp else "scsi(0)disk(1)rdisk(0)partition(8)boot"
            rpc("serial-send", data="boot -f " + loader + "\r")
            marker = ("XIRI_IP28_LOADER_HANDOFF_PASS: data BSS argv bootinfo"
                      if args.expect == "handoff" else "Use a kernel linked for this machine.")
            wait(re.escape(marker), start)
            wait(r">>\s|System Maintenance Menu", start)
            body = transcript[start:]
            if "XIRI_IP28_LOADER_HANDOFF_FAIL" in body or "Exception:" in body:
                raise RuntimeError(body)
            result.update(passed=True, returned_to_prom=True, evidence=body)
        except Exception as error:
            result["error"] = str(error)
        finally:
            try:
                rpc("quit")
            except (OSError, ValueError, RuntimeError):
                pass
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=10)
            result.update(exit_code=process.returncode, elapsed_seconds=round(time.monotonic() - started, 2))
            (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
