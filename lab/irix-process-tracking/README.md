# Native child-event tracking

This lab separates native NetBSD descendant notifications and supervisor
cleanup from an application's startup or X11 behavior. It follows the
retained compview observation whose guard reported one remaining process
even though its PID was absent from the process snapshots. Passing a replay
does not establish why that earlier observation failed.

`events.c` uses a pipe to identify all intended children independently of
`EVFILT_PROC`. It then checks each `NOTE_CHILD` and `NOTE_EXIT`, including
the original parent PID, ordering, exit status and duplicate/trailing events.
It exercises three trees:

- Eight children that exit immediately, allowing notifications to accumulate.
- Four children that each create a grandchild in a new session. Each grandchild
  waits for reparenting before exiting, requiring it to outlive its parent.
- Eight children held behind a pipe until every birth record has arrived,
  then released together by closing the parent's pipe.

Both one-event and 64-event receive buffers are tested as root and xiritest
(UID 1234). Sixteen rounds produce 1,536 complete child lifecycles per image.
The fixture checks direct-child reaping too. Children have bounded alarms;
losing the parent releases held children. Run this fixture only in a disposable
guest, never as a host process.

```sh
python3 scripts/probe-process-tracking.py \
  --bundle .work/images/xiri-netbsd-desktop-20261105-wait --guard-tests
```

For the older comparison, use the same command with
`.work/images/xiri-netbsd-desktop-20261103-gimp`. `--rounds` accepts 1–64.
`--guard-tests` also runs the maintained adversarial fixtures against the
image's installed session guard. These cover live/exit bursts, detached
descendants, leader and exec failures, logout, signals, and survival of an
independent process belonging to the same user. They do not rebuild or replace
the installed guard.

The runner verifies the selected CHD, emulator, configuration, boot profile,
kernel/module and installed guard hashes. Each run gets a private CHD copy
and writable overlay, an ordinary graphical emulator, and read-only test CD.
The source image and selected manual state remain unchanged. Evidence under
`.work/process-tracking/native-*` includes the exact harness and fixtures,
guest logs/binaries, source hashes, result JSON and clean-unmount/halt log.
Failure capture includes CPU state, kernel messages and a PNG when available.
A test is successful only with all expected results, an observation archive,
an unchanged source CHD and a clean guest halt.

The paired compview replay uses the existing catalog observer unchanged:

```sh
python3 scripts/probe-irix-catalog.py --bundle BUNDLE \
  --partition 2 --after-case app-097 --limit 1
```

That is a bounded cleanup experiment, not an application functionality test.
Its X-query status and final PID snapshots must be retained alongside the
guard's result; a window-query timeout is not evidence of a leaked process.

## Cleanup deadline experiment

`--deadline-tests` adds seven native scenarios: immediate TERM cleanup,
delayed return after TERM, delayed return after KILL, an intentionally live
child, a stop signal, a logout request, and leader exit with a surviving
descendant. The independent controller publishes the worker PID through a
pipe and checks its native process state after the supervisor finishes. A
same-user sentinel outside the supervised tree must survive every scenario.

The guest-only `delay.so` delays the supervisor for seven seconds after the
selected real signal call. It reads NetBSD's kqueue event count with `fstat`
before returning, without consuming events. After the supervisor prints its
verdict, the library audits real pending events immediately before closing
the queue. It never fabricates a child or exit notification. The deliberately
live control suppresses signals inside the test library; it must still be
reported as incomplete cleanup. The controller then releases that worker
through a private pipe. Alarms and pipe lifetimes bound all fixture children.

```sh
python3 scripts/probe-process-tracking.py \
  --bundle .work/images/xiri-netbsd-desktop-20261105-wait \
  --rounds 1 --deadline-tests
```

The test requires correct outcomes, so an incorrect supervisor verdict makes
the run fail while retaining every scenario, its pending events, process
state and clean-shutdown evidence. An injected delay establishes the tested
ordering; it does not establish why an earlier catalog run failed.

To compare a runtime correction, add `--candidate-guard --guard-tests`. This
builds the maintained guard and installs it only in the disposable guest,
after verifying and preserving the original installed binary. The candidate
source and executable hashes are recorded. The injection library and fixture
are never installed in the reusable desktop image.

The [deadline qualification](../../docs/results/2026-11-05-cleanup-deadline.md)
records five measured false failures and the corrected replay. Verify its
retained archives, exact binaries and independent observations with:

```sh
python3 lab/irix-process-tracking/qualify-deadline.py \
  --before .work/process-tracking/native-krgzvjab \
  --after .work/process-tracking/native-qjdjzyr_ \
  --output docs/results/2026-11-05-cleanup-deadline.json --self-test
```

The self-test rejects corrupted completion, pending-event, live-worker and
leader-status evidence. Passing this experiment does not resolve the retained
historical compview failure.
