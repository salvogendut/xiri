# IRIS upstream integration, 2026-11-17

Integration of upstream `main` through
`878bc6dadc6523c53aceeeeb9c8f30f827acfd11` into the IRIS `xiri` branch,
starting from `707912ddf39ad5b768b433f08369214f0205643e`. The incoming range
contains 125 commits. The final revision and validation results are recorded
in the [JSON record](2026-11-17-iris-upstream.json).

The merge is `6420c255` on the IRIS fork's `xiri` branch.

Upstream supplies the common display refresh thread, expanded resident
Newport GPU rendering, shared SN machine constructors, CPU compile-pool and
clock changes, and the generic graphics-board picker. The merge uses these
implementations while retaining Xiri's NetBSD CPU/device fixes and frontend
interfaces.

The conflict resolutions move borrowed SCSI/Fibre Channel access into the
shared SN machine and retain injected serial/audio transports and headless
Onyx construction. `FuelConsole` is a compatibility alias for upstream's
shared console type, allowing the existing Prismatic frontend to compile.
The obsolete board-specific CPU-counter implementations and graphics picker
are replaced by their upstream equivalents.

Newport GPU command capture now decodes physical RGB24 write masks into the
same packed framebuffer representation as the interpreter and raster JIT.
Register values remain unchanged. Snapshot guards use the configured
frontend snapshot directory, including upstream's incomplete-resident-snapshot
marker. The RTC calendar cache uses upstream's clock abstraction.

## Validation

Validation uses the existing `xiri-iris` build container, Rust
`nightly-2026-10-28`, two build jobs, and an isolated target directory.
The ordinary workspace/JIT suite, optional wgpu backend, interpreter cache,
instruction-driven clock, Newport hardware parity and Prismatic consumer
checks are recorded separately in the JSON record.

The first suite exposed two upstream test expectations that needed adapting:
RGB24 fast-clear pixels use the physical plane layout, and an explicitly
headless Onyx may omit its graphics brick. Two filesystem tests require a
non-root user; they are checked separately from the root-container suite.
Both the host-transfer and reverse-fill RGB24 fixtures now use independently
decoded pixel values.

| Check | Result |
| --- | --- |
| Serial core, JIT and wgpu enabled | 5,705 reported passes; two failures explained below; 102 ignored, two permission cases filtered |
| Remaining workspace binaries, integration tests and doctests | 195 passed; 17 ignored |
| Final merge-specific checks | 10 passed, including the corrected reverse-fill expectation |
| Default-feature CPU and RTC | 393 passed |
| Instruction-driven clock and RTC | 19 passed |
| JIT equivalence with opt-in optimizations | 283 passed; two ignored |
| Filesystem permission cases, unprivileged | Two passed |
| Newport Vulkan raster and production lifecycle | Seven passed |
| Newport common window presenter | Passed on the real display |
| Prismatic `63b6cc86`, JIT and wgpu enabled | Compile check passed |

The serial core run completed with one outdated RGB24 reverse-fill
expectation, subsequently corrected and passed, and one remaining IMPACT
GPU readback failure. The IMPACT test
`dev::mgras::wgpu::tests::transfer_reads_see_the_drawing` fails at step 64,
line 4 both in the merge and in a pristine `878bc6da` control build, with
identical expected and actual byte arrays. It is a confirmed upstream
baseline failure on this host, not a resolved result or a new Xiri regression.
The IMPACT implementation and common GPU code match upstream.

An earlier parallel core run terminated inside the host Vulkan loader during
IMPACT tests. The serial run completed; this does not establish the cause of
the parallel crash. No crash workaround was added. Xvfb also lacks the DRI3
support required by the presenter test, which passed on the host display.
Hardware checks used Vulkan on the AMD Radeon 780M (RADV, Mesa 26.2.5).

Five real-device audio tests report success after returning early because
`IRIS_AUDIO_LOOPBACK` is unset. Their skipped status is confirmed separately;
the pass counts above do not establish real-device audio coverage.

This is source integration and regression qualification. No new IRIX
6.5.22 or 6.5.30 desktop image is published, and neither release's last
qualified donor, preview CHD or emulator pin is replaced. The NetBSD and
Prismatic checkouts remain unchanged. Prismatic is checked from a disposable
source snapshot against the candidate IRIS.

Prismatic's `iris_headless_counters` build-time probe still looks in the old
IP27 source file. Upstream moved the method to `sn.rs`; the probe controls an
ignored frontend test, while the runtime calls the unchanged Workstation
interface. Updating that probe belongs to a later Prismatic cycle.

## Reproduction and cleanup

Use the merge revision and commands from the JSON record. The temporary
topic branch, worktree, consumer snapshot and build cache are removed after
validation and push. Compact logs remain under
`.work/iris-upstream-20261117/`; their hashes and cleanup measurements are
recorded in the JSON. Existing pinned lab worktrees and qualified artifacts
are preserved.

Removed 5,200,445,440 bytes of allocated temporary file footprint (4.84 GiB),
including both temporary worktrees, the build cache and the frontend source
snapshot. This measures removed file allocations, not exclusive physical
space reclaimed on a filesystem that can share blocks. No owned emulator or
build process remains.

The parallel test crash also produced a system-managed core dump outside
the project. It occupies 301,891,584 allocated bytes (about 288 MiB).
The journal metadata is retained with the logs. Removing the dump requires
root access; `sudo -n` reported that a password is required. The exact
cleanup command is:

```sh
sudo rm -- /var/lib/systemd/coredump/core.iris-b7aa503925.589824.03901678364d4b22abe01d06884bdc42.538795.1794952982000000.zst
```
