# Original-media desktop previews

Separate **6.5.30f/R5000** and **6.5.22f/R4400** NetBSD/Xiri previews are ready
for manual testing. Each contains a standalone CHD, a pinned emulator, graphics
NVRAM and a launcher. The existing enriched 6.5.22m manual reference remains
available separately.

## Start the 6.5.30 desktop

Run this from a graphical host terminal:

```sh
/var/home/salvogendut/Dev/xiri/.work/images/xiri-irix-6.5.30f-r5000-20261115/run-iris.sh
```

The launcher selects Indy/IP24, R5000, 256 MB, Newport and **shadow cache mode**,
using the qualified `7d46498b` emulator. NetBSD should boot automatically into
the full 1280×1024 Xorg/xdm login screen. Log in as **xiritest**, password
**xiritest**, for the IRIX desktop. This runs the original 6.5.30 applications
on NetBSD. The launcher starts the standalone IRIS emulator directly.

Use **netbsdtest** / **netbsdtest** for a native ctwm session. To shut down,
log out of the IRIX desktop, log in as netbsdtest, open its terminal and run
`su -` (root's password is empty), then `shutdown -h now`. Wait for the guest
to halt before closing IRIS. Native root login is also available on serial B,
`127.0.0.1:18991`. These are development-image credentials.

The 6.5.22f counterpart has its own launcher:

```sh
/var/home/salvogendut/Dev/xiri/.work/images/xiri-irix-6.5.22f-r4400-20261115/run-iris.sh
```

It selects R4400/default cache with the separately qualified `819c6825`
emulator. Its credentials are the same; serial B uses port 18891.

Each image writes an adjacent `netbsd-xiri.chd.diff.chd`. Keep that overlay
to retain your changes, and use only one running instance of each bundle.
The launchers clear `IRIS_CHD_DIFF_DIR` so the write location stays with the
preview. Source qualification disks remain untouched.

## Coverage and limits

These CHDs merge the cleanly halted disks from the
[dual-release qualification](2026-11-14-r5000-6.5.30.md). That work checks
native boot, the compatibility module, full-screen Xorg, 4Dwm, Toolchest,
Icon Catalog, winterm, xclock, File Manager, shell/HOME, logout/relogin,
native ctwm and clean shutdown. Each preview retains its source result and
probe in `verification/`.

Packaging checks verify input hashes, emulator/NVRAM pins, unchanged source
files, `chdman verify`, TOML paths and launcher shell syntax. **No new boot of
these merged bundles was performed during packaging**; the manifests label
them `packaged-from-qualified-state` rather than claiming a fresh boot pass.

On November 15, the user tried the 6.5.30 preview and reported that it
"looks ok for now." This records positive initial visual feedback on the
packaged desktop. Broader application and session testing remains open;
the packaging manifests retain their original validation scope.

The original-media imports do not include the enriched reference image's
extra freeware, such as GIMP, GNOME, Acrobat or xmahjongg. Prepared user homes
and saved catalog/session state are inherited; an existing catalog entry does
not establish that its application is installed. Broader 6.5.30 application
testing and a clean-target installer remain separate work.

Keep the 6.5.30 preview in **shadow cache mode**. The full-cache import produced
incorrect file contents; its root cause remains unresolved. Native NetBSD O2
boot/driver repairs and Octane board support are separate prerequisites for
those machines.

## Reproduce the packages

From the Xiri checkout, with the retained qualified inputs:

```sh
python3 scripts/package-irix-preview.py \
  --run .work/irix-6.5.30-r5000-desktop \
  --base-bundle .work/images/xiri-netbsd-desktop-20261114-controls \
  --emulator-dir .work/emulators/iris-xiri-20261114-r5k-config \
  --output .work/images/xiri-irix-6.5.30f-r5000-20261115 \
  --port-base 18990

python3 scripts/package-irix-preview.py \
  --run .work/irix-6.5.22-r4400-final \
  --base-bundle .work/images/xiri-netbsd-desktop-20261114-controls \
  --emulator-dir .work/images/xiri-netbsd-desktop-20261114-controls/emulator \
  --output .work/images/xiri-irix-6.5.22f-r4400-20261115 \
  --port-base 18890
```

Output directories must not already exist. The packager merges each overlay
with its parent directly into CHD, without an intermediate 8 GB raw image.
Its manifest records source/output hashes, commands and validation scope.
The [packaging ledger](2026-11-15-irix-previews.json) retains both manifests;
vendor images and binaries stay local.

No emulator was started for packaging. The required upstream test build was
cleaned afterward: 4.28 GiB of newly created cache-file footprint was removed,
with the pre-existing cache and qualified artifacts preserved. This measures
file allocation, not exclusive physical space recovered.
