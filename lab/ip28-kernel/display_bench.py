"""Time Xlib requests through visible IMPACT scanout and check the full region."""
import re
import statistics
import time

from PIL import Image

COLORS = ("ca4632", "249ace")
WIDTH, HEIGHT = 640, 480


def qualify(shell, monitor, rpc, capture, result):
    shell("cd /var/tmp/ip28-xorg && cc -O2 -Wall -Wextra -Werror "
          "-I/usr/X11R7/include -L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib "
          "/cdrom/display-bench.c -lX11 -o display-bench && mkfifo bench.fifo")
    shell("exec 7<>bench.fifo; DISPLAY=:0 ./display-bench <bench.fifo 7>&- >bench.log & "
          "bench_pid=$!; (i=0; until grep -qx READY bench.log; do "
          'kill -0 "$bench_pid" || exit 1; i=$((i+1)); test $i -lt 60 || exit 1; sleep 1; done)')

    def draw(work, phase):
        # The bottom right square has even parity. Alternate colours so the
        # previous frame cannot satisfy this sample. Include serial delivery.
        start = time.monotonic()
        rpc("serial-send", data=f"echo {work}{phase} >&7\r")
        command = f"screen pix {WIDTH - 3} {HEIGHT - 3}"
        while time.monotonic() - start < 30:
            pixel = monitor([command])[command]
            if re.search(r"= " + COLORS[phase] + r"\b", pixel, re.I):
                return (time.monotonic() - start) * 1000
            time.sleep(0.02)
        raise RuntimeError("Timed out waiting for " + command + ": " + pixel)

    try:
        for work, name in (("f", "solid_fill"), ("p", "pixmap_copy")):
            draw(work, 0)
            samples = [round(draw(work, phase), 2) for phase in (1, 0, 1, 0, 1)]
            path = capture("bench-" + name)
            with Image.open(path) as image:
                actual = image.convert("RGB").crop((0, 0, WIDTH, HEIGHT)).tobytes()
            palette = tuple(bytes.fromhex(c) for c in COLORS)
            expected = palette[1] * (WIDTH * HEIGHT)
            if work == "p":
                rows = [b"".join(palette[(1 + x // 8 + row) % 2] for x in range(WIDTH))
                        for row in range(2)]
                expected = b"".join(rows[(y // 8) % 2] for y in range(HEIGHT))
            if actual != expected:
                raise RuntimeError(name + " scanout does not match the expected 640x480 image")
            result[name] = dict(samples_ms=samples, median_ms=statistics.median(samples),
                                verified_pixels=WIDTH * HEIGHT)
    finally:
        shell('echo q >&7; exec 7>&-; wait "$bench_pid"')
    result["passed"] = True
