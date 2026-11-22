"""Native xdm checks shared by IP28 preparation and packaged-image boots.

The accounts/passwords below are existing public disposable image fixtures.
Authentication uses real PS/2 typing into native xdm; XTest is only used for
terminal commands after login. No runtime or user login files are replaced.
"""
import hashlib
import re
import shlex

from PIL import Image


def qualify(shell, monitor, capture, mode, result):
    result.update(passed=False, mode=mode, screenshots={}, sessions=[])

    def read(command):
        body = shell("printf '\\nIP28_DATA_BEGIN\\n'; (" + command +
                     "); ip28_status=$?; printf '\\nIP28_DATA_END\\n'; test \"$ip28_status\" = 0")
        match = re.search(r"\nIP28_DATA_BEGIN\n(.*?)\nIP28_DATA_END\n", body.replace("\r", ""), re.S)
        if not match:
            raise RuntimeError("Missing command data: " + body)
        return match[1].strip()

    def wait_for(command, seconds=120):
        shell("(ip28_tries=0; until { " + command +
              "; } >/dev/null 2>&1; do ip28_tries=$((ip28_tries+1)); "
              "test \"$ip28_tries\" -lt " + str(seconds) + " || exit 1; sleep 1; done)")

    def server_auth():
        shell("export DISPLAY=:0; XAUTHORITY=$(ps -axww -o args= | "
              "awk '$1 == \"/usr/X11R7/bin/Xorg\" {for (i=1;i<NF;i++) if ($i == \"-auth\") print $(i+1)}'); "
              "export XAUTHORITY; test -s \"$XAUTHORITY\"")

    def dimensions():
        value = read("xdpyinfo | grep dimensions:")
        if not re.search(r"dimensions:\s+1280x1024 pixels", value):
            raise RuntimeError("Wrong X screen size: " + value)
        return value

    def screenshot(name, tree=None):
        shell("sleep 2")
        path = capture(name)
        frame = Image.open(path).convert("RGB")
        if frame.size != (1280, 1024):
            raise RuntimeError("Wrong scanout size: " + str(frame.size))
        entry = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "size": list(frame.size)}
        if tree is not None:
            match = re.search(r'"xlogin".*?\s(\d+)x(\d+)\+(\d+)\+(\d+)', tree)
            if not match:
                raise RuntimeError("Missing graphical login window")
            width, height, x, y = map(int, match.groups())
            crop = frame.crop((x + 20, y + 15, x + 20 + width // 2, y + height - 15))
            pixels = list(crop.getdata())
            dark = sum(max(p) < 80 for p in pixels)
            light = sum(min(p) > 200 for p in pixels)
            if not (500 < dark < len(pixels) // 4 and light > len(pixels) // 2):
                raise RuntimeError(f"Greeter text/background check failed: dark={dark}, light={light}")
            entry.update(greeter_dark_pixels=dark, greeter_light_pixels=light)
        result["screenshots"][name] = entry

    def greeter():
        wait_for('test -s /tmp/.X0-lock && kill -0 "$(cat /tmp/.X0-lock)"', 60)
        server_auth()
        wait_for("xwininfo -root -tree | grep '\"xlogin\"'")
        shell("! pgrep -u 1234 -f '^/emul/irix/usr/bin/X11/4Dwm( |$)' && "
              "/usr/local/libexec/xiri/x11-check vacant")
        dimensions()
        return read("xwininfo -root -tree")

    def services():
        return read("cat /var/run/xdm.pid /var/run/xiri_famd.pid /var/run/rpcbind.pid").splitlines()

    def services_unchanged():
        current = services()
        if current != result["service_pids"]:
            raise RuntimeError("System services restarted across desktop logout")
        shell("kill -0 " + " ".join(str(int(pid)) for pid in current))

    def login(user):
        # These accounts already exist in the input images.
        home = "/home/netbsdtest" if user == "netbsdtest" else "/usr/people/" + user
        shell("rm -f " + home + "/.xsession-errors")
        monitor(["key type " + user, "key Return", "key type " + user, "key Return"])

    def type_text(display, window, text):
        shell(shlex.join(["/var/tmp/ip28-xdm/type", display, window, text]))

    def irix_session(label):
        login("xiritest")
        wait_for('grep -q "Logs: " /usr/people/xiritest/.xsession-errors')
        shell('job=$(sed -n "s/.*Logs: //p" /usr/people/xiritest/.xsession-errors | head -1); '
              'test -d "$job"; XAUTHORITY=$(sed -n "s/.* authority=//p" "$job/identity"); '
              'test "$XAUTHORITY" != default || XAUTHORITY=/usr/people/xiritest/.Xauthority; '
              'export XAUTHORITY DISPLAY=127.0.0.1:0; test -r "$XAUTHORITY"')
        wait_for('test -s "$job/handoff" && /usr/local/libexec/xiri/x11-check ready')
        wait_for('xwininfo -name winterm && xwininfo -root -tree | grep "of [0-9][0-9]*)"')
        shell("shell_pid=$(sed -n 's/^NATIVE_HANDOFF pid=\\([0-9][0-9]*\\).*/\\1/p' \"$job/handoff\")")
        wait_for('ps -p "$shell_pid" -o comm= | grep -Eq \'^[[:space:]]*sh[[:space:]]*$\'')
        shell("sleep 3")
        type_text("127.0.0.1:0", "winterm",
                  '(id -un; id -u; echo "$HOME"; pwd; id -G; echo "${XAUTHORITY:-$HOME/.Xauthority}") > "$XIRI_SESSION_DIR/ip28-shell"\n')
        wait_for('test -s "$job/ip28-shell"', 30)
        proof = read('cat "$job/ip28-shell"').splitlines()
        if proof[:4] != ["xiritest", "1234", "/usr/people/xiritest", "/usr/people/xiritest"]:
            raise RuntimeError("Wrong IRIX session identity: " + repr(proof))
        if "1235" not in proof[4].split() or proof[5] != read('printf "%s" "$XAUTHORITY"'):
            raise RuntimeError("IRIX session lost groups or X authority")
        shell("if XAUTHORITY=/dev/null xdpyinfo >/dev/null 2>&1; then exit 1; fi")
        entry = {"user": "xiritest", "proof": proof, "dimensions": dimensions(), "label": label,
                 "identity": read('cat "$job/identity"'), "unauthenticated_x_rejected": True}
        screenshot(label)
        # The user-facing command requests the normal supervisor/save path.
        type_text("127.0.0.1:0", "winterm", '(sleep 2; /usr/local/bin/xiri-logout) &\n')
        tree = greeter()
        wait_for("! pgrep -u 1234", 45)
        services_unchanged()
        entry["logout_returned_to_greeter"] = True
        result["sessions"].append(entry)
        return tree

    shell("export PATH=/usr/local/sbin:/usr/local/bin:/usr/X11R7/bin:/sbin:/usr/sbin:/bin:/usr/bin")
    result["boot_services"] = read("/etc/rc.d/xdm status && /etc/rc.d/xiri_famd status && "
                                   "/etc/rc.d/rpcbind status && test -f /var/run/xiri-pty-ready && "
                                   "modstat | grep -E '^compat_irix_o32[[:space:]]+exec[[:space:]]+filesys'")
    shell('test "$(sysctl -n kern.securelevel)" = 1')
    result["boot_order"] = read("rcorder /etc/rc.d/* | grep -E '/(wscons|xdm|xiri_devices|xiri_famd|modules)$'").splitlines()
    if result["boot_order"].index("/etc/rc.d/wscons") > result["boot_order"].index("/etc/rc.d/xdm"):
        raise RuntimeError("wscons must prepare the display before xdm")
    result["service_pids"] = services()
    result["greeter"] = greeter()
    screenshot("xdm-greeter", result["greeter"])
    if mode == "greeter":
        result["passed"] = True
        return result

    shell("mkdir -p /var/tmp/ip28-xdm && cc -O2 -Wall -Wextra -Werror "
          "-I/usr/X11R7/include -L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib "
          "/cdrom/type-ready.c -lX11 -lXtst -o /var/tmp/ip28-xdm/type")
    irix_session("xdm-irix")
    shell("test ! -e /home/netbsdtest/.xsession && rm -f /home/netbsdtest/ip28-proof /home/netbsdtest/ip28-groups")
    login("netbsdtest")
    wait_for("pgrep -u 1236 -f '^/usr/X11R7/bin/ctwm( |$)'")
    server_auth()
    wait_for("xwininfo -root -tree | grep '\"UXTerm\"'")
    tree = read("xwininfo -root -tree")
    terminal = re.search(r'"([^"\n]+)": \("[^"\n]*" "UXTerm"\)', tree)
    if not terminal:
        raise RuntimeError("Native terminal missing")
    type_text(":0", terminal[1], '(id -un; id -u; echo "$HOME"; pwd) > "$HOME/ip28-proof"; id -Gn > "$HOME/ip28-groups"\n')
    wait_for("test -s /home/netbsdtest/ip28-proof && test -s /home/netbsdtest/ip28-groups", 30)
    proof = read("cat /home/netbsdtest/ip28-proof").splitlines()
    groups = read("cat /home/netbsdtest/ip28-groups").split()
    if proof != ["netbsdtest", "1236", "/home/netbsdtest", "/home/netbsdtest"] or "wheel" not in groups:
        raise RuntimeError("Wrong native session identity/groups: " + repr((proof, groups)))
    shell("! pgrep -u 1236 -f '^/emul/irix/'")
    entry = {"user": "netbsdtest", "proof": proof, "groups": groups, "dimensions": dimensions(), "wm": "ctwm"}
    screenshot("xdm-native")
    wait_for("test \"$(pgrep -u 1236 -f '^/usr/X11R7/bin/ctwm( |$)' | wc -l)\" -eq 1", 30)
    wm_pid = int(read("pgrep -u 1236 -f '^/usr/X11R7/bin/ctwm( |$)'"))
    type_text(":0", terminal[1], f"(sleep 2; kill -TERM {wm_pid}) &\n")
    greeter()
    wait_for("! pgrep -u 1236", 45)
    services_unchanged()
    entry["logout_returned_to_greeter"] = True
    result["sessions"].append(entry)
    final_tree = irix_session("xdm-irix-retry")
    screenshot("xdm-after-logout", final_tree)
    shell("rm -f /home/netbsdtest/ip28-proof /home/netbsdtest/ip28-groups; rm -rf /var/tmp/ip28-xdm")
    result["passed"] = True
    return result
