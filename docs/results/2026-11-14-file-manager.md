# File Manager across filesystems

Date: 2026-11-14. The fresh [two-user GUI run](2026-11-14-file-manager-cold.json),
[328-record ABI check](2026-11-14-file-manager-filemeta.json) and
[full desktop gate](2026-11-14-file-manager-image.json) pass. The new CHD
is selected for manual testing.

The module now implements IRIX `symlink` (1115) and `utimets` (1235),
including File Manager's indirect syscall form. These complete the measured
copy-and-remove path used when moving files and directories between FFS and
tmpfs. The native VFS still supplies ownership, permissions and lookup.
No additional core hook or imported desktop resource is needed.

## Implementation and ABI boundary

The change is confined to `sys/compat/irix_o32/irix_o32.c` in the NetBSD
`xiri` branch. Symlink target bytes remain unchanged; trailing slashes are
removed only from the new link pathname. The timestamp adapter follows
symlinks, uses emulation-root lookup and accepts a null times pointer for
current time. Both application ABIs use two 32-bit seconds/nanoseconds pairs.

The [observer and reproduction instructions](../../lab/irix-pathops/README.md#symlinks-and-nanosecond-timestamps)
cover 41 cases under root and UID 1234, o32/n32, direct/indirect dispatch:
328 original-IRIX observations. They include bad pointers, path errors,
permissions, ownership, target bytes, return registers and before/after
metadata. Reference records are from a disposable IRIX 6.5.22m guest that
shut down cleanly.

Two explicit limits prevent native sentinels changing the meaning of an
IRIX request: invalid nanoseconds and seconds equal to -1 return EINVAL
without changing metadata. IRIX accepts them. The qualifier therefore
requires 304 exact reference records and 24 precisely specified error-policy
records; it does not claim complete timestamp parity. Native controls also
check epoch seconds, contents and an ordinary NetBSD executable.
The fresh CHD's [ABI qualification](2026-11-14-file-manager-filemeta.json)
passes all 328 records with no mismatches and a clean guest shutdown.

The first timestamp observer used the wrong version-3 stat offset; the
retained reference uses word 17, after the padding word. A first native
candidate exposed eight successful no-ops for seconds -1, because native
vnode attributes reserve it as VNOVAL. The final adapter rejects that value.
Those earlier observations are diagnostic, not final acceptance evidence.

## Desktop checks

`scripts/probe-xiri-filemanager.py` uses original menus and real XTest mouse
drags in a fresh CHD under xiritest and xiritest2. It checks different device
IDs before treating a move as cross-filesystem and verifies exact content
hashes, UID/GID, modes and modification times through native tools.

The bounded sequence covers:

- Native create, rename and delete notifications in already-open views.
- A file with a space in its name moved from FFS to tmpfs.
- Collision Cancel, with both files unchanged, and Overwrite.
- A directory containing a file and a relative symlink, preserving mode,
  ownership, link target and saved modification times.
- Permission denial with the source intact, followed by a successful retry
  after restoring destination permissions, without restarting File Manager.
- Rejection at a read-only CD destination with the source intact. This GUI
  test does not establish which access/read-only check rejects the request.
- Normal logout and absence of the session's owned descendants for each user.

A native rename can put the icon in a different slot. An initial diagnostic
drag used the old coordinates and moved nothing. The maintained probe records
the live updates first, then uses the original **Sort → by Name** action to
make subsequent drag coordinates stable. It does not use Sort as evidence of
automatic notification delivery.

The first cold GUI run lost the closing quote after a multiline serial-shell
argument, before any File Manager action. It was cancelled, its shell input
reset and its guest stopped. The cancellation interrupted halt verification,
so this run does not claim a clean shutdown and is excluded from acceptance. The focused
probe now types the terminal command without an embedded serial newline and
delivers Return as a separate XTest key event. Its fresh rerun completes
the whole sequence without manual recovery and shuts down cleanly.

## Source and image provenance

The [module build](../../lab/irix-pathops/filemeta-build.json) records its
imports, relocations and source hashes. Its SHA256 is
`89d63b8dd67b5fa062edc0a7540a38f84630a32cdeacadd7920b6534e592f19e`.
The [source-equivalence record](../../lab/irix-pathops/filemeta-source-equivalence.json)
matches committed NetBSD `xiri` source
`633a79f257a92ff89437f7e17b0b42b49cee3e99` and separately binds the reused core
artifacts. The qualifier accepts an explicit record path so older builds'
records and the frozen build manifest remain intact.
The core remains the qualified native-wait build, source-equivalent to
`e9ff76a58affee773b767d334f98075bf86daf7e`. The manual image retains its
qualified IRIS `819c6825504d40ad9f9aa00554249affd2da9446` binary. Module
source and current fork HEAD do not imply that every later core change is
installed.

The independent [IRIS integration record](2026-11-14-file-manager-upstream.json)
updates the fork's `xiri` branch through upstream
`1c9d16adcf9748430e214bda5d7f7fe6aef40e85`, preserving the frontend PCM
factory across the new shared audio renderer. Engine/audio regressions and
frontend checks pass; new audible guest playback was not tested. The
Prismatic fixture/lockfile adaptation is on
[`topic/xiri-audio-renderer`, draft PR #1](https://github.com/salvogendut/prismatic/pull/1).
Its default branch is unchanged.

The requested [NetBSD upstreaming guide](../NETBSD-UPSTREAM.md) maps the
three core dependencies and native fixes to exact source files, distinguishes
src/xsrc/userland work, and records packaging and acceptance gaps.

## Limits and follow-up

Visual review found a retained dialog image in the post-directory-move PNG:
the folder has moved and all native data/metadata checks pass, but the earlier
collision dialog is still pictured over the destination view. The later
permission dialog displays the correct new message. Whether the retained
image reflects window lifecycle or repaint/scanout has not been diagnosed.
This is a remaining visual issue; the qualification covers the listed file
operations and does not claim perfect dialog redraw.

Follow-up: the [desktop-controls investigation](2026-11-14-desktop-controls.md)
identifies a still-mapped collision dialog. Escape had not dismissed it, so
the earlier source-preservation check overstated the Cancel gesture. The
revised probe clicks **Cancel**/**Overwrite** and checks actual window mapping
before continuing. The screenshot did not establish a Newport redraw fault.

These checks cover small local files and directories. Remote filesystems,
full-disk failures, immutable flags, concurrent pathname replacement, richer
metadata and wider file types remain unqualified. Existing Dumpster and
same-filesystem checks are recorded in the [preceding cycle](2026-11-13-file-manager.md).
This cycle does not repeat every application survey, shell-job sequence or
earlier ABI suite.


## Manual image

The full image gate passes full-screen xdm, both IRIX users, native ctwm,
both logout menus, startup recovery, catalog launching, 345 native text
comparisons, three winterm checks and clean shutdown. The 63 repository
tests also pass. The installed-file comparison finds only the module changed;
the [inventory delta](2026-11-14-file-manager-inventory.json) records both hashes.

Run the selected image from the repository:

```sh
./xiri run
```

Or run `.work/images/xiri-netbsd-desktop-20261114-filemanager/run-iris.sh`.
Log in as `xiritest` / `xiritest` or `xiritest2` / `xiritest2`. Native ctwm
remains available as `netbsdtest` / `netbsdtest`, with wheel membership.
The CHD SHA256 is `0df71bb25749d8dc30d456c6459f0236c0f64154a640522873f6137e45bd4111`.

PNGs show the [moved directory](images/2026-11-14-file-manager-xiritest-directory-moved.png),
[second user's directory](images/2026-11-14-file-manager-xiritest2-directory-moved.png),
[collision](images/2026-11-14-file-manager-xiritest-collision-overwrite.png),
[permission failure](images/2026-11-14-file-manager-xiritest-permission-denied.png)
and [full desktop](images/2026-11-14-file-manager-desktop.png).

## Cleanup

The [cleanup ledger](2026-11-14-file-manager-cleanup.json) records stopped
owned guests and removed disposable media, redundant raw seeds and temporary
emulator/frontend builds. Qualified CHDs and manual state remain intact, with
one reusable raw seed for the selected image. Logs, source/build pins and PNGs
remain available. Allocated sizes include shared reflink extents and are not
the same as physical filesystem space recovered.

The removed files account for **26.9 GiB of allocated space**. Filesystem
free space increased by **8.06 GiB during the final cleanup**, measured after
syncing; the earlier build/reference cleanup did not retain a full before/after
measurement. All seven recorded owned guest process groups are absent.
