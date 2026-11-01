# Supplied SGI Freeware CD sets

The supplied `irix-sgi-freeware-cdroms.chd` contains four extracted CD sets
from **SGI Freeware, May 2004**, identified by its `inst.README`. It is an
uncompressed version 5 hard-disk CHD, not a single optical-disc image. The
94 GiB logical disk contains the sets under `/cds/cd-1` through `/cds/cd-4`.

| Directory | Package inventory records |
| --- | ---: |
| `/cds/cd-1/dist` | 129 |
| `/cds/cd-2/dist` | 79 |
| `/cds/cd-3/dist` | 140 |
| `/cds/cd-4/dist` | 144 |
| Total | 492 |

There are **489 distinct package names**; `fw_common` occurs on all four CDs.
Each set has `dist` and `relnotes` directories. Distributions include product
descriptors, `.idb` file inventories and software/manual/source payloads, with
additional ABI payloads for some packages. This counts media records, not
applications demonstrated to run on Xiri.

The [validated inventory](2026-11-01-irix-freeware.json) binds 990 privately
extracted metadata files, package names, hashes and the CD memberships. Of
these, four files read entirely as zero: the descriptors and `.idb` inventories
for `fw_ncurses` and `fw_nedit` on CD3. Their usability is unresolved; other
payloads have not undergone a full integrity audit.

## Installation and catalog evidence

The selected first application is **xmahjongg 3.6.1**, on CD4. Its `.idb`
contains install/removal operations invoking original `iconcatalogedit` with
the system page **Freeware**, two `.fti` icon files and a `.ftr` type rule.
A separate operation rebuilds the file-type database through its Makefile.
Twenty distinct package inventories contain `iconcatalogedit` references.

The installed IRIX image confirms that catalog pages live beneath
`/usr/lib/desktop/iconcatalog/pages/C` for the C locale. Its Freeware page
contains links to programs in `/usr/freeware`; Applications also contains
links to both native IRIX and freeware programs. Package hooks and these
installed links support using the original registration mechanism. They do
not yet prove catalog discovery or launch on NetBSD.

The [software plan](../IRIX-SOFTWARE.md) now targets original `inst` and
Software Manager, followed by catalog launch, persistence and removal. The
original installer family has a complete static 37-path n32 closure in the
[installer manifest](../../lab/irix-installer/manifest.json). Static resolution
does not qualify runtime helper programs, services or delayed library loads.

## Preservation and reproduction

The user-supplied CHD SHA-256 is
`6da9a2efe74eccedf4ba1a75e21849099e650460b75f14bac635f8409d19edb8`.
An isolated copy matches it. The retained IRIS `chd-extract` reads that copy
into a sparse 100,663,296,000-byte raw file, occupying about 8 GiB. SHA-256
computed over the conversion stream is
`4854f25ccca842e36ad2626f750a3a5f9cb57db4d0e6b9f331b48c91515feb18`.
Its XFS partition starts at byte136314880 and is inspected through libguestfs
with `--ro` and `ro,norecovery`.

The original download, its Prismatic diff/overlay files and the running user's
environment are unchanged. The overlay contents and secondary XFS partition
are outside this inventory. Images, installed binaries and distribution
payloads remain under ignored `.work`; only metadata and findings are public.

The supplied `irix65_chd/irix65.chd` matches the existing installed reference
exactly: SHA-256
`f0615ce71308026c1366c289be8de8a640a0ca83ca7b808139acb71f3482a659`.
The existing read-only raw conversion is reused for installer/home inspection.
Its `/usr/people` directory and `/etc/stdcshrc`, `/etc/stdlogin`,
`/etc/stdprofile` templates inform the native-account layout; personal account
settings and the installed package-history database are not imported.

The local intake scripts and extraction log are hashed in the report. Recheck
the retained metadata and regenerate its summary with:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/summarize-irix-freeware.py
```
