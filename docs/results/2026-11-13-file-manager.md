# File Manager and Dumpster — 2026-11-13

The original IRIX File Manager now performs local folder creation, rename,
copy, move, discard, recovery and permanent Dumpster removal under both
`xiritest` and `xiritest2`. The fixes are in the compatibility module and
image configuration; the qualified native-wait core and emulator are reused.

## What changed

Three independent problems blocked the workflow:

1. File Manager requested IRIX filesystem statistics through unsupported
   calls. The module now implements `statvfs`, `fstatvfs`, `statvfs64` and
   `fstatvfs64`, using native filesystem data and credentials. It writes the
   measured 156-byte o32 or 184-byte wide layout, checks overflow and clears
   reserved bytes.
2. The image's own hostname did not resolve. File Manager's local-host cache
   stayed empty and Rename/Make Copy misleadingly reported existing files
   as missing. Image preparation adds `127.0.0.1 xiri-indy` when an IPv4 entry
   is absent. The general runtime installer leaves administrator networking
   configuration alone.
3. Empty Dumpster needed the original `telldesktop` helper and the missing
   `unlink`/`rmdir` calls. The helper is imported unchanged. Removal preserves
   native permissions and final-symlink handling, with measured IRIX
   trailing-slash and error behavior. The misleading removal-permission popup
   was an unsupported syscall, not an ownership problem.

NetBSD `xiri` commit `8bf86afce2afede752c0eae37852e2f2472d91cb` is pushed.
The [module build](../../lab/irix-pathops/filemanager-build.json) and
[source equivalence](../../lab/irix-pathops/source-equivalence.json) retain
the exact inputs. The module SHA-256 is
`d0ad3bd0efd300fbd1d8a93388fc9d27143e72d8f4f33ca83f805f31facf15bc`.
The reused core matches `e9ff76a58affee773b767d334f98075bf86daf7e`; the
included IRIS remains `819c6825504d40ad9f9aa00554249affd2da9446`.
The separate [upstream checkpoint](2026-11-13-file-manager-upstream.json)
records the tested, pushed IRIS source integration.

## Evidence

The fresh packaged-image ABI run passes all
[384 filesystem-statistics records](2026-11-13-file-manager-statvfs.json) and
[336 removal records](2026-11-13-file-manager-remove.json), with no mismatches.
Its [owning run](2026-11-13-file-manager-abi.json) verifies the loaded module,
passes the native control, halts cleanly and leaves the source CHD unchanged.
Cold-desktop qualification is pending. The first cold-check supervisor was
[interrupted](2026-11-13-file-manager-cold-interruption.json) before its final
result; the orphaned guest was halted cleanly. That run is not used for
promotion. Its replacement retains partial checkpoints as well as the final
result, with the acceptance checks unchanged.

The independent [pathname observers](../../lab/irix-pathops/README.md) use
the same executable bytes on IRIX 6.5.22m and NetBSD. They cover 384
filesystem-statistics records and 336 removal records across o32/n32,
direct/indirect traps, root and UID 1234. Filesystem capacities and IDs remain
native: FFS is not made to report the reference disk's XFS values.

The [GUI observations](2026-11-13-file-manager-gui.json) record these original
actions for both users:

| Action | Observation |
| --- | --- |
| Create directory, rename, Make Copy | Original menu/label actions succeed |
| Move, discard, recover | Middle-button drags succeed; recovered content matches |
| Empty Dumpster | Removes files and a directory containing a file; retains `.dumpster` |
| Ownership and modes | UID/GID 1234 or 1237 retained; surviving files remain 0640/0600 |
| Isolation | Each account can read its own file and cannot read the other user's file or traverse their Dumpster |
| Persistence | Both users' recorded paths, ownership, modes and sizes match after a clean restart |
| Normal logout | Both pre-restart sessions save successfully and report zero remaining descendants |

The extra post-restart GUI sequence was interrupted by host cleanup during
the first user's logout, following a stale observation of the earlier halt.
That whole run has `clean_shutdown=false` and is excluded from final ABI
qualification. Its completed GUI/persistence observations are retained with
that limit explicit. The fresh ABI and cold-image checks use separate owning
guests. No kernel or emulator crash fix is claimed from this harness incident.

PNGs show [recovery into File Manager](2026-11-13-file-manager-recovered.png)
and [the second user's emptied Dumpster](2026-11-13-file-manager-empty.png).
The host regression suite passes all 58 tests.

## Manual image

The candidate is `.work/images/xiri-netbsd-desktop-20261113-filemanager/`.
It has passed CHD verification and an exact raw-disk round trip; selection
awaits the cold-desktop qualification.

CHD SHA-256:
`ac2e0702746448da893a623045cee06d359bbe6b8dc0f96668d66d3b8e9ec06e`.

The [File Manager guide](../IRIX-FILEMANAGER.md) gives the original mouse/menu
actions, generic-host setup and per-user storage layout. The
[resource ledger](../../lab/irix-filemanager/resources.json) records the one
added vendor file, its destination, dependencies and permissions. No original
user home or Dumpster contents are imported.

Cross-filesystem moves, collisions, remote filesystems, immutable flags and
concurrent pathname replacement remain outside this cycle. Toolchest's
separate missing `xconfirm`/Legal Notice helper is not part of Dumpster
removal and remains unqualified.

## Cleanup

Completed and interrupted disposable disks, temporary emulator build output
and the redundant 8 GiB round-trip decode are removed at checkpoints.
Logs, PNGs, manifests, original media and qualified/manual image state are
retained. Final guest cleanup and the selected raw-seed replacement are
recorded after qualification.
