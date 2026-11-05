# IRIX sleep, child state and shell jobs

This cycle measures the supplied IRIX 6.5.22m installation, implements its
sleep and child-state interfaces in `compat_irix_o32`, and exercises real
terminal jobs. The [cycle report](../../docs/results/2026-11-05-irix-job-control.md)
separates ABI comparisons, terminal behavior, retained diagnostic failures
and the later investigation of native stalls.

## Measured interfaces

Both foreign ABIs use an eight-byte `timespec` with signed 32-bit seconds and
nanoseconds. `nanosleep` is syscall 1077, including indirect dispatch. It
accepts unaligned input, validates nanoseconds before treating negative
seconds as elapsed, and caps large durations at `INT32_MAX` 100 Hz ticks.
Successful sleeps leave the remaining-time pointer untouched. Interrupted
sleeps copy remaining time in 10 ms units; output faults take precedence over
interruption, and a page-crossing output can write its valid prefix. Aliased
request/output storage must not change the copied request.

Original `SA_RESTART` restarts the entire request. The adapter preserves
`kpause`'s EINTR/ERESTART distinction; the native `nanosleep` helper erases
that distinction. Our raw assembly bridge reloads the syscall number directly
before `syscall`, allowing the original restart path to execute that load
again. Reusing a bridge whose preceding instruction writes a register can
produce a fixture SIGSYS instead of testing the adapter.

Native NetBSD's 100 Hz sleep timer is coarser than the original machine for
sub-10 ms requests. This implementation does not promise identical short-sleep
latency or busy-wait to simulate it. The wire/error/restart checks and the
separate libc timing observations make that limit explicit.

`waitsys` now accepts P_PID, P_PGID and P_ALL, WEXITED/WTRAPPED/WSTOPPED/
WCONTINUED, and optional WNOHANG/WNOWAIT. Native wait owns child selection and
consumption. Stop/resume events preserve the secondary return register; a
consumed death/exit updates it. Invalid selectors/options, bad destinations,
read-only consumption behavior and unsupported non-null rusage remain tested.
The original's P_PGID/id=0 case observes stops and continues but fails to select
an exited child; the candidate deliberately retains native successful exit
reaping for this selector. It is an explicit policy difference, not exact
reference parity.
An empty event selection is also still rejected with EINVAL; original IRIX
returns no event for WNOHANG|WNOWAIT without any selected state. The dedicated
option matrix reports all 24 such differences rather than counting them as
matching behavior.

IRIX `SA_NOCLDSTOP` suppresses both stopped and continued SIGCHLD notices.
A generic opt-in `EMUL_NOCLDSTOP_CONT` bit in `emul.e_flags` lets the core apply
that policy before queuing a continued-child notice. Suppressing it only at
signal delivery would still interrupt blocked calls and could replace a
pending exit event. Native NetBSD does not opt in and keeps its prior behavior.
The matching core and module must be installed together. Other translation
code remains in the module; this adds a third core interface to the
[stock-kernel deployment work](../../docs/ARCHITECTURE.md).

`syssgi(SGI_GETPGID)` (64) and `SGI_SETPGID` (21) delegate process-group
lookup and assignment to NetBSD. Its ownership, session and after-exec checks
remain authoritative. Original measurements distinguish a missing process
(ESRCH), an executed child (EACCES), another session or missing destination
group (EPERM), and an invalid group (EINVAL). `getpgid` excludes IDs at or
above `0x7ffffff0`; `setpgid` accepts that group boundary and rejects values
above it before target lookup. Negative process IDs return EINVAL for the
getter and ESRCH for the setter. The public libc's `sysconf(_SC_JOB_CONTROL)`
returns 1 without requiring raw `SGI_SYSCONF/6` support; the latter returns
EINVAL on the reference and stays unchanged.

## Fixtures and independent checks

`headers.c` prints constants and layouts from installed public IRIX headers.
`nanosleep.c` emits 512-byte records for 33 duration, pointer, interruption and
restart cases. `children.c` emits 2,560-byte records for four signal-handler
modes and eight selectors. Pipes and WNOWAIT observations establish readiness;
a short assumed sleep does not establish that a child stopped or resumed.
Each matrix covers o32/n32, direct/indirect dispatch and root/UID 1234.

`groups.c` adds 24 records with 37 group operations each, covering children
before exec, after exec and in a new session. It checks create/join/rejoin,
queries, ID boundaries and permission/error precedence. Readiness and release
use pipes; the child holds no writer for its release pipe, so parent death
also releases a child that has moved outside the parent's process group.
Every passing record requires the child to be reaped with status 37.

`wait-options.c` observes SIGSTOP, SIGTSTP and SIGTTIN with all 16 combinations
of the four event flags, always using WNOHANG|WNOWAIT. Its 24 records verify
360 matching nonempty selections and explicitly retain the 24 empty-selection
differences. In particular, WTRAPPED alone does not report ordinary stops.

The independent qualifier compares 264 sleep records and 256 child-state
contracts. Reference siginfo padding/accounting and no-event status are
undefined and excluded; unused candidate bytes must be zero. PID and time
variation is validated before normalization. Thirty-two P_PGID/0 exit
selection differences are reported explicitly. Native before/after controls
check both SIGCHLD policies under both identities. The baseline records
24 ENOSYS sleep calls and 16 EINVAL stop waits.

The original-libc `libc-sleep.c` and `sleep-rounding.c` controls separately
exercise `usleep`, ordinary/interrupted/restarted `nanosleep`, remaining time,
short-sleep timing and reaping. They are compiled on IRIX and the same binaries
run on the candidate. Existing signal, sproc and process qualifiers replay
48, 48 and 144 older cases respectively. The sproc suite must run from its own
fixture directory because its exec helper is a relative pathname.

Build and stage fresh inputs:

```sh
python3 scripts/build-irix-nanosleep.py
python3 scripts/build-irix-children.py
python3 scripts/build-irix-groups.py
python3 scripts/build-irix-wait-options.py
python3 scripts/stage-irix-job-control.py --output .work/job-control/fresh-media
```

Transfer the resulting tarball into a new writable directory in each disposable
guest. On original IRIX, run `sh run-reference-nanosleep.sh` and
`sh run-reference-children.sh` from that directory; retrieve
`sleep-reference.tar` and `child-reference.tar`. The installed freeware GCC
builds the native guard. The scripts refuse reuse of an existing result
directory. The guard reserves a new output file before starting the child,
rejects malformed arguments, bounds every raw fixture, reaps it, terminates
its remaining process group and checks that the group is absent. Its timeout
control must fail and leave no group. Sleep/child-state fixtures remain in
the guard's process group. Group fixtures also use the pipe ownership rule
described above.

On native NetBSD, run `sh run-native.sh baseline` on the old kernel and
`sh run-native.sh` on the candidate, each from a fresh staged directory as
root. The native runner drops to the requested identity, owns the probe's
process group and has a separate five-second limit. Preserve each
`native-results.tgz`. A readable `input.txt` is mandatory for this shared
runner. Compare the collected archives:

```sh
python3 scripts/qualify-irix-job-control.py \
  --sleep-reference /path/to/sleep-reference.tar \
  --child-reference /path/to/child-reference.tar \
  --baseline /path/to/baseline-results.tgz \
  --candidate /path/to/candidate-results.tgz \
  --output /path/to/comparison.json
```

The qualifier verifies the original ELF bytes, matching manifests, current
fixture source hashes and guest candidate digests. It rejects duplicate tar
members and incomplete/duplicate observations. Negative controls corrupt a
notification count, unused siginfo word, sleep return value or process-group
cleanup result and require rejection.

The additional `run-reference-groups.sh` and `run-native-groups.sh` produce
`group-reference.tar` and `groups-native.tgz` for
`qualify-irix-groups.py --reference REF --candidate NEW --output RESULT`.
That comparison validates all 888 operations, every secondary return
register, the release/reap result and unused record bytes. Its negative
controls corrupt register preservation, group identity, error precedence
and padding.

The analogous `run-reference-wait-options.sh` and
`run-native-wait-options.sh` produce `wait-options-reference.tar` and
`wait-options-native.tgz`. Compare them with
`qualify-irix-wait-options.py --reference REF --candidate NEW --output RESULT`.
Its successful status is `passed-with-differences`, preserving the empty-event
selection limitation explicitly.

## Real desktop jobs

The maintained `probe-xiri-xdm.py --jobs` option uses
[`job_control.py`](../../scripts/xiri_lab/job_control.py), real XTest keyboard
input, and the bounded native `job-worker.c`. It checks winterm's native shell
and the original IRIX shell in GNOME Terminal. Both must start with interactive
and monitor mode enabled; `set -m` then makes the test's intention explicit.

The sequence verifies the foreground process group, Ctrl-Z, `jobs`, `bg`,
`fg`, Ctrl-C and its exit status, a background read stopped by SIGTTIN, explicit
child waiting, and absence of exited PIDs. The IRIX terminal must close on
`exit`. A real desktop menu logout must then remove a running worker, a
stopped worker and their shell, with the session guard reporting zero surviving
descendants. The normal image probe also checks the separate netbsdtest/ctwm
login and full-size xdm greeter. PNGs and guest logs are retained in the run.

The original shell requests SA_NOCLDSTOP and polls children between input
lines. On both original IRIX and Xiri, the first `jobs` after a background read
can report Running; the next reports Stopped (SIGTTIN). The test records both
and enters `fg` at a separate prompt. Sending a marker command after every
reference command conceals this behavior, so the reference comparison uses
raw serial input without extra guest commands between observations.

```sh
python3 scripts/probe-xiri-xdm.py --bundle /path/to/candidate-bundle \
  --winterm --fonts --jobs
```

These terminal tests cover a bounded set of single-shell jobs. They do not
establish general multi-LWP behavior, nested shell pipelines, general layered
TTY revoke, or a cause for earlier intermittent native stalls. The preserved
older images and failed runs remain available for those investigations.
