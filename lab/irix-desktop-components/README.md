# Original file and icon desktop components

This lab extends the [working 4Dwm/Toolchest/winterm session](../irix-4dwm/README.md)
with the original `fm`, `bgicons` and `iconcatalog` programs. It attempts a home
directory window, background file management, background-icon setup and the
Icon Catalog. This is desktop bring-up; launching these processes alone does
not qualify a complete desktop or file operations.

[SGI's desktop overview](https://techpubs.jurassic.nl/library/manuals/2000/007-2167-006/sgi_html/ch01.html)
identifies the file manager, icons and Icon Catalog alongside Toolchest and
desks. Its [services chapter](https://techpubs.jurassic.nl/library/manuals/2000/007-2167-006/sgi_html/ch04.html)
also describes FAM file-change notifications. Those are behavior targets;
the supplied installation and observed calls determine the exact interfaces.

## Inputs and resource scope

[manifest.json](manifest.json) contains a static n32 closure of 38 executable
and library paths for `fm`, `bgicons`, `iconcatalog` and `fmserv`, plus 16 selected
resource files. It also lists the discovered file-type, icon, catalog-page and
scheme roots. The initial extraction does not copy those entire trees, and
neither inventory presence nor static dependency resolution proves runtime use.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/inventory-irix-desktop-components.py
```

Run the extraction with the host's existing libguestfs installation. It mounts
the supplied raw IRIX disk with `ro,norecovery`, checks its pinned size and
previously selected file hashes, and writes original bytes only under ignored
`.work/irix-desktop-components/root`. Review the generated `inventory.json`
before updating the tracked manifest. Runtime loading beyond the static
closure remains an observation to make.

## Bounded expanded session

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-desktop-components.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-desktop-components.py --mode ordinary
```

The probe clones the cleanly stopped, accepted CI 4Dwm session. It verifies the
PRDA kernel and original pinned IRIS binaries, checks inherited files, and
installs the new closure with explicit readable/executable modes. It preserves
the established `SG_manageSession: false` and `SG_autoSave: false` options;
saved-session file operations and complete login/logout remain separate work.

A native supervisor bounds the reserved-UID session to 120 seconds and checks
all descendants are absent afterward. Native window reparenting, pointer focus,
key delivery and dragging run before application startup. The probe attempts
a typed native shell command through original winterm before releasing the
additional desktop components. It retains this baseline result even if a new
component fails.

Each new launch records its PID, any exit status produced before cleanup,
stdout/stderr and a bounded per-PID syscall trace. An empty exit-status file
is not success: the client or its waiting shell may have survived until the
supervisor ended the job. The probe also captures the process list, X window
tree, root properties and framebuffer before cleanup. It checks native ABI
behavior before and after, confirms native X remains usable, and halts the
guest in a `finally` block. Original bytes, traces, disks and raw frames remain
under `.work`; public reports contain metadata and selected observations.

## Desktop acceptance still required

The [first observation](../../docs/results/2026-11-01-irix-desktop-components.md)
finds an unimplemented `getrlimit(RLIMIT_PTHREAD)` in fm/Icon Catalog startup
and an executable-alignment rejection for bgicons. These are startup failures,
not missing-font evidence. The static closure is available, but none of the new
components is qualified as usable. Preserve any failed native focus check in
the same run separately from successful terminal input.

Verify the captured observations with:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/qualify-irix-desktop-components.py \
  .work/irix-desktop-components/runs/ci-hbta8m3o \
  .work/irix-desktop-components/runs/ordinary-hzy8u164 \
  --output docs/results/2026-11-01-irix-desktop-components.json
```

The qualifier's success means both modes reproduce the recorded blockers and
pass their specified native controls/cleanup. It explicitly records
`desktop_success:false`; it is not a desktop acceptance gate.

The [resource-limit lab](../irix-rlimit/README.md) now clears both initial
blockers with new isolated kernels. Use `probe-irix-desktop-startup-fixes.py`
and its qualifier for the [follow-up](../../docs/results/2026-11-01-irix-desktop-startup-fixes.md).
The original probe and observation remain frozen for reproduction. That
checkpoint reached pthread-table allocation with `MAP_AUTORESRV`; the later
result below clears it.

Qualify directory navigation, icon actions, file updates and service behavior
after startup works. Then address saved-session filesystem calls, desks,
restoration and logout, retaining the working terminal controls. Desktop
artwork, catalog pages, file-type rules and additional helpers belong in the
[resource checklist](../../docs/IRIX-RESOURCES.md) as their use is established.
Keep the [fork workflow](../../docs/FORKS.md) for any emulator or kernel changes;
this lab uses the qualified older binaries until replacement qualification.

The [AUTORESRV result](../../docs/results/2026-11-01-irix-mmap-autoresrv.md)
now clears table allocation. The [next application boundary](../../docs/results/2026-11-01-irix-desktop-autoresrv.md)
is `prctl(PR_INIT_THREADS)`, after both private allocations succeed. No further
image assets are required by this observed failure.
