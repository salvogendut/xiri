# Offline Indy system upgrade and rollback

The recent native XiriBSD installer ISOs contain the same Indy kernel,
PROM-loadable kernel, IRIX compatibility module and desktop runtime.
To exercise a real binary change, the test uses the archived audio-v7
Indy builds in the current runtime packaging layout. The destination is the
native payload from the November 27 operator-permissions installer.
Both generations use NetBSD 11.99.11. This fixture is for regression testing.
The procedure for an actual update starts with two trusted installer ISOs.
[Operator instructions](../XIRIPREP.md#upgrade-or-roll-back-the-indy-kernel-module-and-desktop-runtime)

| Native component | Earlier SHA-256 prefix | Current SHA-256 prefix |
| --- | --- | --- |
| Kernel, `/netbsd` | `55e77aaacba0` | `d650c7107a30` |
| PROM image, `/netbsd.boot` | `95cca60334ff` | `3ebca6498070` |
| `compat_irix_o32.kmod` | `55c4f2eefd74` | `6750998ce562` |
| Cached desktop runtime | `8b9c50189ef3` | `6b4af62fd703` |

The update CD includes both generations of 13 native files. It operates
with the IRIX donor detached. It verifies the four receipts for the
installed desktop, checks the original files before writing, and installs
each replacement by rename. A persistent journal records the update
direction and media identity. Its lock is released by the NetBSD kernel
when the updater exits. The operator can resume after an interruption
from an independent maintenance disk even if the target has mismatched
boot files. Back up the complete stopped target before starting.

## Results

Both the R4400 with IRIX 6.5.22f and the R5000 with IRIX 6.5.30f passed.
Each rejected an update of the running system and a competing update. The
test then killed the updater after it installed `/netbsd` and verified
that the old module was still on disk. A fresh maintenance boot rejected
the reverse direction, resumed the original operation, and recognised a
second invocation as already complete. The same CD rolled back the
completed update. This exercises process interruption and a clean reboot
of the maintenance disk. Power loss during an FFS write remains untested.

Before the update, after recovery, and after rollback, both Indys booted
their expected kernel, loaded the matching module, and accepted both xdm
logins. 4Dwm restored the blue 6.5.22f and green 6.5.30f backdrops, Icon
Catalog opened, and winterm acquired the user's terminal. The native
account got ctwm. Checksums covered the native accounts, groups, xdm and
service configuration, session selection, a user document and the imported
4Dwm binary. Both guests powered off. Two fixture builds returned
identical content manifests. [Per-release records and hashes](2026-11-27-xiriprep-system-update.json) ·
[6.5.22f desktop](2026-11-27-xiriprep-system-update-6.5.22f.png) ·
[6.5.30f desktop](2026-11-27-xiriprep-system-update-6.5.30f.png)

## Reproduction

On the workstation, create the test CD in a scratch directory and run
the checker separately against each qualified `xiriprep` desktop bundle.
Each run makes its own system and maintenance disks and writable overlays.

```sh
python3 lab/native-iso/make-upgrade-replay.py \
    .work/images/xiribsd-indy-operator-11.99.11.iso \
    .work/installers/indy-11.99.11/audio-v7/xiri-6.5.22f.iso \
    /tmp/indy-system-test.iso
for release in 6.5.22f 6.5.30f; do
    python3 lab/native-iso/check-system-update.py \
        --bundle ".work/images/xiribsd-indy-${release}-xiriprep-20261127" \
        --media /tmp/indy-system-test.iso \
        --emulator .work/emulators/iris-xiri-20261122/accelerated \
        --output ".work/offline-update-test-${release}" || break
done
```
