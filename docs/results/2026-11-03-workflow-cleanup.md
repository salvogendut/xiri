# Current workflow consolidation, 2026-11-03

The desktop has reached a useful development baseline. The user reports that
many tools work in a quick manual survey, while others need tuning. This cycle
consolidates the everyday workflow before the requested module/service/login
packaging work. It does not broaden per-application compatibility claims.

The completed workflow is qualified by 18 host checks, a direct CHD boot and
full graphical login/logout replay. The existing manual CHD remains selected.
IRIS upstream integration is separately validated and pushed as `c84757d`.

## Changes

The root `./xiri` entry point reads `config/development.json` and the selected
image's manifest. It provides status, prerequisite/artifact checks, manual
launch, disposable CHD qualification, reusable seed preparation, isolated fork
builds and packaging of a qualified raw run. Builds resolve the worktree that
owns `xiri`; they never switch a shared checkout. New output lives under
`.work/builds/`, separate from qualified builds and images.

Automated commands record arguments, exit status and logs under
`.work/workflows/`. Interrupts go to the child probe and wait for its existing
cleanup. `check` writes a new qualification JSON and PNG without promoting or
mutating the manual bundle. The current image and its tested emulator remain
selected. Manual NVRAM and overlays are user state: artifact checks do not
reject them for changing, and seed preparation excludes a changed graphical
NVRAM instead of failing or resetting it.

The current CHD and prepared-desktop probes now share UART pacing, compressed
binary output transfer, captures and bounded waits in `scripts/xiri_lab`.
Boot, shutdown and owned-process teardown remain with `probe-netbsd.py`.
Evidence includes hashes of the shared helpers. Historical probes, pinned
worktrees and artifacts are retained.

The README now describes the current desktop and routine commands. The old
checkpoint narrative is retained in [HISTORY.md](../HISTORY.md); the
[development guide](../DEVELOPMENT.md) documents the maintained interface.
The [roadmap](../ROADMAP.md#next-packaging-phase) records the next deployment
work: separate services and per-user sessions, a boot-loadable compatibility
module modeled on `compat_linux`, normal xiritest login via xdm, and native
IRIX clogin later. Those runtime changes are not implemented in this cycle.

## IRIS upstream integration

Fetched `https://github.com/techomancer/iris.git`, reviewing 16 commits between
`2eb811f43a69a9dec7f0ceb50cb439b7e088845c` and
`68f4e4a6d56d85e109ef3d4363854df1cd39cfda`. The updates cover block-device
handling and CHD overlay durability, serial logging, optional virtio-serial,
idle parking, NFS execute bits, configuration validation and CLI selection.

Merge **`c84757d2f812412581253352c9947c1058e9cf3a`** is pushed to `origin/xiri`.
It integrates from `819c6825504d40ad9f9aa00554249affd2da9446` on the `xiri`
worktree `.work/iris-upstream-sproc`. Conflicts in the O2/Octane constructors
and documentation index were resolved while preserving the fork's embedded
flash firmware. The new `--validate` path now respects embedded selection and
strict errors for explicit missing firmware overrides; regression tests cover
empty/default/explicit paths and invalid default candidates.

The first workspace run found a new upstream test selecting the default
R4400 CPU for an Octane. The virtio-serial test fixture now selects a supported
CPU for each profile and checks the actual O2 unsupported-transport error.
Runtime CPU validation remains intact. The initial failure and corrected
validation logs are retained under `.work/streamline/`.

The integration build uses `.work/target-iris-streamline`, Rust
`nightly-2026-10-28`, locked offline dependencies and two build/test jobs.
It is separate from the pinned desktop backend. NetBSD source and the
independent `../iris` performance checkout were not edited by this cycle.
Separate performance work subsequently advanced `xiri` to `3b854a8` and
returned branch ownership to `../iris`. That tip contains this cycle's tested
`c84757d` merge; its additional cache changes belong to the separate cycle
and are not included in this cycle's emulator qualification. The old worktree
is now detached at `26771f9` and is left untouched. The workflow correctly
discovers the new branch owner.

## Validation and artifacts

See the [machine-readable record](2026-11-03-workflow-cleanup.json) for final revisions, commands,
run directories, source hashes and outcomes. Host checks exercise malformed
binary transfers, command/monitor failures, missing or mismatched immutable
artifacts, preservation of mutable NVRAM, worktree selection and interruption
cleanup. Build, run and image commands are checked in dry-run mode; this cycle
does not rebuild a kernel or package another identical desktop CHD.

Guest checks use the current `20261103-newport-xmahjongg` bundle and its exact
`819c682` emulator. The cold-boot probe checks the original application/catalog
payload, native Render, HOME, catalog launch, desktop resources and cleanup.
The prepared-disk probe additionally checks graphical console input, both
logout routes and fixed-board xmahjongg interaction. These retain the known
limitations around winterm startup metrics, broader graphics operations and
incomplete application compatibility.

The host suite passes **18 checks**. IRIS's workspace suite passes, including
2,563 core-library checks (33 ignored) and 183 Newport checks, with its ancillary
workspace suites also passing. The targeted idle-parking run passes 25 checks.
Both `iris` and `iris-ci` build. Eight CLI/configuration cases pass: help, the
selected Indy configuration, and embedded/default/explicit-missing flash PROM
selection for O2 and Octane. The two missing explicit paths correctly exit 1.

The [cold-boot qualification](2026-11-03-workflow-cleanup-image.json) passes,
including clean shutdown and an unchanged base CHD. Its
[PNG](images/2026-11-03-workflow-cleanup-image.png) shows the catalog-launched game.
The selected manual image remains the same; this is a fresh observation of it.

The first prepared-desktop replay (`ordinary-rc2e6pvx`) passed graphical
login, Toolchest logout and all four xmahjongg capture comparisons, but a
quote was dropped from a diagnostic UART command during the second session.
The shell waited for the unfinished quote and the probe timed out. This is
retained as a failed replay, not a successful overall result. The shared
sender now allows 20 ms between bytes instead of 5 ms; both maintained guest
checks were rerun with that conservative diagnostic pacing. No desktop or
kernel code is changed for this transport adjustment.

The next CHD observation (`chd-dnf0xk5g`) reached catalog launch and capture,
but failed the old RPC log assertion: the historical count decreased from two
to zero. That is consistent with log rotation, rather than a newly emitted
warning. Its guest also halted cleanly. The image probe now follows new
syslog messages with native `tail -F`, confirms START/END markers from `logger`,
and rejects any new bind warning. Historical counts remain diagnostic only
for these new observations. The qualifier retains the old rule for old results.
Four host regressions cover rotation, a new warning despite a decreasing total,
an incomplete observer and the historical rule.

The paced prepared replay (`ordinary-t042ou24`) completed graphical login,
both logout routes and exact game captures before the same historical-count
assertion failed. The live observer is therefore used in both maintained
probes. That intermediate replay is retained as failed overall, with its
successful subchecks recorded separately. Both failure paths halted their
disposable guests cleanly.

The corrected CHD check (`chd-v3krnbq0`, workflow `check-9kenk7jc`)
passes the full qualifier, including the live RPC observer, native Render,
catalog double-click, HOME, resource hashes, service/client cleanup and PNG
fidelity. It halts cleanly and leaves the base CHD unchanged.

The final prepared replay (`ordinary-e5xx3o99`) also passes: graphical console
login, xiritest identity/HOME/cwd, both logout routes, two native Render passes,
no new RPC bind warnings, installed-file hashes and clean shutdown. Initial,
move, undo and resize/restore game captures each match all **617,684 client
pixels** of the prior qualified capture. The raw seed remains unchanged.
The final process audit finds no remaining owned emulator/group processes
and no other standalone IRIS processes. All six guest runs, including the
failed observations, halted cleanly.
