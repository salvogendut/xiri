# Reusable NetBSD/IRIX desktop CHD

The prepared CHD packages the halted imported-payload baseline, its
qualified signal kernel and persistent desktop helpers. Routine work can
clone this image rather than extracting the IRIX source disk again.
[Manual instructions](../XIRI-IMAGE.md) cover the supplied IRIS configuration,
serial login, desktop launch, overlay retention and clean shutdown.

The local image is
`.work/images/xiri-netbsd-desktop-20261101/netbsd-xiri.chd`:

- Logical disk: 8,589,934,592 bytes (8 GiB), 512-byte sectors.
- CHD: 479,911,028 bytes, zlib compression, 16,384-byte hunks.
- CHD SHA-256: `ddbbc6360afd5aa3712bd34258f0daaad4573292fae63d915157d3db0027f7b3`.
- Source/extracted raw SHA-256: `e0d7bb159dff7faf0c0f29f17a5c5cf6fff63242164e04a7576cebf3b72d5954`.
- Source seed: `ordinary-w6lzsg5x`; kernel source: NetBSD `xiri`
  `4680cd61b625a5eaa393a0deaea73f4b9f7ed7bc`.

`chdman` 0.289 verified the archive, then extracted all 8 GiB. Both size and
SHA-256 equal the stopped source disk; the source was unchanged. The first
cold boot, `chd-00s61v1l`, reached native multiuser through the disk's volume
header and `/netbsd.boot`, with no TFTP boot. Native Xorg/Newport initialized
at 1024×768×24. Its fixed early capture contained only the root background;
that run is retained as a diagnostic, not a desktop rendering pass.

The revised probe, `chd-y0zzl4os`, waits for xmahjongg to become viewable
instead of sleeping for a fixed interval. It raises/focuses the game and
records the window tree and two native XWD captures. The tree contains
4Dwm decorations, winterm, xmahjongg and Icon Catalog. The visible terminal
has a native `xiri$` prompt. Window placement overlaps on the 1024×768
screen; game interaction and catalog actions are not established by these
captures. See the [machine-readable qualification](2026-11-02-xiri-image.json)
and [PNG](images/2026-11-02-xiri-image.png).

The cold-boot probe checks both installed kernel hashes, additional ledger
resources including all 22 persistent Screen fonts, and the native ABI
control before and after the desktop. It requests termination through the
manual launcher, checks reserved-UID descendant cleanup, halts NetBSD and
confirms the base CHD remained unchanged. The qualified boot NVRAM is
promoted into the bundle; the original build manifest/NVRAM are preserved
under `verification/`.

The [copy ledger](../../lab/irix-installed-desktop/copy-ledger.json) contains
1,990 source/destination entries. The [permission manifest](../../lab/irix-installed-desktop/permissions.json)
records the ELF 0555 adjustment required by native VEXEC checks. Native
helpers, PTY setup, font indexing and home ownership are documented
separately in [IRIX-IMPORT.md](../IRIX-IMPORT.md).

Icon Catalog's populated system files remain installed, but the imported
payload still displays Blank. Original `inst` installation, per-application
data closure beyond xmahjongg, full desktop services, personal state across
later logins and general GUI interaction remain open. SGI's catalog and
customization references are recorded in the import guide for the next
focused discovery trace. No IRIS or kernel source changes were needed to
create the image.

The unchanged winterm script reports that its `gettxt` child cannot execute;
it nevertheless starts xwsh and reaches the native shell handoff. Preserve
that diagnostic as a separate utility compatibility follow-up. Xorg also
logs nonfatal keysym warnings. Neither issue is hidden by the qualification.
