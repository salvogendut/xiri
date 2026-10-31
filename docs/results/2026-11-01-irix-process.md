# IRIX fork, signal masks and child-exit waits

The process adapter advances original winterm/xwsh through fork and PTY slave
opening to child command startup. Xwsh now draws its own terminal window,
scrollbar and green cursor. A usable native shell and terminal input remain
the next objective, before the original 4Dwm evaluation.

![Original xwsh window before shell startup](images/2026-11-01-irix-winterm-window.png)

This is the actual three-second capture on the native Xvfb server. The
983×840 default window is clipped by the 640×480 test viewport. The blank
terminal is expected: child execve is still unsupported, so there is no prompt.
The observer ends the parent at five seconds and verifies descendant cleanup.

The implementation lives on the NetBSD fork's `xiri/irix-process` branch.
The [lab](../../lab/irix-process/README.md), [LP64 pin](../../lab/irix-process/baseline.json)
and [o32 pin](../../lab/irix-process/o32-baseline.json) record reproducible inputs.
Code revision `96e4607fed9` includes the reference error-order and signed
exit-status fixes; the clean build pin includes documentation at `fd219672645`.
The emulator remains at `9df1df14334838a989253efefe26f0547e6da592`.

## Measured behavior

Native fork already supplies IRIX's raw register convention: the parent gets
the child PID and second register zero; the child gets zero and second register
one. The adapter also supplies IRIX's getpid/getppid pair. Tests check identity
inheritance, actual native masks, private parent/child memory, the shared open
file offset and exit status. The child reads `A`; after waiting, the parent
reads `B` while retaining its original private memory value.

Signal-mask operations read and write the full 16-byte foreign structure.
The input copy precedes operation validation, while old-mask copyout follows
the mask update. NULL input queries ignore the operation code. Unaligned and
aliased buffers, immutable text, high/wrapped pointers and a partially mapped
range are included. The adapter maps traditional IRIX signals 1–31 and leaves
native-only inherited bits alone. Unsupported checkpoint/realtime mask bits
are ignored and reported zero, an explicit difference from original IRIX.
This does not qualify signal delivery, handlers or signal context restoration.

The wait subset accepts positive P_PID, WEXITED, WNOHANG and WNOWAIT. A FIFO
holds the child alive during the nohang case. Normal reaping returns the native
encoded exit status, sign-extended from 16 bits, in the second register; nohang without an event and nowait
preserve that register. A second wait distinguishes retained from consumed
children. NULL info is EINVAL; unmapped ranges fault before consumption;
read-only mapped output faults after consumption. Unsupported selectors or
options fail before consuming a child, and non-NULL rusage is ENOSYS.

The adapter owns and zeroes its 128-byte exit-info buffer. Original IRIX's
unused siginfo bytes contain undefined data, so the exported reference removes
that padding and retains raw hashes. PID relationships are checked before
canonicalization. Native padding must actually be zero. Accounting fields are
zero for this subset; signal-caused deaths, CPU accounting, other selectors,
stopped/continued children and interruption semantics remain unqualified.

## Validation

The original reference contains 944 executions of 118 variants across o32/n32,
direct/indirect dispatch and root/uid 1234 with empty supplementary groups.
The candidate matrix repeats both LP64 execution modes and o32 CI. Native
supervisors independently inspect KERN_PROC2 while the foreign processes wait
on a pipe, then verify exit and complete process-group cleanup. Native mask/fork
controls and native o32/original asa/echo controls run before and after.

The [matrix report](2026-11-01-irix-process.json),
[original-app report](2026-11-01-irix-winterm-process.json) and
[sanitized oracle](../../lab/irix-process/reference-records.json) retain the
accepted evidence. Capture-only data remains unqualified until the qualifiers
check every case, source hash, kernel pin and shutdown result.

| Qualified run | Cases | Records | Native/vendor controls | Native process controls |
| --- | ---: | ---: | ---: | ---: |
| LP64 CI, o32+n32 | 944 | 1,248 | 12 | 8 |
| LP64 ordinary, o32+n32 | 944 | 1,248 | 12 | 8 |
| o32 CI | 472 | 624 | 8 | 8 |
| Total | 2,360 | 3,120 | 32 | 24 |

All three guests halted cleanly. After checking PID relationships and removing
only undefined oracle padding, 1,580 cases match the canonical reference.
The other 780 follow explicit policy: 740 restrict signal masks to traditional
signals, and 40 reject P_ALL/non-NULL rusage before consumption. In 120 accepted
wait-output cases, native padding is independently required to be zero.

The full process comparison is reproducible with:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/qualify-irix-process.py \
  .work/irix-process/runs/lp64-ci-t3sfz_kh \
  .work/irix-process/runs/lp64-ordinary-s2u9_yj_ \
  .work/irix-process/runs/o32-ci-rpl8u4t_ \
  --reference .work/irix-reference/process-records-runs/ci-mznyh53j \
  --output docs/results/2026-11-01-irix-process.json \
  --export-reference lab/irix-process/reference-records.json
```

Eight original xwsh starts also pass the observed startup contract: root and
uid 1234, default/imported and fixed fonts, CI and ordinary modes. Every child
opens its slave, reaches unsupported execve and exits; every parent is ended
by the five-second supervisor, which verifies the complete group is absent.
Native PTY, font/window, ptrace and deliberately orphaned-descendant controls
pass before and after. Both guests halt cleanly. These are startup/rendering
checks, not shell/input qualification.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/qualify-irix-winterm-process.py \
  .work/irix-winterm-process/runs/ci-vzqks6v0 \
  .work/irix-winterm-process/runs/ordinary-ocbz0htw \
  --output docs/results/2026-11-01-irix-winterm-process.json
```

The qualifier uses ImageMagick to verify that the committed PNG has exactly
the captured XWD pixels.

Initial diagnostic runs are excluded: the first original smoke harness lost
some `/bin/sh` wait statuses when it launched its watchdog after the fixture;
the corrected full reference launches the watchdog first and records all zero
statuses. The first winterm trace transfer exceeded its serial timeout because
the parent loops after child startup fails. The final observer retains the
first 2,000 parent trace events, all other processes and every signal, with
hashes/counts for the full trace. It does not claim a complete parent trace.
An intermediate attempt to use formatted kdump hit the installed o32 tool’s
LP64 msghdr decoder fault; accepted captures use the established raw decoder.
The installed o32 decoder also cannot decode the LP64 PSIG payload. The host
parser recovers its missing newline without interpreting the payload; signal
delivery is not qualified. Full binary traces remain on the disposable disks.
The first full candidate matrix exposed the signed exit-255 status-register
difference; those captures are excluded and the entire matrix was repeated
after correction. A later trace-metadata transfer needed shell grouping around
two commands; its incomplete winterm capture is also excluded.

## Remaining terminal work

The child now reaches unsupported execve (1059) after opening the slave. Its
startup also requests session/process-group operations, descriptor duplication,
credential calls, signal dispositions and terminal control. Those interfaces
need measured native adaptations before shell execution can work correctly.

| Observed child request | Follow-up |
| --- | --- |
| syssgi FDHI (109), ulimit (1063) | Descriptor-limit queries used during setup |
| syssgi SETSID (20), dup (1041) | Native session and standard-descriptor wiring |
| ioctl 0x80087467 | Terminal window-size request; preserve native PTY authority |
| setuid (1023), setgid (1046), nice (1034) | Native identity/priority policy and error behavior |
| sigaction (1162) | Signal dispositions, delivery and context handling |
| execve (1059) | Checked foreign argv/envp marshalling into a native shell |

The parent requires bounded cleanup after the failed command; native controls
deliberately leave a descendant alive to verify that the runner removes it.
Before adding setsid, extend supervision to track children that leave the
inherited process group.

No additional original resource bundle was needed for this process checkpoint.
Keep the original fonts, locale files, app-defaults and synthetic account
fixtures from the stopped seed. Shell selection, descriptors, credentials,
controlling terminal and user state belong to native NetBSD session setup.
The [resource checklist](../IRIX-RESOURCES.md) tracks remaining image assets.
