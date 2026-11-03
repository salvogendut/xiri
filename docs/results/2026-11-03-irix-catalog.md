# Icon Catalog startup survey, 2026-11-03–04

The requested [per-tab checklist](../ICON-CATALOG.md) now preserves all 166
registered entries from the supplied IRIX 6.5.22 installation. There are
17 system pages plus the empty user **Blank** page. Clicking the stacked page
edges at the bottom-right opens the [menu of all 18 pages](images/2026-11-03-irix-catalog-pages.png).
Unresolved source links can be omitted by the live catalog; the checklist
keeps them visible as inventory findings.

The survey attempted 124 distinct program targets on disposable copies of the
qualified GIMP CHD. Repeated target paths share an observation, while distinct
aliases with different paths are retained. GIMP, xmahjongg and xclock keep
their prior bounded evidence. The remaining 19 document/web entries, 13
unresolved source links and one directory target need separate handler,
registration or payload checks.

## Startup observations

| Startup observation | Distinct targets |
| --- | ---: |
| Window observed (including dialogs) | 41 |
| No window before timed test stop | 11 |
| Nonzero exit without a window | 42 |
| Zero exit without a window | 17 |
| Signal termination without a window | 7 |
| X observation interrupted | 5 |
| Launch cleanup not verified | 1 |
| **Total** | **124** |

These are observation categories, not application-support totals. Mapped
windows include errors, information and privilege dialogs. A zero exit is
also not proof of success: several wrappers print missing-resource errors
and return zero. The [JSON record](2026-11-03-irix-catalog.json) retains
stdout/stderr, signal/exit information, window names, CPU/process samples,
cleanup status, source hashes and the interrupted attempts.

The most useful findings for later work are:

- **Busy processes without a window:** nine launch targets—Evolution, gedit,
  glynx, GNOME Terminal, midnight-commander, Balsa, Glade, Gnumeric and XChat—
  show the symptom the user reported. Their late samples contain about 30
  seconds of CPU time and roughly 69–73% guest `ps` CPU. glynx and
  midnight-commander invoke GNOME Terminal, so this covers seven underlying
  programs. Investigate a representative in a fresh home before attributing
  the common pattern to a particular interface or library. The bounded
  observation does not establish an indefinite hang.
- **Acrobat:** direct execution exits 127, and a real Applications double-click
  reaches the same missing `/usr/adobe/Acrobat4.0/bin/acroread.dist` helper.
  Only its wrapper was imported. A read-only [source audit](../../lab/irix-catalog/acrobat-source.json)
  locates 84 installation paths, including the actual Reader executable,
  libraries, resources and fonts, for a later import. PDF rendering is untested.
- **NEdit:** the Freeware version launches by double-click, accepts visible
  text, changes to its opened icon and restores the icon after Quit/Discard.
  [Editing screenshot](images/2026-11-03-irix-catalog-nedit.png). Save fails
  with [“can't create”](images/2026-11-03-irix-catalog-nedit-save.png); the file
  remains absent while a native write as the same user under that home’s
  `.xiri-catalog/` subdirectory succeeds. A write control in the exact
  destination directory remains pending. Its exit status was not captured.
  The separate Applications
  `/usr/sbin/nedit` binary fails to execute, so the two entries are not equivalent.
- **Other startup UI:** Xfig, FLUID, grok, plan, several desktop settings panels
  and [Adobe ShowPS](images/2026-11-03-irix-catalog-showps.png) create windows.
  Warnings and setup dialogs are retained in the checklist. Drawing/saving,
  document rendering and normal exits remain unqualified for these entries.
- **Package resources:** AbiWord executables, Mozilla/gFTP runtime programs,
  Emacs Lisp/data, Dia objects, LyX data, xpat2 cards, CaseVision helpers and
  Eclipse bitmaps are missing. Galculator reports missing Fontconfig
  configuration/no fonts plus encoding-conversion warnings. xmcd's wrapper
  selects a missing `bin-NetBSD-ALL` payload; review OS detection as well as
  the installed files. No new vendor resources were imported by this survey.
- **Interfaces and hardware:** xosview reports its unsupported statistics
  interface; XMMS fails to create its control socket; xsetmon needs XSGIvc;
  mag/imged report missing ReadDisplay; audio and flat-panel tools report
  unavailable hardware/driver prerequisites. Graphics initialization,
  shared-arena failures and ToolTalk messages are also recorded. These need
  individual diagnosis rather than blanket library copying.

## Interactive checks and interrupted observations

The [interactive evidence](2026-11-03-irix-catalog-interactive.json) records
Acrobat and NEdit catalog clicks, NEdit's failed save and native write control,
Quit/Discard, FAM execution/exit notifications, the page menu and the empty
Blank directory. Its guest halted cleanly. Other catalog entries still need
real double-click and useful-operation checks.

The original observer's X query alarm interrupted BZFlag, mag and ical
attempts. Their launch guards verified timed descendant cleanup and their
guests halted cleanly. These results remain **observation interrupted**;
they do not establish permanent application hangs. The mag interactive retry
also reports missing ReadDisplay and a failed pointer-steering attempt. Its
90-second guard completes cleanup and X readiness recovers. An unterminated
error line joined the guard summary in that retry's combined log, causing an
anchored text waiter to time out; the subsequent full log establishes cleanup.

For compview, the guard reports `absent=0 valid=0 remaining=1`. Later process
snapshots do not contain that PID, so a live-process leak is not established,
but the tracker did not prove cleanup. The entire disposable guest halted
cleanly. This remains **cleanup unverified**, and needs investigation of both
application startup and process tracking. The qualifier rejects this record
as an ordinary successful-cleanup case.

The initial 22-case remainder also completed its application launches but
failed the guest halt check during shutdown; swap removal was among the
last messages. The owner stopped that emulator; the source CHD was unchanged. Its
[separate diagnostic](2026-11-03-irix-catalog-shutdown.json) is excluded
from the primary counts. All 22 targets repeated in smaller fresh batches
with the same startup categories and clean guest halts. The halt failure remains unresolved and is not attributed to any
particular application.

The maintained observer now records a bounded X-query failure and still
samples processes, without the older unbounded `xwininfo` query. Resumed
runs use that version. Neither an interrupted query nor a failed cleanup is
silently converted into a passing application result. The current observer
records failed X queries for `/usr/sbin/mailbox` and `/usr/sbin/moviemaker`,
while retaining process samples and verified launch cleanup. Captured media and
harness hashes distinguish the versions used by each run.

## Reproduction and validation

Use the [lab procedure](../../lab/irix-catalog/README.md),
[probe](../../scripts/probe-irix-catalog.py) and
[evidence qualifier](../../scripts/qualify-irix-catalog.py). The
[checklist renderer](../../scripts/render-irix-catalog.py) checks inventory
coverage before combining observations with the reviewed UI notes. `--after-case`
continues a partition in a fresh guest after an interrupted attempt. The
qualifier requires complete inventory coverage, matching program/media
hashes, native controls and clean halts for all included result runs.
Completed cases preceding an interruption must match their saved progress
record. Failures retain their explicit status.

The tested image is `xiri-netbsd-desktop-20261103-gimp`, SHA-256
`20b328a070537255c8c0aa4771aefd83cbaa8027208b93bf997302c426ef83b7`,
with its pinned IRIS `819c6825504d40ad9f9aa00554249affd2da9446`,
NetBSD core source `9390bc04900a0d04796d494aca5b00651f12954d` and module SHA
`1f7beada69c483ccdf6f118e5b9bae6210b4cddfe5319f4527fb2b2cf2be4efd`.
Tests log in through native xdm as xiritest, UID/GID 1234, HOME/cwd
`/usr/people/xiritest`, on accelerated 1280×1024 Xorg. The selected source CHD
is unchanged, and this survey does not promote a replacement image.

Native controls cover detached-child ownership, timed child cleanup, mapped
versus hidden windows, and—after the observer update—holding the X server
for 20 seconds, the query's 15-second alarm and subsequent recovery. Python
compilation, shell syntax, inventory/hash checks and evidence qualification
pass. Negative controls reject a missing registration, a changed target,
a duplicate case, ordinary failed tracking and an unclean halt.
`./xiri doctor` verifies all 12 immutable artifacts and host tools.
Both integration forks remain on `xiri`; the daily upstream check again finds
IRIS `28fa516684c54e00e35b258c65e5dcac3a36165c` already integrated.

The [excluded bootstrap records](2026-11-03-irix-catalog-bootstrap.json)
retain the initial CD-script-access failures and two native child-control
timeouts: one interactive attempt and one repeat batch before any application
observation. The latter two copies required forced host cleanup. These
control/shutdown stalls remain unresolved and are not application results. The
corrected boots and the included runs retain their own controls and shutdown
records. All owned IRIS instances are stopped at the end of the cycle.

The launch guard requests a stop at 45 seconds; scheduling and cleanup may
take longer, as recorded by its elapsed counter. Snapshot labels are loop
positions, not exact startup timings. Programs share a home sequentially
within a disposable run, so earlier configuration/helper state can affect
later cases. Standard input is closed. Screenshots are attempted after 12
host seconds from issuing the paced launch command and can precede UI
readiness. Resource limits disable cores and cap output. Useful operation,
normal exit, persistence and document handlers require later targeted tests.
