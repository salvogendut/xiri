# Native multi-child wait accounting

Terminal qualification exposed a negative `p_nstopchild` in a native shell.
A separate native program reproduced a missed stopped child under both root
and UID 1234. This is shared NetBSD wait code, not an IRIX ABI translation.

`kern_sig.c` removes an uncollected stop from `p_nstopchild` when SIGCONT
resumes a child. `find_stopped_child()` incorrectly subtracted again when
WCONTINUED consumed the continuation. The count could reach zero despite a
pending stop behind a live sibling, allowing the child-list scan to return
no event.
Independently, the same shortcut skipped continued children behind a live
sibling because continued events are not included in this count.

The fix clears `PS_CONTINUED` when the continuation is consumed, without
changing stopped-child accounting. It also scans past live siblings when
WCONTINUED is requested. WNOWAIT retains the event. Native signal policy and
IRIX's opt-in SA_NOCLDSTOP policy are unchanged.

The NetBSD fork's `tests/lib/libc/sys/t_wait.c` adds two regression cases:

- `wait6_continued_multiple`: three children, P_ALL/P_PGID selection behind
  live siblings, repeated WNOWAIT, consuming once, and four stop/resume cycles
  alternating collected and uncollected stops.
- `wait6_stop_exit_after_continue`: consume one child's continuation, then
  select a different child's stop behind a live sibling and collect an exit.

The second case reproduces a missed stop. Its exit collection is a regression
control: NetBSD moves an exited child to the head of the list, so this fixture
does not reproduce a missed exit.

Compile the actual fork test on the native guest and run both cases, plus
the existing `wait6_stop_and_go` and `wait6_stopgo_loop`, under root and an
ordinary user. The lab runner owns the process group, bounds execution and
checks that no descendants remain. The tests also kill and reap their own
children on normal completion and assertion failure.

```sh
cc -O2 -Wall -Wextra -Werror -Wno-array-bounds -Wno-stringop-overflow t_wait.c -latf-c -o t_wait
./runner ./t_wait 1234 1234 1234 1234 -- -r /dev/stdout wait6_continued_multiple
./runner ./t_wait 1234 1234 1234 1234 -- -r /dev/stdout wait6_stop_exit_after_continue
```

The warning exception is for the existing coredump test's deliberate write
to address 8; the new wait tests require no warning exceptions.

The matching core/module artifacts are in `build.json`; `baseline.json` pins
them for the disposable image builder. The earlier job-control build and
image are retained separately. This reproduction does not establish the
cause of the older catalog bootstrap or shutdown stalls.

NetBSD `xiri` commit `e9ff76a58affee773b767d334f98075bf86daf7e` contains
the fix and tests. `source-equivalence.json` ties its committed file bytes
to the retained build. The IRIX module binary is identical to the v3
job-control module; only the native core changes. Its full 264 sleep/256
child-state replay and 48 signal/48 sproc/144 process regressions also pass.

The [paired record](../../docs/results/2026-11-05-native-wait.json) verifies
four failures in the new cases on the unfixed core, four passing old controls,
and all eight passes after the fix. The same native ELF runs on both cores.
Every run reports absent descendants. The ATF cases run inside the lab's
bounded process-group runner; ATF itself warns when invoked without atf-run.

`scripts/qualify-native-wait.py` checks the record framing, exact case set,
expected baseline assertions, statuses, cleanup and common ELF/source hashes.
Negative controls reject an unexpected signal, timeout, surviving group and
missing case. Earlier compiler-warning and shell-command setup failures are
excluded from the paired records.
