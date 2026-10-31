# IRIX access permission checks

This lab measures trap 1033 (`access`) on the supplied original IRIX 6.5.22m
installation and compares the results with the NetBSD personality. The
[qualified checkpoint](../../docs/results/2026-10-31-irix-access.md) passes
4,020 bounded checks and clears the [winterm resource failure](../irix-winterm/README.md).

The original assembly fixtures cover o32/n32, direct/indirect traps, every
standard permission bit and combinations, owner/group/other selection,
searchable and denied directories, symlinks, path lengths, bad pointers,
page-end strings and unusable stack pointers. Six identity combinations
separate real and effective user/group IDs. Each 64-byte record captures all
four IDs before and after the call, its return registers and two sentinels.
The n32 probe also checks a 64-bit saved-register canary.

The reference clears supplementary groups through original syssgi SETGROUPS,
sets IDs through setregid/setreuid, and verifies GETGROUPS still reports an
empty list. The native parent clears groups and sets native IDs before exec.
This experiment does not establish general supplementary-group or ACL
conformance.

The adapter supplies standard modes 0–7. Extra IRIX mode bits are explicitly
unsupported, and native root execute checks remain stricter than IRIX for
files without executable mode bits. The [contract comparator](../../scripts/irix-access-records.py)
retains every native-policy difference in the qualification report.

Absolute-path checks distinguish a present, unreadable `/emul/irix` shadow
from an absent shadow that falls back to the native namespace. The denied
shadow deliberately differs from the readable original-IRIX fixture.

Build and measure:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build-irix-access.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-reference-access.py
```

Build the two kernel configurations sequentially, with
`XIRI_BUILD_JOBS=2`, the authorized NetBSD worktree, separate build/TFTP
outputs and `mips64eb` or `mipseb`. The pinned baseline files identify the
accepted builds. Run the host-side guest harness, not its Python entry
point inside Toolbox:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-access.py \
  --seed-directory .work/irix-x11-fonts/runs/ci-_6m3l41w --mode ci
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-access.py \
  --seed-directory .work/irix-x11-fonts/runs/ci-_6m3l41w --mode ordinary
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-access.py \
  --seed-directory .work/irix-x11-fonts/runs/ci-_6m3l41w --kernel-abi o32
```

Each run clones the stopped seed, verifies inputs, installs the matching
kernel, bounds each foreign process, checks native/o32/n32 controls before
and after, and halts its owned guest. The qualifier checks every record
against the reference and the explicit bounded-mode, native root-execute and
emulation-shadow policies. With `--observe-only`, captures remain uncompared
until the separate qualifier succeeds.

The result report records the accepted run directories and qualification
command. Its `--export-reference lab/irix-access/reference.json` option saves
the original oracle only after every native record passes. The checked-in
reference supports later runs without `--observe-only`.

The [winterm observer](../../scripts/probe-irix-winterm-access.py) uses the
same stopped font/locale seed and the new LP64 kernel. It loads the supplied
Screen font with a native client before launching original xwsh, records
window trees and frames, and captures a checked ptrace trace if xwsh still
faults. Vendor bytes, raw traces and images stay in ignored `.work`.
