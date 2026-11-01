# IRIX directory creation

This lab measures trap1080 (`mkdir`) on the supplied IRIX 6.5.22m installation
and compares it with native filesystem creation through the NetBSD IRIX
personality. The [qualified result](../../docs/results/2026-11-01-irix-mkdir.md)
passes 3,200 records, 1,540 independently verified directory creations and
44 native/vendor controls. It targets the session-directory failure reached by bgicons,
fm and Icon Catalog after pthread initialization.

The reference contains 1,280 records: 32 pathname/mode cases, two inherited
umasks, five real/effective credential combinations, both ABIs and both trap
dispatch forms. Each record captures the return registers, effective directory
metadata through the measured wide xstat layout, identities before/after and
fixed sentinels. Fixtures use no libc. The bounded native runner controls
credentials; the original-IRIX fixture uses the reference's credential calls.

Cases cover normal/zero/special/type/high mode bits, existing files and
directories, final and parent symlinks, dangling links and loops, missing and
non-directory parents, denied search/write, owner/group permissions, a parent
configured with setgid, trailing slashes, empty paths, bad pointers, overlong
components/paths and page-end strings. Two absolute paths distinguish native
fallback from creation under an existing `/emul/irix` parent.

The adapter copies the original pathname with its length bound, removes final
slashes as required by the measured IRIX existing-file result, and calls native
`do_sys_mkdir`. Native credentials, vnode authorization, umask, read-only mount
checks and filesystem ownership policy remain authoritative. FFS parent-group
ownership is retained and explicitly separated from reference metadata.
This adds no new core-kernel hook for the eventual loadable-module target.

The qualifier checks complete foreign records and independent native
before/after `find`/`stat` snapshots. Every preexisting pathname must retain
its type, mode and owner/group; only the expected new directories may appear,
with verified native metadata. The native namespace must remain untouched
when the emulation parent is selected. Native creation controls also test
native namespace isolation, duplicate creation, removal and read-only-media
denial. Native o32 and vendor asa/echo controls run before/after the matrix.

## Reproduce

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build-irix-mkdir.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-reference-mkdir.py \
  --seed-directory .work/irix-reference/init-threads-records-runs/ci-8hf99523
```

Build the two configs here sequentially with `XIRI_BUILD_JOBS=2`, the NetBSD
`xiri` checkout and separate `.work/netbsd-irix-mkdir[-o32]-v2-build` outputs.
The matching toolchains can be shared with the preceding initialization lab;
record the matching `build-arch` when preparing a directory that links an
existing toolchain. Preserve the earlier candidate build directories.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/pin-irix-mkdir.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/pin-irix-mkdir.py --kernel-abi o32
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-mkdir.py \
  --seed-directory .work/irix-x11-fonts/runs/ci-_6m3l41w
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-mkdir.py \
  --seed-directory .work/irix-x11-fonts/runs/ci-_6m3l41w --mode ordinary
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-mkdir.py \
  --seed-directory .work/irix-x11-fonts/runs/ci-_6m3l41w --kernel-abi o32
```

`qualify-irix-mkdir.py --reference REF RUN... --output REPORT` requires the
complete three-run native matrix. `--export-reference` freezes the decoded
original oracle after checking its structure and source hashes. Capturing
records alone does not constitute a pass.

`probe-irix-desktop-mkdir.py` repeats the existing bounded desktop session with
the new LP64 kernel. Keep native shell/window checks separate from new-client
progress and preserve failed attempts. Raw disks, vendor files and traces stay
in ignored `.work`. Directory removal/rename, waits, file notification and
other full-desktop services remain separate work.

The [desktop result](../../docs/results/2026-11-01-irix-desktop-mkdir.md) records
bgicons exit zero, Icon Catalog’s empty fallback with unstaged page
data, and fm crashes after pipe/sgikopt ENOSYS. The independent desktop
qualifier retains ordinary-mode shell/capture failures alongside CI success.
