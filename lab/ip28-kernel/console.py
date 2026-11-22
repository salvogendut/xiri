"""Native IMPACT text-console/keyboard/DDB checks on a disposable guest."""
import hashlib
import re
import time
from pathlib import Path


def qualify_console(shell, monitor, capture, result, frame_reference=None):
    result.update(passed=False)

    def settled_capture(name):
        # Synchronous DDB repaint can take several seconds on emulated IMPACT.
        # Retain the completed frame instead of a partially redrawn console.
        deadline = time.monotonic() + 60
        last, stable = None, 0
        while time.monotonic() < deadline:
            path = capture(name)
            digest = hashlib.sha256(path.read_bytes()).digest()
            stable = stable + 1 if digest == last else 0
            if stable >= 3:
                return str(path)
            last = digest
            time.sleep(1)
        raise RuntimeError("Debugger display did not settle")

    shell("/etc/rc.d/xdm onestop; sleep 2; ! pgrep -x Xorg")
    result["attachment"] = shell("dmesg | grep -E 'wsdisplay0|wskbd0|IMPACT'")
    if not re.search(r"wsdisplay0.*console", result["attachment"]):
        raise RuntimeError("Native IMPACT console was not attached")
    shell("printf '\\nXIRI IMPACT console: text before Xorg\\n' >/dev/console")
    result["text_png"] = str(capture("native-console"))
    if frame_reference:
        from frame import load_reference, check, check_scroll
        reference = load_reference(frame_reference)
        result["frame"] = {"after_xorg": check(reference, Path(result["text_png"]))}
        result["frame"]["scroll"] = check_scroll(shell, capture, reference)
    shell("set +m; rm -f /var/tmp/ip28-console-proof; /usr/libexec/getty Pc ttyE0 >/var/tmp/ip28-console-getty.log 2>&1 & echo $! >/var/tmp/ip28-console-getty.pid; sleep 2")
    monitor(["key type root", "key Return"])
    shell("(n=0; until pgrep -t ttyE0 -x '(-)?sh' >/dev/null; do n=$((n+1)); test $n -lt 30 || exit 1; sleep 1; done) && sleep 2")
    monitor(["key type id > /var/tmp/ip28-console-proof", "key Return"])
    result["keyboard"] = shell("(n=0; until test -s /var/tmp/ip28-console-proof; do n=$((n+1)); test $n -lt 15 || exit 1; sleep 1; done) && cat /var/tmp/ip28-console-proof; grep -q 'uid=0(root)' /var/tmp/ip28-console-proof")
    result["keyboard_png"] = str(capture("console-keyboard"))
    shell("sysctl -w ddb.fromconsole=1 ddb.tee_msgbuf=1")
    monitor(["key ctrl+alt+Escape"])
    settled_capture("console-ddb-ready")
    monitor(["key type print/x 0x1234abcd", "key Return"])
    result["ddb_png"] = settled_capture("console-ddb")
    monitor(["key type continue", "key Return"])
    # DDB must really have executed the command, not just echoed shell input.
    result["ddb"] = shell("sleep 2; dmesg | grep -E '^(db>|[[:space:]]*1234abcd)' ; dmesg | grep -Eq '^(db>[[:space:]]*)?[[:space:]]*1234abcd[[:space:]]*$'")
    if frame_reference:
        checks = result["frame"]
        checks["ddb"] = check(reference, Path(result["ddb_png"]))
        if not all(item["passed"] for item in checks.values()):
            raise RuntimeError(f"Framed console mismatch: {checks}")
    monitor(["key type exit", "key Return"])
    shell("(n=0; while kill -0 $(cat /var/tmp/ip28-console-getty.pid) 2>/dev/null; do n=$((n+1)); test $n -lt 30 || exit 1; sleep 1; done) && rm -f /var/tmp/ip28-console-proof /var/tmp/ip28-console-getty.pid /var/tmp/ip28-console-getty.log")
    shell("set -m; sed 's/^xdm=.*/xdm=YES/' /etc/rc.conf.d/xdm >/etc/rc.conf.d/xdm.ip28-new && mv /etc/rc.conf.d/xdm.ip28-new /etc/rc.conf.d/xdm; /etc/rc.d/xdm start")
    result["passed"] = True
