# Type1 sizing and native MIPS signal return

These native NetBSD fixtures separate floating-point context restoration,
libXfont sizing, direct FreeType rendering and X server pixmap output. They
require the guest's development tools and X11 headers. They do not import
IRIX source or modify the installed fonts/libraries.
The [finding and qualification](../../docs/results/2026-11-05-type1-scaler.md)
identify the native MIPS FPU validity bug. `baseline.json` pins the tested
kernel; `build.json` preserves its actual pre-commit provenance and
`source-equivalence.json` checks it against the committed fork source.

Copy this directory into a disposable NetBSD guest and run `make` there.
The register fixture targets the native o32 userland used by our mips64eb
kernel; it is not a portable host test.

```sh
./signal-registers
./fp-signal 200000
./ft-metrics
```

`signal-registers` compares all 32 FPR words and FCSR, including all four
rounding modes and a sticky exception flag. Ordinary and `SA_SIGINFO` handlers
run both with and without deliberately clobbering FPU state. Eight no-signal
controls and sixteen signal cases must pass. A 30-second alarm bounds it.
`fp-signal` repeatedly converts 14.5 points into 26.6 units under a periodic
SIGALRM; require `FP_PASS`, exit zero and a nonzero delivered-signal count.
The host harness also needs a timeout for that test. `ft-metrics` independently
loads the installed IBM Courier file and renders `M` and `g` at 20 pixels.

Use an unused X display for the scalable-font control. Leave Xvfb's default
smart scheduler enabled here: its SIGALRM activity exposes the native bug.
The production Xorg `-dumbSched` setting addresses a separate input starvation
problem and remains part of the qualified desktop configuration.

```sh
LD_PRELOAD="$PWD/fttrace.so" Xvfb :1 -screen 0 800x600x24 \
    -ac -noreset -nolisten tcp >freetype.log 2>&1 &
server=$!
# Wait for DISPLAY=:1 xdpyinfo to succeed before running the following.
DISPLAY=:1 ./stress 560 churn >stress.log 2>&1
rc=$?
kill "$server"
wait "$server"
test "$rc" -eq 0
```

The 560-operation churn alternates seven sizes and four IBM Courier faces,
font listing, font opening and fontsets, releasing all retained fonts every
28 operations to exercise fresh sizing. Require `STRESS_PASS iterations=560`,
healthy metrics, and no zero-size `FTSIZE` requests. The test has a 600-second
alarm. A baseline failure can occur at different iterations; the register
test is the deterministic control. Tiny accent outlines at the smallest size
are not themselves failures in the trace.

`core-metrics` accepts `open`, `list` or `set`, an optional XLFD, and a repeat
count. Its default is the historical failing bold 20-pixel IBM Courier request.
It records the actual `XA_FONT` name, metrics, and a pixmap rendering of
`MMggCourier`. Healthy bold-20 output has ascent 17, descent 4, advance 12,
643 ink pixels and bounding box `10,31,140,47`. Raw pixel hashes depend on the
server's pixel values; compare the ink count and bounds across Xorg and Xvfb.
The requested average width 110 is resolved to an actual font width of 120.

`fttrace.so` is diagnostic interposition for the private Xvfb process only.
It records FreeType size requests and unusual glyph/outline results; it is
never installed into the desktop runtime. These fixtures do not qualify every
Type1 face, native n64 programs, ptrace or physical SGI hardware.

The recorded cold comparison and graphical continuation can be revalidated
without another guest boot:

```sh
python3 scripts/qualify-type1-scaler.py .work/type1/qualification-knnth2vm \
    --output /tmp/type1-result.json --png /tmp/type1-courier.png
```

The qualifier requires the retained run, the local IRIX signal fixtures and
a clean halt. It checks the known baseline failure, the corrected register
state, every traced size request, pixmap output, native/original Xlib metrics,
the original IRIX FPU records and winterm resize/exit evidence. A separate
CHD acceptance still checks the shipped desktop defaults and both xdm users.
