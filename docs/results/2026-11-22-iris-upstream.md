# IRIS upstream refresh and binaries, 2026-11-22

The IRIS `xiri` branch integrates 101 upstream commits through
[`6ec1ebf3`](https://github.com/techomancer/iris/commit/6ec1ebf379228d572026a9ae8d291511ed28af74),
starting from `6420c255`. Merge `e54410de` and test adaptation `0bc52567`
form the refreshed source. Full revisions, hashes and qualification records
are in the [JSON record](2026-11-22-iris-upstream.json).

Notable upstream changes include NetBSD Indy keyboard translation and R5000
cache configuration, JIT flush/deadlock fixes, SCSI DMA wakeups, O2 boot/reboot
work, Octane PCI decoding, and graphics fixes. The merge replaces our keyboard
translation and cache-line implementations with upstream's versions and removes
their superseded local tests and notes. The fork's delta drops from 115 files
with 4,960 added lines to 113 files with 4,840 added lines.

Frontend storage, audio and serial interfaces, headless Onyx construction,
Ultra64 bridge lifetime protection, and the full O2 PCI address decode remain.
The existing compile-pool regression now supplies upstream's CPU selector.

## Binaries and manual use

The Linux x86-64 binaries are in `.work/emulators/iris-xiri-20261122/`:

| Location | Build |
| --- | --- |
| `iris`, `iris-ci` | Links to the interpreter pair in `interpreter/` |
| `accelerated/iris`, `accelerated/iris-ci` | CPU and graphics JITs, idle pause, wgpu and graphics tracing |
| `iris-gui` | Link to the bundled GUI in `accelerated/` |

Builds use Rust `nightly-2026-10-28`, release optimization, no LTO, 16 codegen
units, and no debug information. Each directory contains a source/feature/hash
manifest. The final interpreter rebuild is byte-identical to the pair used
for its desktop checks.

From the Xiri repository, run either preview with the new interpreter:

```sh
./.work/emulators/iris-xiri-20261122/run-6.5.22.sh
./.work/emulators/iris-xiri-20261122/run-6.5.30.sh
```

Select the JIT build with `XIRI_IRIS_BUILD=accelerated` before either command.
The launchers use the corresponding existing November 15 preview folder,
including its manual-test overlay. The original image launchers and embedded
emulator binaries remain available. These are executable refreshes; the donor
images, vendor profiles, native kernel/module and CHDs retain their existing pins.

## Validation

Both vendor releases are checked separately with
[`probe-iris-desktop.py`](../../scripts/probe-iris-desktop.py), using private
disk copies and overlays. The acceptance sequence checks native disk boot,
the IRIX compatibility module, 1280×1024 xdm, the `xiritest` desktop and IRIX
shell, the user's identity/home/current directory, logout, the `netbsdtest`
ctwm session, and clean shutdown. PNG captures and detailed results remain
under `.work/iris-upstream-20261122/`.

| Check | Result |
| --- | --- |
| Interpreter core | 4,983 passed, 55 ignored; two permission cases run separately |
| Filesystem permission cases, unprivileged | Two passed |
| JIT/GPU core, serial | 5,818 passed, one known failure, 104 ignored |
| Remaining workspace, including GUI | 209 passed, 14 ignored; all 120 GUI tests passed |
| Documentation tests | Three ignored, none failed |
| Standalone GUI | Window presented; graceful close returned zero |
| Interpreter desktop, 6.5.22f/R4400 | Passed, including native ctwm and clean halt |
| Interpreter desktop, 6.5.30f/R5000 shadow cache | Passed, including native ctwm and clean halt |
| JIT desktop, 6.5.22f/R4400 | Passed, including paced PS/2 shell input, native ctwm and clean halt |
| JIT desktop, 6.5.30f/R5000 shadow cache | Passed, including paced PS/2 shell input, native ctwm and clean halt |

The first JIT desktop attempts reached the desktop but failed to produce the
shell proof after a long, unpaced monitor keyboard burst. Both passed when the
harness sent one character every 25 ms through the emulated PS/2 controller.
The failed attempts and exact probe versions remain in the evidence; no emulator
change was needed for the paced checks. The interpreter checks used the guest's
existing XTEST helper for the shell command and PS/2 input for xdm credentials.

Desktop captures: [6.5.22](2026-11-22-irix-6.5.22.png) and
[6.5.30](2026-11-22-irix-6.5.30.png). Both use native Xorg at 1280×1024;
the emulator PNG includes two additional pixels at the frame edge.

The optional IMPACT GPU test
`dev::mgras::wgpu::tests::transfer_reads_see_the_drawing` still fails at
step 64, line 4. Its expected/actual arrays exactly match the pristine-upstream
control from the [November 17 integration](2026-11-17-iris-upstream.md), and
the upstream IMPACT GPU source is unchanged across this range. No workaround
or unrelated crash investigation is added. Real-device audio loopback is not
qualified by these tests.

## Prismatic consumer check

Prismatic `63b6cc86` needs one adaptation before rebuilding against this core:
`src/machines.rs` assigns a plain `u8` to `origin3200.c_bricks`, which upstream
changed to `Option<u8>`. Changing the assignment to `self.nodes.into()` compiles
in the disposable consumer snapshot and also permits the older plain field type.
The patch and compiler logs are retained with this refresh's evidence. The actual
Prismatic checkout and its existing executable are unchanged; applying and
qualifying its frontend/helper rebuild remains a separate follow-up.

## Reproduction and cleanup

The JSON record lists commands, binary manifests and evidence hashes. The
isolated source worktree and build target are temporary; compact logs, test
scripts, screenshots and the new binaries are retained. Existing pinned lab
worktrees and previously qualified artifacts are preserved.

The integration is pushed to `origin/xiri` at `0bc52567`; the temporary topic
branch and worktree have been removed. Cleanup removed 7.48 GiB of allocated
temporary files (including reflink-shared disk copies); observed available disk
space increased by 2.34 GiB. The retained binary bundle uses 135 MiB and
the local evidence uses 3 MiB. All test IRIS instances are stopped and the
build container has been returned to its original stopped state.
