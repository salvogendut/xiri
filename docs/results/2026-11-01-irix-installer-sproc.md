# Original inst after bounded sproc support

Original `inst` now creates its subcommand child, arms parent release and
executes native NetBSD `/bin/sh`. The [checked trace](2026-11-01-irix-installer-sproc.json)
shows the former `sproc` ENOSYS boundary is cleared on the
[bounded sproc kernel](2026-11-01-irix-sproc.md). **Distribution reading and
installation still fail**: the dry run reaches its 30-second watchdog.

## Child progress and the next failure

The unchanged distribution request is:

```text
inst -n -M -r /emul/irix -f /cdrom/dist -c /cdrom/commands
```

The trace records parent PID486 calling trap1129 at libc PC`0x0fa75038`,
entry`0x0fa750a8`, flags`0x03000040`. Child PID555 runs the libc entry path,
queries its PID and successfully calls `prctl(PR_UNBLKONEXEC, 486)`. It then
performs descriptor setup and calls execve. Native `/bin/sh` and its NetBSD
runtime are loaded under that PID; the parent's sproc returns PID555 with
A3 zero. The child arm, exec and successful parent return are paired by PID
and LWP so interleaved traces cannot incorrectly match one process's call to
another's return.

The first concrete new incompatibility is descriptor duplication:

| Child request | Result |
| --- | --- |
| fcntl(fd4, F_GETFL, 0) | writable descriptor flags, success |
| fcntl(fd4, F_DUPFD, 1) | EINVAL22 |
| fcntl(fd6, F_GETFL, 0) | writable descriptor flags, success |
| fcntl(fd6, F_DUPFD, 2) | EINVAL22 |

Libc has closed descriptors1/2 and attempts to replace them with the pipe
writers. Our fcntl adapter does not implement selector0, so the helper's
stdout/stderr are not reconnected. This is distinct from the already supported
dup/dup2 trap path. The historical licensed NetBSD IRIX/SVR4 headers establish
selector0 as F_DUPFD; paired original/native tests are needed before adding it.

The parent subsequently makes repeated gettimeofday trap1128 calls returning
IRIX ENOSYS89, interleaved with select. There are 58 captured gettimeofday
failures in this run. The final select is interrupted by watchdog cleanup.
These observations do not establish a single cause for the timeout: broken
pipe setup already occurs earlier, and timekeeping is also unsupported.

The native shell searches `/sbin`, `/usr/bin`, `/usr/bsd`, `/usr/sbin`, `/etc`,
`/usr/etc` and the current directory for `ls` and `mkdir`; it never searches
`/bin` for those commands. No successful utility exec is observed. NetBSD's
native utility layout differs from the helper's IRIX-style search. After
fixing descriptor setup, capture actual helper output and arguments, then
choose explicitly between staged original utilities and a native bootstrap
arrangement. Do not create a fake successful installer or an unverified
package history.

## Retained controls and evidence

The `-H` command still prints an incomplete hardware profile and maps the
staged 5025-byte machfile. The shared 1 MiB zero-device mmap succeeds in both
cases. SIGBUS/SIGSEGV handler registrations remain ENOSYS; their warnings
remain visible, without a corresponding application SIGBUS/SIGSEGV in this
capture. Hardware queries, time and creat also remain observed gaps.

Four native controls pass before/after as root and UID1234. Account setup
creates `/usr/people/xiritest`, verifies mode700 and idempotence, and a native
shell writes a file that original IRIX asa reads. Foreign root HOME remains
`/`. This repeats shared-home checks; graphical login persistence is not
newly qualified.

The accepted run is `.work/irix-installer-sproc/runs/ci-n9wz97l5`. Its supervisor
removes the whole test group, including the timed-out distribution attempt,
and the guest halts cleanly. An earlier run `ci-qi0clxb8` failed during native
setup because embedded newlines corrupted a serial completion marker. It also
halted cleanly. The repaired harness keeps that shell command on one serial
line; the failed capture is not a qualification result or seed.

The qualifier verifies original input hashes, the kernel pin, exact outputs,
controls, home ownership, trace hashes and ordered PID-specific syscall pairs.
It collapses byte-identical head/tail captures, including traces whose last
line lacks a newline. A successful exec's recorded A3 belongs to the new
register image and is not treated as an ordinary errno flag; native loader
and process-name evidence establish that handoff.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-installer-sproc.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/qualify-irix-installer-sproc.py \
  .work/irix-installer-sproc/runs/ci-n9wz97l5 \
  --output docs/results/2026-11-01-irix-installer-sproc.json
```

Next qualify F_DUPFD's allocation, limits, descriptor flags, shared offsets,
errors and rollback on original IRIX and both native kernels, then repeat
this unchanged installer command. Resolve the helper paths and measured
gettimeofday behavior from the subsequent trace. xmahjongg installation,
original catalog hooks, the Freeware launch action and removal remain open.
