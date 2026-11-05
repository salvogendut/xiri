# Session cleanup at the deadline

A deliberate scheduling delay reproduces a false cleanup failure in the
native session guard. The corrected guard drains queued exit notifications
and checks its leader's wait status once more before declaring that cleanup
has failed. All seven deadline scenarios pass, including rejection of a
child that really remains alive. The six-second grace period is unchanged.

This establishes a runtime defect and its correction. It does **not** establish
the cause of the earlier compview tracking failure, native bootstrap stalls
or catalog-batch halt failure. Those historical observations remain open.
The [previous tracking cycle](2026-11-05-process-tracking.md) and its paired
compview replays remain separate evidence.

## Measured failure

The [native tracking lab](../../lab/irix-process-tracking/README.md#cleanup-deadline-experiment)
runs the original installed supervisor and the candidate on separate disposable
copies of the same qualified native-wait image. Kernel, module, emulator,
fixture sources and compiled delay/controller binaries are identical.
Tests run as xiritest, UID 1234, beside the native xdm greeter.

A guest-only interposer calls the real `kill`, then delays the supervisor's
return for seven seconds. Before returning, it reads NetBSD's actual kqueue
count with `fstat`, which does not consume notifications. After the guard
prints its verdict, the interposer audits any notifications still queued at
close. The controller independently knows the worker PID from a private pipe
and queries its native process state after the guard exits.

In five scenarios, the original guard reports `valid=0 remaining=1` despite
the child having exited. Each has one real `NOTE_EXIT` already pending before
the delayed call returns, and the same event remains unread when the guard
closes its queue. Direct children are zombies awaiting reaping; the orphaned
grandchild is already absent. Thus PID disappearance alone is not the proof:
the retained notification, worker identity and actual state agree.

| Scenario | Original guard status | Corrected status | Corrected remaining |
| --- | ---: | ---: | ---: |
| Immediate TERM control | 0 | 0 | 0 |
| Delayed TERM return | 2, false failure | 0 | 0 |
| Delayed KILL return, child ignores TERM | 2, false failure | 0 | 0 |
| Intentionally live child | 2, expected failure | 2, expected failure | 1 |
| Supervisor stop signal | 2, false failure | 0 | 0 |
| Logout request file | 2, false failure | 0 | 0 |
| Leader exits 37; surviving grandchild | 2, false failure | 37 | 0 |

The live-child control suppresses signals inside the fixture only. Both guards
correctly reject cleanup; its queue is empty and its worker is still active.
The controller subsequently releases that worker through a private pipe.
An independent same-user sentinel survives every scenario, then is released
and reaped normally. Fixture children have bounded alarms.

## Correction and diagnostics

The main loop previously drained events, signaled descendants, then checked
elapsed time and failed immediately at the deadline. Time spent signaling,
querying process state or being descheduled could make that first event drain
stale. The final iteration now performs another nonblocking event drain and
`waitpid(WNOHANG)` before deciding whether any tracked child remains.

This final check adds no sleep, retry signal or grace-period extension. It
does not infer completion from PID absence, weaken identity checks or scan
an entire user's processes. Tracking errors still fail the launch. If cleanup
is incomplete, stderr records the leader's reaping status, remaining count,
queue count, and each remaining PID's recorded start identity, generation,
last signal and native process state. The existing `GUARD` summary format is
unchanged. The injection library and fixtures are never installed in the
reusable desktop image.

## Verification and reproduction

The [machine-readable qualification](2026-11-05-cleanup-deadline.json) verifies
the original failing run `native-krgzvjab` and corrected run `native-qjdjzyr_`.
It retains the per-case verdict, independent observations, queue audit and
exact source/binary/archive hashes. The original run intentionally fails its
acceptance gate; it is not relabeled as a passing test.

The candidate also passes 1,536 independently checked child lifecycles as
root and xiritest, with one- and 64-event buffers, plus all eight existing
supervisor scenarios. The latter cover 88 tracked descendants, including
detached children, live/exit bursts, leader and exec failures, logout and
signal shutdown. The original run's smaller native control covers 96 child
lifecycles. Both guests unmount and halt cleanly with unchanged source CHDs.

```sh
python3 scripts/probe-process-tracking.py \
  --bundle .work/images/xiri-netbsd-desktop-20261105-wait \
  --rounds 1 --deadline-tests
python3 scripts/probe-process-tracking.py \
  --bundle .work/images/xiri-netbsd-desktop-20261105-wait \
  --rounds 16 --deadline-tests --candidate-guard --guard-tests
python3 lab/irix-process-tracking/qualify-deadline.py \
  --before .work/process-tracking/native-krgzvjab \
  --after .work/process-tracking/native-qjdjzyr_ \
  --output docs/results/2026-11-05-cleanup-deadline.json --self-test
```

The qualifier rejects four deliberately corrupted observations: a failed
completion verdict, an unread exit after correction, a falsely dead live
control and a lost leader exit status. The 48 existing host unit tests pass.
Guest C sources compile with `-Wall -Wextra -Werror`.

IRIS upstream through `c382cdcc25389769b5ae3a436ae1ff73ae42e964` is integrated
and pushed as `fb24628e1bf97a4f379309c79e808d82929672b7`; the Linux release
build and 431 affected tests pass, with four existing ignored tests. See
[fork development](../FORKS.md) for the Windows conflict and validation limits.
The [host/fork evidence index](2026-11-05-cleanup-host.json) records exact
build and test log hashes.
The experimental guests retain the qualified `819c682` emulator. NetBSD
remains unchanged at `e9ff76a58affee773b767d334f98075bf86daf7e`.

The [replacement CHD record](2026-11-05-cleanup-image.md) covers installation,
cold desktop qualification, memory-pressure checks and manual testing.
