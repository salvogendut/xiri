# Indy v4 test images and disk-full recovery

These local CHDs start from stock NetBSD 11.0 userland, boot the 11.99.11
kernel with its matching Xiri module and run the v4 native desktop package.
Run either command from the Xiri repository root.

| IRIX userland | Emulated Indy | Imported components | Launch command |
| --- | --- | --- | --- |
| 6.5.22f | R4400, 256 MiB, Newport | Desktop, fonts, Acrobat | `.work/images/xiri-clean-indy-6.5.22f-v4-20261124/run-iris.sh` |
| 6.5.30f | R5000, shadow cache, 256 MiB, Newport | Desktop, fonts | `.work/images/xiri-clean-indy-6.5.30f-v4-20261124/run-iris.sh` |

At xdm, use `xiritest` for 4Dwm or `netbsdtest` for NetBSD ctwm. The test
password is the same as the username. Each launcher starts the pinned
accelerated IRIS binary and keeps manual changes in its own writable
overlay. The November 23 v1 bundles retain their previous overlays.

## Recovery checks

The release-specific CDs are in `.work/installers/indy-11.99.11/space-recovery/`.
They carry the original v4 native archive and the vendor payload for the
specified IRIX release. The revised installer checks each copy and rename
before recording completion and removes incomplete staging files on exit.
The updater also checks copies used to save and restore pre-existing files.
See the [operator's retry procedure](../NATIVE-PACKAGE.md#recover-from-a-full-target-filesystem).

The lab used 1 MiB filesystems on disposable guests. The installer passed
its initial space check, then an actual guest write returned `No space left
on device`. In each case the retry used the same CD and filesystem after
deleting the filler.

| Target write | State observed at failure | Evidence after retry |
| --- | --- | --- |
| Fresh install, font copy under `/usr/local/share/xiri` | The IRIX tree had its receipt. The incomplete font staging directory was removed and the final font directory and completed receipt were absent. | The two trees and completed install had matching receipts. The imported font files matched the vendor checksums, excluding the generated `fonts.dir`. |
| Fresh install, live configuration under `/etc/rc.conf.d` | Both vendor trees had matching receipts. The installer named the failed service setting, discarded the partial file and left the install pending. | All five live service settings existed and the completed receipt matched the original inputs. |
| v3-to-v4 update, packaged FAM example | The new service script and old example were both present. The completed receipt still identified v3 and the update journal identified the pending operation. | The example matched v4, all four receipts agreed and the journal was cleared. Repeating the update reported that v4 was already installed. |

The tests compared contents, inode, owner, group and mode of the local FAM
settings, a private file belonging to `xiritest`, the password database and
the group file across the failures and retries. Physical Indy hardware,
exhaustion of the root or state filesystem, and sudden power loss during a
write remain separate tests. [Reproduction commands](../../lab/native-package/README.md#disk-full-recovery-and-fresh-v4-images)

## Manual image checks

The images came from separate clean installations. Each install resumed
after interruption, preserved an administrator's conflicting file and
passed repeat installation. After shutdown, `chdman verify` checked each
image and its data SHA-1 matched the complete 8 GiB raw disk. Each packaged
CHD then cold-booted on a private overlay with the graphical PROM and no
installer CD attached.

The desktop check compared the guest's release and package receipt with
the bundle manifest, logged in as `xiritest`, verified 1280×1024 and found
Toolchest, Icon Catalog, winterm and xclock. The original IRIX shell ran
as `xiritest`, and the session recorded `/usr/people/xiritest` as both its
home and working directory. The native
account opened ctwm and UXTerm. Both sessions returned to xdm before the
guest halted. [6.5.22f screenshot](2026-11-24-indy-v4-recovery-6.5.22f.png)
· [6.5.30f screenshot](2026-11-24-indy-v4-recovery-6.5.30f.png)

The [qualification record](2026-11-24-indy-v4-recovery.json) contains
the CD and CHD hashes, per-release receipts and checks. The compact
`qualification.tar.gz` alongside the CDs contains guest diagnostics,
both desktop screenshots per release and host test logs. The host suite
passed 94 tests. The emulator shipped in these bundles is the version used
for the November 23 clean images. The [IRIS fork record](../FORKS.md#iris-upstream-updates)
covers the separate upstream merge.
