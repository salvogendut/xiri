# IRIX import profiles

Maintain separate **6.5.22** and **6.5.30** deliverables. Each version has its
own donor pin, import profile, qualification and CHD. The current qualified
desktop profile is 6.5.22f. The separate original-media
[6.5.30f profile](irix-6.5.30f-v1.json) now produces reproducible payloads;
its core desktop checks now pass on Indy/R5000 with shadow cache mode and the
MIPS IV-aware module. Separate [manual previews](../docs/results/2026-11-15-irix-previews.md)
now package both qualified disk states; broader acceptance remains pending.
The shared module also passes the 6.5.22f regression.
The [native package profiles](../docs/NATIVE-PACKAGE.md) describe
NetBSD components and does not establish compatibility with an untested vendor
release.

`./xiri import` builds a vendor payload without reading a previous NetBSD image,
historical staging directories or the selected manual-image pointer. Run it on
the host with Python 3, `guestfish`/libguestfs and `chdman` installed:

```sh
./xiri import \
  --profile profiles/irix-6.5.22f-v1.json \
  --source .work/donors/irix-6.5.22f-original-media/irix-donor.chd \
  --output .work/imports/irix-6.5.22f-v1 \
  --component acrobat
```

The output directory must be new. Add `--dry-run` to inspect the selection
without opening media. Desktop and fonts are selected by default; Acrobat is
optional. This donor has no GIMP, GNOME or xmahjongg: requesting those components
fails before extraction and explains the missing source. Nothing is downloaded.

The first profile pins **our qualified original-media 6.5.22f donor**, by CHD
and raw SHA256. Another independently installed 6.5.22f disk has different
filesystem bytes and needs its own audited profile. A standalone raw export
with the pinned raw hash also works. Export overlay-backed installations using
[`export-irix-donor.py`](../scripts/export-irix-donor.py) first; the importer
rejects unmerged overlays instead of silently ignoring them.

The profile records source paths, destination exceptions, components and
expected content/link hashes from the [donor comparison](../lab/irix-donor/6.5.22f-comparison.json).
The importer mounts the XFS partition read-only with `ro,norecovery`, checks
required paths, and adds ELF libraries, executable script interpreters and
canonical names for copied executables/libraries. Acrobat's launcher-specific
library directory is explicit. Missing ELF dependencies stop the build.
This closure does not prove every application works or discover every `dlopen`
module, script-invoked helper or application data file.

Outputs are:

- `payload.tar.gz`: vendor files under `/emul/irix` and 22 screen fonts under
  `/usr/local/share/xiri/fonts`. Archive ordering, owners, modes, timestamps
  and gzip headers are normalized for reproducibility.
- `manifest.json`: source/destination types, canonical paths, hashes, modes,
  dependency edges, selected components and omitted catalog links. Catalog
  links are omitted when their targets are not in this payload.
- `extract.log`: CHD extraction diagnostics, when the source is a CHD.

Original symlink text is retained for catalog/resources. Executable/library
paths that resolve through donor symlinks are copied as regular files, with
their canonical names included too. No donor symlink is created on the host;
payload entries beneath another payload file or symlink are rejected.
ELFs and executables use mode 0555, other files 0444, and directories 0755.
The temporary raw disk, downloaded objects and libguestfs cache are removed
on completion or handled failure. Failed builds do not publish a manifest or
payload archive. Keep only qualified payloads and their provenance.

This is the **vendor-payload stage**, not the complete NetBSD installer. Native
kernel/module, Xorg/Newport/Type1, FAM/rpcbind, runtime helpers, configuration,
users and devices are separate prerequisites listed in the profile. Account
tables, PTYs, font indexes and the augmented filetype database are generated
on NetBSD; donor passwords, homes and installed-package databases are not
imported. Do not extract this archive over a live desktop to test it.

The disposable qualification harness replaces the entire vendor tree and
font directory in a copy of a qualified native NetBSD image:

```sh
python3 scripts/probe-irix-import.py \
  --bundle .work/images/xiri-netbsd-desktop-20261114-controls \
  --payload .work/imports/irix-6.5.22f-v1 \
  --output .work/irix-import-check
```

It checks inherited native files, imported file hashes, full-screen xdm,
4Dwm/Toolchest/Icon Catalog/winterm/xclock, a shell's identity and home, the
IRIX shell, File Manager, logout/relogin and native ctwm. It records screenshots
and clean shutdown while preserving the original CHD. A new profile needs
its own results; passing host import checks alone does not qualify a desktop.
The test image's public account credentials are described in the main README.
See the [6.5.22f qualification record](../docs/results/2026-11-14-irix-import.md)
for the completed checks, retained evidence and known helper limitation.

Use native `pax -rz -pe` for extraction in this base. Its `bsdtar` 3.7.7 disk
extraction repeatedly replaced a 16 KiB zero-filled region in `/lib/rld` with
nonzero data. The archive itself, `tar` streaming to stdout, direct copying,
and a `pax` extraction all produced the expected bytes. Keep the full checksum
gate: this observation does not identify a general libarchive or kernel cause.

For 6.5.30, use `--profile profiles/irix-6.5.30f-v1.json` and
`.work/donors/irix-6.5.30f-original-media/irix-donor.chd`, with a separate
output directory. The payload has 1,424 files, 72 directories and 94 links;
its own resources and libraries supply the desktop/fonts. Acrobat, GIMP,
GNOME and xmahjongg are absent and rejected as missing components. Fourteen
ELFs declare MIPS IV, so the R4400 test command above is unsuitable. The
[Indy/R5000 retry](../docs/results/2026-11-14-r5000-6.5.30.md) boots the existing
native kernel and verifies all imported files with IRIS shadow cache mode.
It also qualifies the MIPS IV interpreter module change and core desktop,
shell, File Manager, logout/relogin and native ctwm checks. The
[O2/R10000 trial](../docs/results/2026-11-14-irix-6.5.30.md)
still stops during native SCSI initialization; it is separate platform work.

See the [installation plan](../docs/XIRI-INSTALLATION.md) for the remaining
clean-install stages. Do not relabel or reuse either release's source pin or
treat a reproducible payload as a qualified desktop image.
