# Native descendant tracking and compview replay

The bounded native checks pass on both the older GIMP image and the current
native-wait image. The paired compview replays also verify descendant cleanup.
The historical tracking failure remains unexplained; these results do not
establish its cause or qualify compview's application functionality.

There is no NetBSD kernel or production runtime change in this cycle. The
[current manual CHD](2026-11-05-native-wait-image.md), its selected state and
pinned `819c682` emulator remain unchanged. The new maintained
[tracking lab](../../lab/irix-process-tracking/README.md) provides an independent
test of the native notifications used by the session supervisor.

## Independent native checks

The fixture publishes child identities through a pipe before comparing them
with kernel `NOTE_CHILD` and `NOTE_EXIT` notifications. It verifies the parent
PID, birth-before-exit ordering, exit status, complete counts and absence of
duplicate or trailing events. Direct children are reaped explicitly.

The three modes cover immediate exits, grandchildren that must survive their
parent and be reparented, and children released together after every birth is
known. Each runs for 16 rounds with eight children per round, receiving either
one or 64 events at a time, as root and UID 1234. The final native test ELF is
byte-identical across both images. Tests run beside the native xdm greeter;
these event checks do not execute foreign applications.

| Image | Complete child lifecycles | Installed supervisor scenarios | Guest halt |
| --- | ---: | ---: | --- |
| `20261103-gimp` | 1,536 | 8 | Clean unmount and halt |
| `20261105-wait` | 1,536 | 8 | Clean unmount and halt |

The eight supervisor scenarios use the existing installed guard and maintained
adversarial fixtures: a TERM-resistant child, detached descendants, a ready
25-process live burst, a 49-process exit burst, leader failure, exec failure,
logout request and signal shutdown. Every scenario reports
`absent=1 valid=1 remaining=0`; an unrelated process of the same user survives.
The 16 scenarios cover 176 tracked descendants in addition to the 3,072 native
event-test lifecycles.

The [evidence index](2026-11-05-process-tracking.json) retains exact source,
ELF, kernel/module, CHD, harness and observation-archive hashes, outputs and
per-scenario guard results. Each disposable guest halts cleanly, and its
source CHD remains unchanged. The runner rejects incomplete output or missing
cleanup/archive evidence.

## Compview comparison

Both replays use the maintained catalog observer unchanged, with
`--partition 2 --after-case app-097 --limit 1`. Each first passes the native
child-completion and timeout controls, then starts the original compview under
the unprivileged 4Dwm session.

| Observation | Older GIMP image | Current native-wait image |
| --- | --- | --- |
| Tracked descendants | 2 | 2 |
| Final guard | `absent=1 valid=1 remaining=0` | `absent=1 valid=1 remaining=0` |
| Owned PIDs in final process snapshot | Absent | Absent |
| First bounded X query | Alarm, status 142 | Alarm, status 142 |
| Later and post-cleanup X queries | Status 0 | Status 0 |
| Guest shutdown | Clean | Clean |

The query timeout therefore recurs without the earlier cleanup failure.
This does not identify the reason for the X query delay, prove normal GUI
exit, or demonstrate useful application interaction. The catalog checklist
records the new cleanup observation and retains the old failure separately.

The original November 3 run, `survey-2-_6lek34z`, reported
`absent=0 valid=0 tracked=2 remaining=1`, with elapsed time 64,142 ms. The
tracked PIDs were already absent from retained process snapshots. Native exit
notification occurs late in process teardown, so a PID's absence alone does
not establish that the supervisor received its exit notification. Neither a
live-process leak nor a lost kernel notification has been demonstrated.
Keep that observation, the earlier bootstrap stalls and the batch shutdown
failure open until their cause is measured.

## Fixture corrections and limits

Two preliminary runs used a version that allowed grandchildren to race their
parent's exit. Both passed the event checks, but those runs are excluded from
the final totals; the final fixture requires reparenting explicitly.

The older preliminary run could not execute the supervisor script because
copying from its CD preserved mode `000`. Root could compile the C sources,
but xiritest could not read the shell script. This is the retained older CD
permission behavior, not a descendant-tracking failure. The runner now uses
`install -m 444` for its fixtures. The corrected older-image run passes all
eight scenarios. Both preliminary guests also halted cleanly.

The first current-image run took time to reach serial login. Its pre-login
CPU/kernel/framebuffer snapshot is retained locally; it subsequently reached
login within the existing deadline and completed. That snapshot is not a
reproduced boot hang.

No cleanup criterion or production deadline was weakened. These finite runs
do not establish reliability under arbitrary memory pressure, scheduling
delays or PID reuse. A future recurrence needs the guard's remaining identity,
pending notification and native teardown state captured together before
shutdown. Existing failure capture preserves CPU, stack, kernel messages and
scanout when available.

## Fork and host validation

IRIS upstream through `54ea8c05afa2996c192768cc72bbe6fcb3c01f5f` is merged and
pushed on `xiri` as `e67e3cc3731c17de1a0c226dbd2d4448d07ec80f`. The release
build, 356 Odyssey tests and 158 network tests pass; four Odyssey tests remain
ignored. Host irix-sh controls check timeout reset and the 255/256-byte command
and text-line boundaries. A live IRIX 6.5.30 NFS/telnet session was not tested.
See [fork development](../FORKS.md) for the conflict resolution and pins.

The 48 host unit tests pass, Python syntax checks pass, the catalog renderer
retains all 166 entries, and `./xiri doctor` verifies all 16 selected immutable
artifacts. The renderer's maintained inputs now also preserve the earlier font
and terminal job-control notes. All owned test IRIS instances are stopped.
