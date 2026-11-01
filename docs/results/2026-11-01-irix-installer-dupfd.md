# Original inst after F_DUPFD support

The [F_DUPFD adapter](2026-11-01-irix-dupfd.md) clears the installer child's
stdout/stderr duplication failure. Original inst successfully duplicates pipe
writer fd4 to fd1 and fd6 to fd2, then executes native `/bin/sh`. The parent
resumes from its armed sproc wait. The [checked trace](2026-11-01-irix-installer-dupfd.json)
records both allocated descriptors and zero error flags.

The unchanged distribution dry run still reaches its 30-second watchdog,
without reading the distribution or producing installer stdout. Its parent
repeatedly calls gettimeofday (trap1128), receiving ENOSYS 89, interleaved with
select calls with nfds 0. There are 66 captured gettimeofday failures in this
run. The final select is interrupted by cleanup. This is not installation
success, and clock failure is not established as the only remaining problem.

The helper shell still searches IRIX-style directories for `ls` and `mkdir`,
without `/bin`; no successful utility exec appears in the retained trace.
Fix and measure the time calls, then repeat the installer and capture helper
output/arguments before choosing a native bootstrap arrangement or staging
original utilities. No helper or package resources were newly imported.

The `-H` command still prints an incomplete hardware profile and maps the
5025-byte machfile. The shared zero-device mmap and sproc/native shell path
remain working. Signal registration, hardware queries, time and creat remain
observed gaps. Four native controls and the native-write/IRIX-read shared-home
check pass. The ordinary user home is `/usr/people/xiritest`; foreign root
HOME remains `/`.

The run is `.work/irix-installer-dupfd/runs/ci-ipvlay90`, using clean-source
kernel revision `572dcb832cb3a42f7c728115db241cae88fc5d8c`. All test groups are
absent, including the timed-out attempt, and the guest halts cleanly. The
qualifier checks original inputs, pins, outputs, native controls, home
ownership, exact duplicate returns, PID/LWP-specific syscall ordering and
native shell loader evidence. As before, post-exec register contents are not
interpreted as ordinary syscall errno flags.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-installer-dupfd.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/qualify-irix-installer-dupfd.py \
  .work/irix-installer-dupfd/runs/ci-ipvlay90 \
  --output docs/results/2026-11-01-irix-installer-dupfd.json
```

The user also requested time support for xclock. Its earlier rendering trace
reports both unsupported time(1013) and gettimeofday(1128), so the next cycle
must qualify both and check actual clock updates, not merely window creation.
Package installation, original hooks and the Freeware catalog launch remain
open.
