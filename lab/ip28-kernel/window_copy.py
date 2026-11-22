"""Compare XCopyArea's visible destination with a snapshot of its source."""
import re
import time

import numpy as np
from PIL import Image


def counters(monitor):
    raw = monitor(["mgras stats"])["mgras stats"]
    dma = re.search(r"DMA: register writes \d+, writes (\d+), reads (\d+), (\d+) bytes", raw)
    pio = re.search(r"PIO dw written (\d+) read (\d+)", raw)
    if not dma or not pio:
        raise ValueError("Missing IMPACT transfer counters")
    return dict(zip(("dma_writes", "dma_reads", "dma_bytes", "pio_written", "pio_read"),
                    map(int, (*dma.groups(), *pio.groups()))))


def difference(new, old):
    return {key: value - old[key] for key, value in new.items()}


def exercise(exchange, monitor, out, count, result, *, ram):
    def pixels():
        path = out / "window-copy.png"
        cmd = f"screen shot {path} 192 128 192 128"
        if "saved " not in monitor([cmd])[cmd]:
            raise RuntimeError("Could not capture copy probe window")
        with Image.open(path) as img:
            if img.size != (192, 128):
                raise ValueError("Unexpected copy probe image dimensions")
            return np.array(img.convert("RGB"))

    def await_image(expected):
        deadline = time.monotonic() + 8
        while True:
            got = pixels()
            errors = int(np.any(got != expected, axis=2).sum())
            if not errors or time.monotonic() > deadline:
                return errors
            time.sleep(.05)

    # Xsgi may apply a different display gamma. The moved pixel values must
    # nevertheless match the *displayed* source exactly. Verify its pattern
    # via XGetImage as well, so an unpainted test window cannot pass.
    result["passed"] = False
    if exchange("seed") != "SEEDED":
        raise RuntimeError("Copy client did not seed its window")
    time.sleep(1)
    if exchange("check") != "XIMAGE 0":
        raise RuntimeError("Incorrect seed readback")
    original = pixels()
    if np.unique(original.reshape(-1, 3), axis=0).shape[0] < 4096:
        raise ValueError("Seed absent or insufficiently varied on scanout")
    if ram:
        y, x = np.indices(original.shape[:2])
        rgb = np.stack(((17*x + 3*y) % 256, (5*x + 19*y) % 256,
                        (23*x + 7*y) % 256), axis=-1).astype(np.uint8)
        result["seed_rgb_errors"] = int(np.any(original != rgb, axis=2).sum())
        if result["seed_rgb_errors"]:
            raise ValueError(f"Incorrect RGB values on scanout: {result['seed_rgb_errors']} pixels")
    before = counters(monitor)
    time.sleep(1)
    result.update(idle_1s=difference(counters(monitor), before), cases=[])
    for n in range(count):
        if exchange("seed") != "SEEDED" or await_image(original):
            raise RuntimeError(f"Could not reset window before case {n}")
        before = counters(monitor)
        reply = exchange(f"copy {n}").split()
        if len(reply) != 7 or reply[0] != "COPY":
            raise ValueError(f"Invalid copy response {reply}")
        sx, sy, dx, dy, w, h = map(int, reply[1:])
        hsrc, wsrc = original.shape[:2]
        x1, x2 = max(dx, 0), min(dx + w, wsrc)
        y1, y2 = max(dy, 0), min(dy + h, hsrc)
        expected = original.copy()
        expected[y1:y2, x1:x2] = original[sy+y1-dy:sy+y2-dy, sx+x1-dx:sx+x2-dx]
        bad = await_image(expected)
        counts = difference(counters(monitor), before)  # before XGetImage
        row = dict(rect=[sx, sy, dx, dy, w, h], scanout_errors=bad, transfers=counts,
                   ximage=exchange("check"))
        if ram:
            row["framebuffer"] = exchange("ram")
        result["cases"].append(row)
        if bad or row["ximage"] != "XIMAGE 0" or (ram and row["framebuffer"] != "RAM 0"):
            raise RuntimeError(f"Copy case {n} failed: {row}")
    result["verified_pixels_per_case"] = wsrc * hsrc
    result["passed"] = True


def qualify(shell, monitor, out, result):
    shell("export DISPLAY=:0; export XAUTHORITY=$(ps -axww -o args= | awk "
          "'$1 == \"/usr/X11R7/bin/Xorg\" {for(i=1;i<NF;i++) if($i==\"-auth\") print $(i+1)}'); "
          "export PATH=/usr/X11R7/bin:$PATH; "
          "(n=0; until xdpyinfo >/dev/null 2>&1; do n=$((n+1)); test $n -lt 120 || exit 1; sleep 1; done)")
    shell('copydir=$(mktemp -d /var/tmp/xiri-window-copy.XXXXXX) && cd "$copydir" && '
          "cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include -L/usr/X11R7/lib "
          "-Wl,-rpath,/usr/X11R7/lib /cdrom/window-copy.c -lX11 -o probe && mkfifo input")
    shell("exec 7<>input; ./probe <input 7>&- >messages 2>&1 & probe_pid=$!")
    try:
        body = shell("(n=0; until grep -q '^READY ' messages; do kill -0 $probe_pid || "
                     "{ cat messages; exit 1; }; n=$((n+1)); test $n -lt 15 || exit 1; sleep 1; done) && "
                     "cat messages")
        count = int(re.search(r"^READY ([0-9]+)\r?$", body, re.M)[1])

        def exchange(cmd):
            # Keeping an open FIFO writer avoids EOF between transactions.
            # The output file is append-only. Use a fresh file offset per command.
            body = shell("offset=$(wc -c <messages); echo '" + cmd + "' >&7; "
                         "(n=0; until test $(wc -c <messages) -gt $offset; do "
                         "kill -0 $probe_pid || exit 1; n=$((n+1)); test $n -lt 15 || exit 1; sleep .1; done) && "
                         "tail -c +$((offset+1)) messages")
            return re.search(r"^(SEEDED|COPY [-0-9 ]+|XIMAGE [-0-9]+|RAM [-0-9]+)\r?$", body, re.M)[1]
        exercise(exchange, monitor, out, count, result, ram=True)
    finally:
        shell('echo quit >&7; exec 7>&-; wait "$probe_pid"; rc=$?; cd /; '
              'rm "$copydir"/input "$copydir"/messages "$copydir"/probe && rmdir "$copydir" && test "$rc" = 0')
