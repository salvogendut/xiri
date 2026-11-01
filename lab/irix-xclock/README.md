# Original IRIX xclock experiment

Follow-up: collision relocation now lets original analog/digital xclock draw in both execution modes and identities. Timekeeping remains unqualified. See the [new result](../../docs/results/2026-10-31-irix-elfmap-relocation.md).

The user requested a simpler X application alongside Toolchest. This lab uses
the unmodified n32 `/usr/bin/X11/xclock` from the supplied IRIX 6.5.22m disk,
with its original libraries and XClock application defaults. It runs on the
[xstat kernel](../irix-xstat/README.md) against native NetBSD Xvfb.

[manifest.json](manifest.json) records hashes, ELF headers, dependencies and
static address overlaps. Only metadata is public; binaries, resources, raw
vendor traces and framebuffer captures stay under `.work/irix-xclock`.
The new inputs are xclock, `libXaw.so.2` and `app-defaults/XClock`. Remaining
libraries are checked against the established desktop inventory.

The executable and libraries have suitable 8 KiB load boundaries. That does
not establish relocation support: libXaw, libXmu and libXt have overlapping
linked ranges. The observed loader result and limits are in the
[result record](../../docs/results/2026-10-31-irix-xclock.md).

Prepare the files using the existing read-only libguestfs procedure in the
[reference lab](../irix-reference/README.md), preserving the manifest hashes.
Use a stopped, complete LP64 xstat run containing the staged Toolchest resources:

```sh
python3 scripts/probe-irix-xclock.py \
  --seed-directory .work/irix-xstat/runs/lp64-ci-8wjwgrbd
python3 scripts/probe-irix-xclock.py --mode ordinary \
  --seed-directory .work/irix-xstat/runs/lp64-ci-8wjwgrbd
```

The harness checks inherited binaries/libraries and new inputs, compiles
original native helpers, and brackets the workload with native/asa/echo
controls. It validates the native ptrace exec/fault PC and captures the later
Toolchest allocator stop twice as root. This also completes that diagnostic
without relying on the rejected non-root tracing attempt.

A native NetBSD xclock must display a viewable window on the same server.
Vendor analog and digital launches then run under root and uid 1234, with an
explicit HOME and a five-second child limit. The harness records parent exit
status, foreign syscall traces, window trees, map state and two root-frame
captures separated by two seconds. A timeout alone is not application success;
a usable window and event handling need independent evidence. Loader messages
written through `/dev/console` are retained in the serial log even when the
child's stdout/stderr are empty. Later runs also retain each case's console
slice separately.

Every run uses a private disk and ports, halts the guest, and stops its emulator.
Count this guest within the user's current limit of four simultaneous IRIS instances.

After both modes finish, recheck their saved records with:

```sh
python3 scripts/qualify-irix-xclock.py <ci-run> <ordinary-run> \
  --output docs/results/2026-10-31-irix-xclock.json
```

The qualifier checks native clock visibility, all four attempts per mode, raw
trace decoding, absence of a foreign X connection/window, matching frame
hashes, the loader diagnostic, repeated root fault PCs and clean shutdowns.

The follow-up [actual ELF-map capture](../../docs/results/2026-10-31-irix-xclock-elfmap.md)
proves that libXmu requests addresses already occupied by libXaw text. Its
separate original native helper uses verified libc/rld syscall breakpoints
and native breakpoint/restoration controls, without a kernel change. Run
from the host, where `genisoimage` is available; the harness launches IRIS in
the toolbox. Use a stopped completed xclock run as the seed:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-xclock-elfmap.py \
  --seed-directory .work/irix-xclock/runs/ci-lerevng9
PYTHONDONTWRITEBYTECODE=1 python3 scripts/qualify-irix-xclock-elfmap.py \
  .work/irix-xclock-loader/runs/ci-nqn5qcww \
  --output docs/results/2026-10-31-irix-xclock-elfmap.json
```

The second command uses the completed run recorded in this repository;
substitute the new run directory to qualify a new capture. Raw memory remains
private under `.work/irix-xclock-loader`. The public report contains only
metadata and hashes. The native helper must pass its entry-PC breakpoint
control before observing vendor code. Both vendor children must exit naturally,
and the guest must halt cleanly. Count the diagnostic guest within the user's
current limit of four total simultaneous IRIS instances and stop it afterward.


The harness also accepts `--kernel-checkpoint siocnread` with a stopped, clean
LP64 SIOCNREAD run as its seed. This repeats analog/digital xclock under both
identities, retains native ABI/ptrace/X controls, and skips the historical
Toolchest allocator-fault expectation that fxstat already fixed. It does not
change the loader or assume that Toolchest's ioctl fix resolves libXmu mapping.

```sh
python3 scripts/probe-irix-xclock.py --kernel-checkpoint siocnread \
  --seed-directory .work/irix-siocnread/runs/lp64-ci-d2asxkow
```

The [same-kernel recheck](../../docs/results/2026-10-31-irix-siocnread.md)
confirms the libXmu ENOMEM boundary in all four CI attempts, before any X socket
or connect call. Native xclock displays and the before/after native/vendor
controls pass. This is a recheck of the existing blocker; no loader fix is
claimed by the SIOCNREAD checkpoint.


The later [time checkpoint](../../docs/results/2026-11-01-irix-time.md) follows
the qualified libXmu relocation fix. Original analog/digital xclock now shows
current UTC time, advances and redraws in both modes under both identities.
Use `scripts/probe-irix-xclock-time.py --seed-directory
.work/irix-xclock/runs/ci-0xaicapn` with `--mode ci` or `--mode ordinary`, then
pass both stopped run directories to `scripts/qualify-irix-xclock-time.py`.
The [time lab](../irix-time/README.md) describes the ABI oracle, kernel pins,
bounded lifetime, native controls and PNG evidence. Historical harnesses and
seeds remain unchanged for reproduction.
