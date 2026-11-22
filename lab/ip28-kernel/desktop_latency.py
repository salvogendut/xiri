"""Measure completed 4Dwm moves and winterm scrolls on the emulated scanout."""
import re
import statistics
import time

import numpy as np
from PIL import Image


def qualify(shell, monitor, rpc, out, result):
    result.update(passed=False)
    shell("export PATH=/usr/local/sbin:/usr/local/bin:/usr/X11R7/bin:/sbin:/usr/sbin:/bin:/usr/bin; "
          "test -s /var/run/xdm.pid && kill -0 $(cat /var/run/xdm.pid)")
    shell("f=/usr/people/xiritest/.Sgiresources; touch \"$f\" && chown xiritest \"$f\" && "
          "printf '\\n4Dwm*moveOpaque: True\\n' >> \"$f\" && rm -f /usr/people/xiritest/.xsession-errors")
    shell("export DISPLAY=:0; XAUTHORITY=$(ps -axww -o args= | awk '$1 == \"/usr/X11R7/bin/Xorg\" "
          "{for (i=1;i<NF;i++) if ($i == \"-auth\") print $(i+1)}'); export XAUTHORITY; "
          "(i=0; until xwininfo -name xlogin >/dev/null 2>&1; do i=$((i+1)); test $i -lt 60 || exit 1; sleep 1; done)")
    monitor(["key type xiritest", "key Return", "key type xiritest", "key Return"])
    shell("(i=0; until grep -q 'Logs: ' /usr/people/xiritest/.xsession-errors; do "
          "i=$((i+1)); test $i -lt 120 || exit 1; sleep 1; done)")
    proof = shell(". /cdrom/start-latency.sh")
    ready = re.search(r"^READY (\d+) (\d+) (\d+) (\d+) (\d+) (\d+)\r?$", proof, re.M)
    if not ready:
        raise RuntimeError("Missing mapped winterm geometry: " + proof)
    x, y, w, h, rows, cols = map(int, ready.groups())
    result.update(client=[x, y, w, h], terminal=[cols, rows])
    result["xorg"] = shell("xdpyinfo | grep dimensions; grep -Ei 'LoadModule: \"(newport|wsfb)\"|XAA acceleration' /var/log/Xorg.0.log")
    result["identity"] = shell('cat "$job/identity" "$job/handoff"; pgrep -u xiritest -lf 4Dwm')
    def counters():
        if 'LoadModule: "wsfb"' not in result["xorg"]:
            return {}
        stats = monitor(["mgras stats"])["mgras stats"]
        fields = {"hq3_words": r"HQ3: (\d+) words", "raster_writes": r"raster writes (\d+)",
                  "pio_dwords": r"PIO dw written (\d+)", "fast_fills": r"fast fills (\d+)",
                  "dma_bytes": r"reads \d+, (\d+) bytes"}
        return {key: int(re.search(pattern, stats)[1]) for key, pattern in fields.items()}
    if not re.search(r"dimensions:\s+1280x1024 pixels", result["xorg"]):
        raise RuntimeError("Desktop dimensions differ from the 1280x1024 reference")
    # Warm patterns occupy more than a full terminal. Keep the dynamic
    # status/caret rows and the title-bar pointer out of the comparison.
    def command(c):
        rpc("serial-send", data=f"echo {c} >&7\r")

    def location():
        body = shell("echo g >&7; sleep 1; grep '^POSITION ' bench.log | tail -1")
        coords = re.search(r"^POSITION (\d+) (\d+)\r?$", body, re.M)
        if not coords:
            raise RuntimeError("Missing winterm position: " + body)
        return list(map(int, coords.groups()))

    def measure(name, a, b, box):
        # Read the composed guest display. The same cropped monitor request
        # supplies both timing and correctness on the two graphics boards.
        path = out / (name + "-sample.png")
        def capture(label=None):
            dest = out / (name + "-" + label + ".png") if label else path
            cmd = f"screen shot {dest} " + " ".join(map(str, box))
            reply = monitor([cmd])[cmd]
            if "saved " not in reply:
                raise RuntimeError("Could not read current scanout: " + reply)
            with Image.open(dest) as img:
                if img.size != tuple(box[2:]):
                    raise RuntimeError(f"Wrong crop size {img.size}")
                return np.asarray(img.convert("RGB"))

        refs = []
        for phase, action in enumerate((a, b, a, b)):
            # Initial state is A. The scroll stimulus toggles on every write.
            if phase:
                command(action)
            time.sleep(1.5)
            refs.append(capture("cal-" + str(phase)))
            if name == "drag":
                actual = location()
                expected = [x + (phase % 2) * 112, y]
                if actual != expected:
                    raise RuntimeError(f"Opaque 4Dwm move: expected {expected}, got {actual}")
        changed = ((refs[0] != refs[1]).any(axis=2) &
                   (refs[0] == refs[2]).all(axis=2) & (refs[1] == refs[3]).all(axis=2))
        n = int(changed.sum())
        if n < 1000:
            raise RuntimeError(f"{name}: only {n} stable changed pixels")
        expected = [img[changed] for img in refs[:2]]
        if name == "scroll":
            # Compare glyph pixels that actually changed. After eight lines of
            # PTY output, the old lower rows must be the new upper rows.
            shift = 8 * round(h / rows)
            old, new = (im[:, 24:-32] for im in refs[:2])
            moved = (old[shift:] != new[shift:]).any(axis=2)
            matches = (old[shift:][moved] == new[:-shift][moved]).all(axis=1)
            if len(matches) < 100 or matches.mean() < .98:
                raise RuntimeError("Scrolled glyphs did not move up by eight text rows")
            result["scroll_shift"] = dict(pixels=shift, compared=len(matches),
                                          fraction=float(matches.mean()))
        samples, lower_bounds, reads, costs = [], [], [], []
        baseline = counters()
        time.sleep(1)
        start_counts = counters()
        for i in range(8):
            phase = i % 2
            # The previous phase must still be on screen when timing starts.
            before = capture()[changed]
            if (before == expected[1-phase]).all(axis=1).mean() < .98:
                raise RuntimeError(f"{name}: unstable precondition before sample {i}")
            start = time.monotonic()
            last_miss = 0.0
            command((a,b)[phase])
            for poll in range(1, 501):
                t = time.monotonic()
                frame = capture()
                costs.append(round((time.monotonic()-t)*1000, 2))
                fraction = (frame[changed] == expected[phase]).all(axis=1).mean()
                elapsed = time.monotonic()-start
                if fraction >= .98:
                    samples.append(round(elapsed*1000, 2))
                    lower_bounds.append(round(last_miss*1000, 2))
                    reads.append(poll)
                    break
                if elapsed > 12:
                    raise RuntimeError(f"{name}: only {fraction:.3f} matched at {elapsed:.2f}s")
                last_miss = t - start
                time.sleep(.005)
            else:
                raise RuntimeError(f"{name}: scanout poll limit")
        result[name] = dict(samples_ms=samples, median_ms=statistics.median(samples),
                            changed_pixels=n, scanout_fraction=.98, crop=box,
                            polls=reads, median_read_ms=statistics.median(costs),
                            last_miss_request_ms=lower_bounds)
        if start_counts:
            end_counts = counters()
            result[name]["impact_counts"] = {k: end_counts[k] - v for k,v in start_counts.items()}
            result[name]["idle_counts_1s"] = {k: start_counts[k] - v for k,v in baseline.items()}

    try:
        command("b")
        time.sleep(.5)
        measure("drag", "l", "r", [x, y+10, w+112, h-32])
        command("e")
        time.sleep(.5)
        if location() != [x+112, y]:
            raise RuntimeError("Moved window did not retain its final position")
        measure("scroll", "s", "s", [x+112+10, y+10, w-32, h-36])
        result["passed"] = True
    finally:
        shell("echo q >&7; exec 7>&-; wait \"$bench_pid\"")
