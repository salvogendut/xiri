# Original-media IRIX donor CHD

The installed Prismatic Indy disk is now exported as a verified **IRIX 6.5.22f
donor CHD**. A disposable CHD copy passed a cold boot, serial root login,
graphical root login and 4Dwm startup. The original IRIX shutdown command
powered the machine off and IRIS exited normally. This qualifies a source
installation; Xiri's tested runtime remains **6.5.22m**.

The [result ledger](2026-11-14-irix-donor.json),
[donor manifest](../../lab/irix-donor/6.5.22f.json) and
[media audit](2026-11-14-irix-donor-audit.json) record the inputs and checks.

## Image and reproduction

The local bundle is `.work/donors/irix-6.5.22f-original-media/`:

| Artifact | Value |
| --- | --- |
| Image | `irix-donor.chd` |
| Compressed size | 530,002,747 bytes, approximately 505.4 MiB |
| Logical disk size | 4,294,967,296 bytes, 4 GiB |
| CHD SHA256 | `b4fff76ffa0ca00c0a90da1c94a3eb41f5f6ba4cb13c0af258b4acca4ad95c41` |
| Raw SHA256 | `fc70f353f53244eaa2707609b348e4a2b22aae3de6ce41398bdd8d6c3f4bda56` |
| Source machine | Indy R4400, 128 MB, 24-bit Newport |
| Boot emulator | Retained IRIS `xiri` build `36858ff4e8694756502fa1e84b1190e6997d6e0d`, with JIT enabled |

Run the donor from a graphical host session with:

```sh
./.work/donors/irix-6.5.22f-original-media/run-iris.sh
```

Choose **1, Start System** at the PROM menu and log in as **root** with an empty
password. This launches original IRIX. The existing NetBSD/Xiri manual-image
pointer is unchanged. The bundle's README records the private NVRAM, overlay and
port settings. Shut down inside IRIX with `shutdown -p -g0 -y` before closing it.

The bundle retains `desktop.png` and `login-golden.png`, the export logs and
compact boot evidence. Original vendor bytes remain outside Git; metadata and
the source-to-reference comparison are tracked here.

To reproduce the export on the Linux host, using a new output directory:

```sh
python3 scripts/export-irix-donor.py \
  --source "$HOME/Downloads/IRIX media/Installed/Indy-R4400-6.5.22/irix6522.img" \
  --output-directory .work/donors/reproduced-6.5.22f --keep-raw

python3 scripts/compare-irix-donor.py \
  --raw .work/donors/reproduced-6.5.22f/disk.raw \
  --output-directory .work/donors/reproduced-6.5.22f/comparison
```

The exporter requires Python 3.11 or later and `chdman`; comparison also requires
working libguestfs/`guestfish`. The original Prismatic guest must be stopped.
The exporter holds its existing disk lease, reads the base, overlay and dirty
map without modifying them, includes appended dirty sectors, rejects incomplete
or out-of-range metadata, and verifies input hashes and file identities before
and after export. It will not replace an existing output file or directory.

`chdman` 0.288 created the image using zlib, 16 KiB hunks, 512-byte sectors and
two compression workers. Verification and extraction reproduced the raw disk
size and SHA256 exactly. The extraction used for that round trip is removed
automatically. `--keep-raw` retains the merged disk only for subsequent read-only
checks; remove it and the comparison appliance caches after preserving results.

## Boot validation

The final test used the standalone IRIS and CI client from
`.work/upstream-qualified/`, whose hashes and build revision are retained in
the donor manifest. A copied CHD and copied NVRAM isolated all guest writes.
Newport remained enabled throughout; the test captured its actual framebuffer.

```sh
python3 scripts/probe-irix-donor.py \
  --chd .work/donors/irix-6.5.22f-original-media/irix-donor.chd \
  --nvram .work/donors/irix-6.5.22f-original-media/nvram.bin \
  --iris .work/upstream-qualified/iris \
  --ci .work/upstream-qualified/iris-ci \
  --login-golden .work/donors/irix-6.5.22f-original-media/login-golden.png \
  --output-directory .work/donors/reproduced-6.5.22f/boot \
  --start-system-after 15 --timeout 1200
```

The `--start-system-after` option is for this saved NVRAM, which stops at the
PROM menu. The image-specific golden verifies that the graphical login window
has appeared before the harness types into it.

Observed results:

- `uname -R` reports `6.5 6.5.22f`; `hinv` reports R4400, 128 MB and Indy 24-bit
  graphics, with the disk at SCSI ID 1.
- The filesystem mounts as XFS. Read-only inventory used `ro,norecovery` and
  left the raw disk hash unchanged.
- The graphical login matches the inspected greeter. Original Xsgi, 4Dwm and
  Toolchest run; the desktop PNG shows Icon Catalog, xclock and desktop icons.
- `sync; shutdown -p -g0 -y` produces the guest shutdown announcement, then
  `Machine: soft power-off` in the emulator log and exit status 0. No host quit
  or forced termination was needed in the passing run.
- The source CHD and original NVRAM hashes remain unchanged.

An initial interpreter-only run exceeded its login timeout while X started.
The first JIT run reached both login interfaces but sent graphical keystrokes
before the greeter mapped. Both owned instances were stopped; the final harness
waits for the visible greeter. These were qualification-harness limitations,
not evidence of a failed disk export. The initial shutdown classifier expected
serial power-off text; it now also recognizes the recorded clean soft power-off
and rejects an ordinary exit, missing shutdown command or forced termination.

## Resource comparison

The [complete inventory](../../lab/irix-donor/6.5.22f-comparison.json) checks
3,407 distinct paths against the existing desktop, bitmap, backdrop, terminal,
session, File Manager, document, Overview, GIMP, GNOME and Acrobat ledgers.

| Observation | Paths |
| --- | ---: |
| Same file bytes | 1,351 |
| Different file bytes | 135 |
| Same directory/type | 91 |
| Same symlink type and target | 124 |
| Absent from this installation | 1,706 |

All **42 selected core paths** are present: 20 match byte-for-byte and 22 have
different hashes. 4Dwm, Icon Catalog, File Manager, Overview, the vendor winterm
script, shells and runtime loaders match. The changed core files include
Toolchest, xclock, xwsh and several libraries.

The [ELF section comparison](../../lab/irix-donor/6.5.22f-sections.json) confirms
identical `.text` sections and file sizes for all 22 changed core ELFs, using
old local files whose full hashes match the tracked reference. Differences are
in data, linker/relocation and related sections, consistent with IRIX's
installation-time requickstarting. This does not establish Xiri runtime
compatibility for their new mapped addresses or data; preserve separate pins
and test the new payload before changing the reference.

All 55 bitmap-ledger paths and the granite backdrop are present and match
their recorded types, link targets or bytes. Acrobat's 86 resource paths are
also present, with six changed file hashes. GIMP lacks 1,216 of its 1,217
resource-ledger paths; the one match is a shared original core library. All 53
GNOME resource/preference paths and xmahjongg are absent. Other missing paths
include developer tools, application defaults and catalog entries from software
added to the old donor. Optional component selection must reflect actual source
contents rather than assume that every old catalog target is installed.

## Next work

Use this donor to build the versioned import profile and qualify its core desktop
on a clean compatible NetBSD target. Keep freeware and other optional payloads
separate, retain the tested 6.5.22m runtime until that passes, and continue the
independent 6.5.30 process described in the
[installation plan](../XIRI-INSTALLATION.md#separate-irix-6530-workflow).

The [result ledger](2026-11-14-irix-donor.json) records final scratch-file cleanup
and owned-process checks. IRIS upstream `49210388` remains included in `xiri`
at `7c4552a6`; this cycle needed no fork changes or rebuild.
