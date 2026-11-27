# Install XiriBSD from independently prepared IRIX donors

Xiri’s reproducible releases use the project’s own 6.5.22f and 6.5.30f
original-media installs. The SuperIRIX MAME Indy tests the user-facing
installer against a disk created outside the project. Two other installations
test whether a donor built for a different SGI machine can supply an Indy.
[Installation guide](../INSTALL-INDY-PRISMATIC.md) · [On-target commands](../XIRIPREP.md)

## Donor identity

| Installed IRIX donor | XiriBSD target | Entries in its desktop plan | Differences from the reference plan before adaptation |
| --- | --- | ---: | --- |
| SuperIRIX MAME Indy, 6.5.22m | Indy R4400 | 1,668 | 167 files had different contents. All original paths existed. |
| Indigo2 IP28, 6.5.22f | Indy R4400 | 1,668 | 159 changed files and seven absent paths |
| Octane IP30, 6.5.30f | Indy R5000 | 1,600 | 159 changed files and 13 absent paths |

The community Indy and the project’s original 6.5.22f donor share identical
`/sbin/sh` and 4Dwm binaries. Their Toolchest binaries differ. The updated
`xiriprep --check` compares all three fingerprints with each installed
plan, reports the selected plan and checks the existing installation receipt.
The full import verifies every planned resource in a private staging tree.
Other installations with the same desktop resources can match even when
their whole-disk hashes differ. The three donor hashes below identify the
specific inputs tested.

| Installed donor CHD | SHA256 |
| --- | --- |
| `irix65_chd/irix65.chd` from SuperIRIX | `f0615ce71308026c1366c289be8de8a640a0ca83ca7b808139acb71f3482a659` |
| `irix-6.5.22f-ip28.chd`, sealed before subsequent emulator writes | `cb5f8b5bd3417acf53092e1f25fb5d1e73d932bf53189344a7b613fc70071414` |
| `irix-donor.chd`, exported from the stopped Octane including its overlay | `9e0c6346c43eb65d077309d9878f2528c50e5a907ae507f52cc2bfacfafbbef0` |

The local Octane export and its readback ledger are under
`.work/donors/irix-6.5.30f-octane-20261127/`. The sealed Indigo2 disk is
under `.work/native/indigo2-ip28-6.5.22f-20261122/`.

The community disk was inspected read-only. Its catalog contains 21 Freeware
entries, including GIMP and xmahjongg. The separate virtual disk accompanying
it holds four Freeware discs. The base donor import selects desktop
components; importing every application or a donor user’s home is outside
this test. [Local archive comparison](../IRIX-RESOURCES.md#provenance-of-the-downloads-images) ·
[Uploader’s notes](https://forums.irixnet.org/thread-4081.html)

On the R4400, the Indigo2 plan selects the donor’s own MIPS III libc at
both loader aliases, plus its MIPS III math, floating-point and digital-media
libraries. The default Indigo2 libc needs MIPS IV. Both alternate feature
plans use their donor’s IMPACT library paths. The Octane plan omits absent
O2-specific flat-panel and video resources. Each plan records its imports
and exact bytes. [Plans and deltas](../../packaging/xiriprep/plans)

## Native media

| Local file under `.work/images/` | Bytes | SHA256 |
| --- | ---: | --- |
| `xiribsd-indy-donor-profiles-11.99.11.iso` | 357103616 | `a2b6fc5f479e81bd4befa39fbf2aad54cd7442e3f2ef142ecac63dde2723ab06` |
| `xiriprep-indy-donor-profiles-tools.iso` | 2705408 | `4aee73a3aea378207b2d6bd39654d5d566af0afffac74ec7c552d16c8b4d0296` |

The build reused the verified NetBSD 11.99.11 sets, Xorg, kernel, module
and native donor reader. It regenerated the profiles and corresponding
source archive, then checked every ISO file and read back the SGI boot
loaders. All SGI executable and font data come from the user’s donor during
installation. [Recipe and input hashes](../../lab/native-iso/indy-owner-donors-20261127.json)

## Fresh installations

The externally supplied 6.5.22m CHD was presented as a file on a read-only
FFS volume at SCSI ID 2. An emulated Indy R4400 installed all 15 XiriBSD
sets from the native ISO, identified the correct maintenance stream and
imported 1,668 entries. A deliberately incorrect digest stopped the first
attempt before publication. Restoring it allowed the import to finish.
Repeating the command preserved the user's X resources and previous session
backup.

With the donor detached, `xiritest` logged into 4Dwm through xdm at
1280×1024. Icon Catalog, Toolchest, winterm and xclock appeared. The Qix
demo and idle saver animated, Space woke the desktop, and the idle setting
survived logout and login. A separate unselected account logged into native
ctwm. The guest powered off. [Community Indy screenshot](2026-11-27-owner-donors-22m-desktop.png) ·
[Community Indy test record](2026-11-27-owner-donors-22m.json)

The manual SuperIRIX test CHD was built from another blank 6 GiB Indy disk
with the same native ISO and donor. The imported desktop receipt matched the
first installation. After shutdown, `chdman verify` passed and the CHD data
SHA1 matched the raw disk. The compressed disk is 469,655,698 bytes and its
SHA256 is `8edb03450e1cea12bc0538a57ed62494e56aaf49245c46d81411f4e68e499549`.
With the donor detached, the CHD booted in IRIS to 1280×1024 4Dwm for
`xiritest` and ctwm for `native`. The graphical Prismatic launcher reached
the XiriBSD xdm greeter from a separate overlay. The local bundle includes
the desktop and greeter screenshots and the per-image test record.
The shutdown check on that build ran from the root console. The published
CHD's `xiritest` account needs to be added to `operator` for menu shutdown.
[Repair the account on this disk](../XIRIPREP.md#allow-desktop-shutdown-for-an-existing-account) ·
[Launch the SuperIRIX test disk](../XIRI-IMAGE.md#superirix-indy-6522m)

The two feature-stream tests used the same native ISO with separate blank
disks. Each donor was read from a data CD at SCSI ID 6. Both installed
desktops passed the 4Dwm, winterm, saved Qix and native ctwm checks.
With the release-matched installer supplement and May 2004 Freeware disc 4,
SGI `inst` installed xmahjongg. Double-clicking its Freeware icon started
the 1006×614 game as the ordinary desktop user. Removing it cleared the
executable, catalog link and game package history. The shared Freeware index
remained installed. The desktop filetype table, user preferences, session
selection and shared installation receipt matched their pre-game hashes.

| Donor | Source of the desktop | Installed optional application | Record |
| --- | --- | --- | --- |
| 6.5.22f | [Indigo2 donor on Indy R4400](2026-11-27-owner-donors-22f-desktop.png) | [xmahjongg](2026-11-27-owner-donors-22f-game.png) | [6.5.22f results](2026-11-27-owner-donors-22f.json) |
| 6.5.30f | [Octane donor on Indy R5000](2026-11-27-owner-donors-30f-desktop.png) | [xmahjongg](2026-11-27-owner-donors-30f-game.png) | [6.5.30f results](2026-11-27-owner-donors-30f.json) |

These are emulator results. The maintenance-stream test covers the desktop
from the third-party disk. The optional software transactions used the two
feature-stream releases.

## Updating existing installations

### Shutdown permissions

Private overlays of the published 6.5.22f, SuperIRIX 6.5.22m and 6.5.30f
Indys reproduced the missing shutdown permission for `xiritest`. On each,
the updated tools created a new desktop account interactively and added it
to NetBSD's `operator` group. Preparing the existing `xiritest` first kept
its permissions, then `--allow-shutdown` granted access. A repeat run kept
the same group-file checksum. A separate supplementary group survived,
the IRIX group map included both operators and the native ctwm user still
lacked shutdown permission. The `--check` path left the group file intact.

After a fresh xdm login as `xiritest`, the 4Dwm desktop menu opened its
confirmation dialog. Clicking **Shut Down** produced IRIS's
`Machine: soft power-off` and exit status zero on all three releases.
The graphical shutdown did not print the root console's shutdown-hook
message on the test serial port.

The new native ISO booted to sysinst on a blank R4400 Indy. Its kernel
set contains the same preparation tools archive contents used in the
three guest tests. The workstation suite passed all 106 tests.

| Local file under `.work/images/` | SHA256 |
| --- | --- |
| `xiribsd-indy-operator-11.99.11.iso` | `3d889b2b8d58f1b95936b063ca162264ebc998961eddcfc268ffde5330c0e990` |
| `xiriprep-indy-operator-tools.iso` | `b1d3474903bf0de9fdd1fddab5e3f49509ca00f28cad6d55a8b537b4db009f92` |

### Donor profile update

On private copies of the two previously published reference Indy CHDs, the
new tools CD recognized the matching donor and refused to prepare a different
release over the existing desktop. On the 6.5.22f system it correctly
identified the community disk as 6.5.22m before reporting the mismatch.
A custom X resource was present in the running session after the upgrade and
again after rollback. The user's session selection, native configuration
and shared receipt kept their recorded hashes.

Rollback restored all ten files from the previous tools CD and removed the
three additional plans after checking their hashes. This test updated the
native preparation tools. Kernel, module and runtime upgrades have their own
recovery procedures. [Tools update and rollback](../XIRIPREP.md#revert-the-tools-update)

## Reproduce the community check

Supply a standalone copy of the original CHD. The test builds a temporary
FFS disk containing that CHD and installs XiriBSD onto a separate blank disk.
The current test uses the installer with operator support. To reproduce the
original run with the donor-profiles ISO, use the test at Xiri commit `cbf6b91`.

```sh
python3 lab/native-iso/check-desktop.py \
  --iso .work/images/xiribsd-indy-operator-11.99.11.iso \
  --release 6.5.22m --donor "$HOME/Downloads/irix65_chd/irix65.chd" \
  --donor-sha256 f0615ce71308026c1366c289be8de8a640a0ca83ca7b808139acb71f3482a659 \
  --makefs .work/netbsd-irix-build/tools/bin/nbmakefs \
  --emulator .work/emulators/iris-xiri-20261122/accelerated \
  --serial-prom .work/indy-netbsd/nvram.bin --output .work/community-donor-check
```
