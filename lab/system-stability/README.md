# Native system stability

This cycle precedes further per-application repairs. Its starting evidence is
the two native child-control stalls in the catalog bootstrap exclusions, the
catalog batch's failed halt, and the transient ten-second native XTest timeout
during the Acrobat image checks. None yet establishes a shared cause.

The fixture setup also exposed lost CD9660 ownership/mask fields in native
NetBSD32 mount translation. `cd9660.c` exercises the real mount system call,
modern and legacy sizes, zero-length legacy calls, ownership/masks, unprivileged
reads, legacy updates, guarded buffers, truncated arguments and copy faults.
`cd9660_mount.h` is the original NetBSD header retained with its license because
the guest's installed development headers do not include it. Baseline images
record the known CD regression failures separately from stability coverage;
a candidate core must pass every CD check.

Run the maintained probe with an explicit qualified bundle:

```sh
python3 scripts/probe-system-stability.py \
  --bundle .work/images/xiri-netbsd-desktop-20261104-acrobat
```

The default is three sequential cold boots, two xiritest sessions per boot,
100 input iterations per transport/desktop and 20 pairs of native detached-child
tests per greeter/IRIX session. It uses ordinary graphical IRIS, a host virtual
display, the bundle's exact emulator and immutable qualification NVRAM, and a
disposable disk overlay. It does not alter the manual image or runtime.

`--kernel-build .work/netbsd-stability-build` verifies and installs that build's
core, boot wrapper and matching module into the clone, halts and reboots it,
then runs the tests. `--seed RUN` can instead clone a cleanly halted candidate
run with exactly matching kernel/module artifacts. The source result and disk
overlay are hashed; the original seed remains unchanged. A cleanly halted
diagnostic failure is a valid starting state, not a qualification pass. The
candidate must still complete all checks after the new cold boot.

`xinput.c` opens a private native event-receiver window. Each iteration opens a
new X connection, moves the pointer, sends press/release with the original
helper's timing, checks both received events, and closes the sender. Every
blocking phase has BEGIN/END monotonic timestamps. An independent alarm emits
`XINPUT_TIMEOUT` and exits 124; Xlib is never called from the signal handler.
Local Unix and loopback TCP transports run at the greeter, under 4Dwm as
xiritest and under standard ctwm as netbsdtest. A deliberately held X server
first verifies timeout detection and recovery; that expected failure is
reported separately.

`guard-loop.sh` repeats the survey's native orphan controls with strict status,
completion-marker and descendant-cleanup checks. The original adversarial
session tests additionally cover double-fork/setsid, child bursts, failed exec,
leader failure, signals and logout while preserving an independent process
of the same user. The catalog's observer variant and installed session guard
remain distinct. No UID-wide termination is used.
The live-burst fixture waits for all 25 intended processes before teardown;
a fixed startup timer can stop it early when paging slows native forks. Its
exact ownership-count check remains mandatory. The completion burst retains
its 49-process check with a bounded minute to finish under load.

Every boot must return both users to the full-size xdm greeter and finish with
the kernel's clean-unmount and halt markers. `--halt-active` logs into 4Dwm
again before shutdown to exercise the service shutdown hooks with active
desktop clients as well. A successful run records bounded
coverage; it does not by itself explain earlier intermittent failures.
`--pressure-mib 96` holds a bounded native allocation with dirty pages across
the session tests. Before/during VM counters record the actual memory load;
there is no assumption that requesting memory necessarily forces paging.
This covers process creation under pressure and, with `--halt-active`, shutdown
with an independent native job still alive. The fixture responds to TERM and
has a separate 30-minute lifetime limit. Without active shutdown the probe
explicitly releases and waits for it before halting.
Results, source hashes, guest logs, screenshots and CPU/kernel diagnostics
are retained in `.work/system-stability/boot-*`. `--debug-failure` exposes the
same bounded request-file diagnostic interface as the catalog probe before
cleanup. All owned emulators are stopped even on failure.

The native input fixture labels the delay between pointer motion and button
requests explicitly. Its watchdog logs the monotonic clock and, on NetBSD
MIPS, the interrupted PC/RA/SP/A0 from the signal context, without calling
Xlib or stdio in the handler. It records runtime libc symbol addresses before
arming the alarm. During the explicit delay only, a bounded read inside the
pinned o32 libc's live 48-byte stack frame records the raw sleep-request
bytes. Interpret those bytes only with the matching PC, symbol offsets and
libc layout; the o32 padding word is not a request field. The harness also
hashes installed native libc. The alarm clock is sampled after the warning
write, so it is not the exact signal-entry time.
Keep the ten-second bound and original event checks
when investigating a timeout; the last logged X request alone does not locate
the interrupted instruction. The
[cleanup-image follow-up](../../docs/results/2026-11-05-cleanup-image.md)
retains four failed 96 MiB pressure runs. The previous-image comparison
captures a correct 200 ms native sleep request at the same libc instruction
as the candidate timeout. Another candidate run reports valid cleanup for
all 25 live-burst descendants, then fails a shell postcheck. The
[native paging investigation](../../docs/results/2026-11-05-native-paging.md)
subsequently traces that assertion and identifies long encrypted pageout
batches. The revised postcheck uses one process-state query, with live,
zombie and already-reaped child controls. The revised kernel passes the full
pressure workload and forced encrypted swap readback. Its replacement image
remains unselected after a separate startup kernel crash; further crash
investigation is deferred at the user's request.
Black pressure captures are excluded from visual qualification; the
independent cold desktop gate passes readable greeter and desktop checks.

The [first cycle report](../../docs/results/2026-11-04-system-stability.md)
separates primary qualification, diagnostic failures and manual continuations.
Each run retains its exact harness and media. The maintained runner's installed
artifact fields contain only verified hashes; the input bundle pin and candidate
build ledger remain separate to avoid attributing the replacement core to the
input image's source revision.

For replacement-image acceptance, `--require-cd9660` also requires every CD
check to pass without installing a candidate kernel. `--acrobat-replay 6`
adds a cold-profile GNOME Terminal check (original interactive shell,
preference save/reopen and normal exits) followed by six catalog-launched
Acrobat PDF/capture/focus/exit sequences. The first half use
`click-original.c`, byte-identical to the earlier helper source that timed out;
the remainder use `click-trace.c` with the same X calls and event delays,
per-stage monotonic timestamps and an async-safe timeout report. The helper
runs immediately after the original GL → software capture sequence, before
any extra guest query. A timeout fails the run and enters the normal CPU,
kernel and guest-log diagnostics; it is not counted as a successful retry.
The application-control source is copied into each run beside its harness.
The replay places Reader at a fixed position before each capture: 4Dwm's
normal cascading otherwise moves the Open toolbar button under the original
`300 300` focus coordinate on the fifth launch. It checks that the file dialog
is no longer viewable and records the document window's geometry. This fixture
correction preserves the original capture → focus → Quit sequence; it does not
explain the earlier native helper timeout.
GNOME launch and PID recording are submitted as one shell line. With two
typed lines, the newly mapped terminal can take focus while the second line
is still being entered into winterm. The image report retains that failed
control and the exact source used by each accepted run.

For example, against a newly packaged image:

```sh
python3 scripts/probe-system-stability.py --bundle NEW_BUNDLE \
  --runs 1 --sessions 1 --input-iterations 10 --child-iterations 5 \
  --require-cd9660 --acrobat-replay 6 --halt-active --debug-failure
```

These smoke and focus checks complement the full `probe-xiri-xdm.py --winterm`
image checks. A successful replay does not establish the earlier timeout's
cause or qualify unrelated applications, larger documents or general fonts.
The [replacement-image report](../../docs/results/2026-11-04-system-stability-image.md)
records a failed `button-sync` deadline, a second occurrence in a reduced
capture/click loop, and the separate stopped-client diagnostics. Disk/session
checks passed, but the application failure held that image's promotion. Preserve the
failed result and archive; a later successful click is diagnostic only.
The [subsequent scheduler image](../../docs/results/2026-11-04-xorg-scheduling.md)
passes fresh application, query-loop, both-user session and clean-halt gates
and is selected independently of those failed runs.

## Native sleep and scheduler diagnostics

`--trace-native` adds native syscall/context-switch traces to the input
fixture and shell tracing to the cleanup suite. It preserves the input
iterations, watchdog and cleanup assertions. Large archives travel through
the existing local NAT gateway, with matching guest/host SHA256 checks;
the listener binds only to host loopback and serves no files. The untraced
runner uses the same verified transfer for its final archive, after the
workload finishes; individual command responses still use the serial console.

The independent fixture removes Xlib from the sleeping process:

```sh
python3 scripts/probe-native-sleep.py \
  --bundle .work/images/xiri-netbsd-desktop-20261105-cleanup \
  --kernel-build .work/netbsd-paging-latency-v3-build \
  --check-swap-control --verify-memory \
  --iterations 100 --pressure-mib 96
```

A native child repeatedly requests 200 ms through `usleep`, `nanosleep` or
`select`, with a separate ten-second alarm. Its parent records both clocks,
LWP state, VM counters and CPU ticks every 100 ms. The matrix runs at the
unloaded greeter, the greeter with a held allocation, and the loaded IRIX
desktop. All processes are native NetBSD. Requesting 96 MiB does not itself
prove paging; the recorded VM counters establish whether it occurred.
`--kernel-build` installs hash-verified artifacts into a disposable disk,
halts, and reboots before observation. The input bundle pin and installed
kernel hashes remain separate. `--seed HALTED_RUN` reuses a verified matching
kernel overlay in a new clone, preserving the original overlay and its result.
After the matrix, `--verify-memory` releases the held allocation and runs a
separate anonymous swap-in control. `--swap-readback-only` runs that control
alone. It adds a temporary 128 MiB swap file on the disposable disk, keeps
encryption enabled, and grows pressure in 8 MiB steps (160 MiB maximum)
until `mincore` proves at least 128 pages of its 96 MiB primary mapping are
nonresident. NetBSD's data-preserving `MADV_DONTNEED` makes the primary mapping
reclaimable. After eviction it releases the extra pressure mappings, verifies
that at least 128 primary pages remain nonresident, reads every primary byte
it wrote (one per 4096 bytes), and requires its own major-fault count to
increase. The extra mappings are pressure only, not part of the checked data.
It then removes the temporary swap device and file. These steps
are separate from the timing matrix's unchanged 96 MiB workload; resident-only
readback is explicitly insufficient. No untouched bytes are claimed checked.
The readback keeps phase timestamps, an explicit alarm marker and native
syscall/signal traces. An inner shell records the control's exit status as
well as the outer launcher's status: the inspected native PAM `su` source
uses `WEXITSTATUS` without first checking for a signalled child, so a launcher
zero by itself is insufficient. The final data-verification marker is mandatory.
`--methods nanosleep usleep select` changes the order to distinguish an API
failure from the first test encountering a paging episode.

`--check-swap-control` verifies false/true/false/true readback with no swap
device configured, then restores configured swap and requires encryption on
for the matrix. `--swap-control-only` runs only that regression on an older
kernel. The baseline big-endian handler incorrectly reports zero while the
actual encryption flag is one. Consequently an ordinary matrix on that old
kernel now fails the initial setting check; the retained historical harness
records its earlier timing observations. `--plaintext-swap` is diagnostic
only and must first pass the control, so that broken readback cannot silently
turn an encrypted run into a claimed plaintext comparison.

Only `waitpid` decides whether the child finished. A disappearing LWP can
legitimately return ESRCH/EAGAIN between the parent's nonblocking wait and
its sysctl query. Such a query is a missing sample, not a successful exit or
an observer failure. Acceptance requires a successful `SLEEP_RESULT` completion
record as well as launcher status zero. The explicit `exit-control` retains a real child zombie
with WNOWAIT, checks this case, and then reaps its expected status 37.

`--sample-kernel` additionally pauses the diagnostic emulator briefly once
per host second for CPU registers and stack words. Those samples can locate
kernel work but are not an unmodified timing qualification. Their pause
durations and raw addresses are retained. Resolve addresses against the
exact pinned `netbsd.gdb`; apparent stack code addresses alone are not an
unwound call stack. Non-root KERN_LWP pointer fields are obscured by NetBSD
and must not be treated as kernel addresses.

`read-ktrace.py TRACE --output REPORT` reads the pinned LP64, big-endian
version-2 kernel trace format. Its 56-byte header and 64-bit nanosecond
field were checked against the matching kernel DWARF; the guest's o32
`kdump` misdecodes that timestamp layout. `--self-test` checks a known
200 ms interval and rejects malformed controls. The observer and worker
both make nanosleep calls, so the report separates counts by PID. Raw
traces remain authoritative; context-switch records are emitted when an
LWP resumes and are not globally time-ordered across different LWPs.

## Pointer-query scheduling control

`--fairness-iterations 10` adds a native Xlib receiver that behaves like a drag
handler: after button press, it queries the pointer until release. A separate
`click-trace` process sends the unchanged 100 ms delayed release with its
ten-second alarm. Forty preliminary press/release events exercise Xorg's
normal input-priority boost. The receiver has its own twenty-second bound,
records its UID, query count and elapsed time, and resets synthetic button
state after recording the result. Each case must observe release and a zero
sender exit status. The probe runs these controls over Unix and loopback TCP
at the greeter and in both user desktops. These are additional checks; the
ordinary input, deliberately held-server, child-supervision and clean-halt
checks remain required.

The [scheduler investigation](../../docs/results/2026-11-04-xorg-scheduling.md)
captures the earlier timeout while the release is already ready in Xorg.
`click-state.c` is the exact expanded diagnostic used for that observation,
separate from the ordinary acceptance helpers. It preserves their X calls
and alarm, opens procfs before testing, and on timeout records its signal
context plus Xorg state without calling Xlib from the handler. Its config
starts with the verified Xorg PID, followed by `symbol address-in-hex words`
lines (maximum 32 entries, 256 words each). Addresses and private structure
layouts are specific to the recorded Xorg binary/load base; the report
retains that config and both raw snapshots. It is not installed in an image.
The attempted Xorg register read failed, so the evidence does not contain a
server backtrace. The successful client-state reads and native scheduler
controls are the usable evidence.
