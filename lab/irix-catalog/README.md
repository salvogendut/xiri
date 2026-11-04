# Icon Catalog startup survey

This lab records the surveyed image's startup behavior before repairing individual
applications. [inventory.json](inventory.json) maps all 166 catalog entries to
programs, script wrappers, document shortcuts, a directory and unresolved source
targets. Repeated targets share one direct-launch observation; separate catalog
aliases are not assumed to have equivalent double-click behavior.
The [per-tab checklist](../../docs/ICON-CATALOG.md) and
[survey report](../../docs/results/2026-11-03-irix-catalog.md) retain startup
failures, partial use and later functional checks. The bottom-right stacked
page edges open a menu of all 18 pages, including the empty user Blank page.

Run from the repository root, using at most the user's authorized four IRIS
instances. Each partition boots its own disposable copy of the selected GIMP
baseline and logs into xdm as xiritest:

```sh
python3 scripts/probe-irix-catalog.py --partition 0
python3 scripts/probe-irix-catalog.py --partition 1
python3 scripts/probe-irix-catalog.py --partition 2
```

The three partitions contain 40, 42 and 42 launch targets. `--limit 1` runs a
pilot; `--interactive` exposes the existing bounded local request queue instead
of executing the partition. The runner defaults to the historical
`20261103-gimp` bundle. Pass `--bundle PATH` to test another qualified bundle,
such as `.work/images/xiri-netbsd-desktop-20261104-acrobat`. It does not replace
the selected CHD or manual state. A `--seed` overlay must match that bundle's
base CHD; do not reuse an overlay from a different image.

Each launch uses original IRIX sh with the desktop's X authority and native
xiritest identity, HOME and current directory. Standard input is `/dev/null`,
so command-line tools and terminal wrappers require separate interactive checks.
The observation records stdout/stderr, process snapshots and viewable X windows.
A framebuffer capture is attempted 12 wall-clock seconds after issuing the paced
launch command; it can precede readiness. Existence of a window or a PID does not
qualify useful interaction or a normal GUI exit.

`app-guard.c` in each run's media is generated from the maintained native
`runtime/libexec/session-guard.c`, with two checked substitutions: an initial
parent's exit does not stop still-running descendants, and the stop reason
reflects the actual deadline or stop request. NOTE_TRACK ownership and process
identity validation remain in use. Native controls verify an early parent exit
with a detached child, and a timed stop of that child. Another native control
verifies that the X helper includes a mapped window and excludes a hidden one.

The observer stops a remaining application after about 40 seconds; the guard's
45-second deadline and bounded termination escalation provide a second bound.
Such a stop is not reported as an application crash or a normal exit. Resource
limits cap test output; core dumps are disabled. Each completed case must report
verified descendant cleanup before the next case starts. The runner halts its
owned guest and checks the source CHD after completion or failure.

The initial observer stopped its batch when the 15-second X query alarm fired
during BZFlag, mag or ical startup. Their application guards completed timed
cleanup and the guests halted cleanly; these attempts retain an explicit
`observation-interrupted` result. This does not prove a permanent application
hang: input selection and server grabs require interactive interpretation.
The current observer records the X helper's status and still samples processes
when a query fails. It omits the older unbounded `xwininfo` tree query. A native
control holds the X server for 20 seconds, checks that the query exits on its
15-second alarm, and verifies recovery after the server is released. The
snapshot labels are loop positions, not precise startup-time measurements.

Resume a stopped partition after its interrupted case without rerunning the
completed entries, for example:

```sh
python3 scripts/probe-irix-catalog.py --partition 1 --after-case app-047
```

The initial bootstrap attempts could not read the test scripts through `/cdrom`
as xiritest. The corrected setup installs them in `/tmp/xiri-catalog` before
launching applications. Those failed bootstrap attempts are not application
results. A corrected Acrobat pilot confirmed exit 127 for the absent
`acroread.dist` helper and clean cleanup. The read-only
[Acrobat source audit](acrobat-source.json) locates that script, the actual
Reader binary and its resource tree for a later import.
The [bootstrap diagnostics](../../docs/results/2026-11-03-irix-catalog-bootstrap.json)
also retain two native child-control timeouts before any application
observation. Those guests required forced host cleanup; the control/shutdown
stalls remain open and are excluded from application qualification.

After the full partitions finish, qualify their printed run directories:

```sh
python3 scripts/qualify-irix-catalog.py --runs RUN0 RUN1 RUN2 \
  --output docs/results/2026-11-03-irix-catalog.json
```

The qualifier requires complete attempt coverage, a consistent source image,
native controls, clean halts and hashed observation archives. Normal cases
require verified descendant cleanup. An interrupted attempt with a failed
tracker retains `cleanup-unverified`; the successful guest halt supplies the
final cleanup boundary, not a claim that the application guard succeeded.
This occurred for compview: the tracker reported one unresolved identity,
although later process snapshots did not contain that PID. A live-process
leak is therefore not established. Keep both the startup and tracker issue
open. Separately, a 22-case batch failed its guest halt check after completing
its launches. Its [diagnostic](../../docs/results/2026-11-03-irix-catalog-shutdown.json)
is excluded from primary qualification; those launches were repeated in
smaller fresh batches. Do not relax the clean-halt gate to admit that run.
For an observer interruption, it preserves only the completed cases that match
the saved progress record, then includes the interrupted case with that status.
It never upgrades a missing window snapshot to a successful application result.
Review each recorded error and screenshot before assigning a repair priority.
Document/URL handlers, catalog clicks, meaningful interaction, persistence and
normal exit remain separate tests. Programs run sequentially within each desktop;
user configuration and helper state can persist between cases in that disposable
home. Repeat an ambiguous result in a fresh guest before attributing it to the
application or kernel.

After qualification, regenerate the checklist with:

```sh
python3 scripts/render-irix-catalog.py
```

This cycle's renderer checks the inventory digest and complete case coverage
before combining observations with [review.json](review.json). The human
notes distinguish useful partial interaction, hardware/privilege dialogs and
missing resources from mere window creation. The separate
[interactive record](../../docs/results/2026-11-03-irix-catalog-interactive.json)
covers Acrobat and Freeware NEdit catalog launches, NEdit's save failure and
native write control, icon restoration, page navigation and the mag retry.
