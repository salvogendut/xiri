# Boot-loaded IRIX module in the manual desktop image

The module-based CHD is qualified and selected for manual testing. It passes
exact raw-disk round-trip verification, direct disk boot, automatic module
loading at securelevel 1, and the accelerated desktop checks. See the
[cold-boot record](2026-11-03-irix-module-image.json) and
[desktop PNG](images/2026-11-03-irix-module-image.png).
This cycle packages the already qualified module and matching kernel. It
adds no IRIX resources and makes no NetBSD or IRIS source changes.

## Inputs and installation

The [image baseline](../../lab/irix-module/image-baseline.json) selects the
[module build](../../lab/irix-module/build.json), source-equivalent to NetBSD
`xiri` commit `d1ce7a96615`. Its original build record is retained: `c46d4e9a931`
plus the diagnostic receive fix subsequently committed as `d1ce7a96615`.
The module and both kernel files are identical to the previously tested
artifacts. The separate [module cycle](2026-11-03-irix-module.md) records
lifecycle qualification and 415 ABI/regression/control checks.

The source disk is the previous accelerated desktop CHD, SHA256
`1fa5c92ffac3706680e16acd1270df4707928106529cf94084152f9dfac14ab5`.
The image keeps its IRIS `819c682` binaries, corrected Newport Xorg driver,
IRIX 6.5.22m runtime and catalog payload. Its module-aware preparation recipe
is in the [module lab](../../lab/irix-module/README.md#prepare-a-manual-image).

| Installed native file | SHA256 |
| --- | --- |
| `/netbsd` | `830483994877a61efc833c3361ed2a6799df003d7e39033181b070908e3f17cd` |
| `/netbsd.boot` | `567265ee63695a792025ca3c9b8797e674c170c36d6f03f290579d859af9017c` |
| `/stand/sgimips/11.99.9/modules/compat_irix_o32/compat_irix_o32.kmod` | `28908b9311dc342afd28d0aaccb3bd45da3b1b0689de697325778e611c52c70d` |

All three are mode 0444. Preparation derives the module directory from
`kern.module.path`, preserves other `/etc/modules.conf` entries, adds
`compat_irix_o32`, and enables `modules=YES` in `/etc/rc.conf`. The generated
configuration files join the installed-file hash ledger. Boot loading uses
the native modules rc.d service before securelevel rises to 1.
`modstat` must identify the personality as `exec / filesys`.

## Prepared-disk checks

The [preparation record](2026-11-03-irix-module-image-prepare.json) retains
`.work/desktop-usability/ordinary-f4_m0gbc/result.json`, its hash and the
pixel comparison results. This run checked:

- Graphical automatic disk boot, module loading at securelevel 1, and real
  keyboard login on `ttyE0`, with diagnostic access on serial B.
- Two desktop sessions, each with winterm input, user `xiritest`, HOME and
  working directory `/usr/people/xiritest`, plus original IRIX `/bin/sh`
  command execution.
- XAA enabled and the native Render probe passing **8,536 pixels with zero
  mismatches**, in both sessions.
- xmahjongg board 12345: hint/take changes the displayed count from 144 to
  142; undo restores 144. The post-undo and resize/restore client areas match
  exactly over **617,684 pixels**. Initial versus undo differs only in the
  pointer: 93 pixels inside its 10×16 rectangle.
- Toolchest and 4Dwm right-click logout returning to the graphical shell,
  with no remaining UID 1234 clients, Xorg, FAM or owned rpcbind.
- No new RPC binding warnings, installed-file hashes, native controls,
  clean unmount/halt and an unchanged source disk.

The game comparison crops `1006x614+150+270` from each captured PNG using
ImageMagick, then compares 8-bit RGBA bytes. The record includes each full
PNG's hash. These are bounded interaction checks, not a complete game.

## Direct CHD qualification

The disposable run `.work/xiri-image/runs/chd-djhymo36` booted the actual
CHD from disk. It verified the kernel/module and persistent resource hashes,
`exec / filesys` module status, securelevel 1, 1280×1024 Xorg with XAA,
the 8,536-pixel Render probe, winterm HOME, and a fresh xmahjongg launch by
Icon Catalog double-click on the Freeware page. Granite/root/home/Dumpster
resources and FAM execution notifications passed. The launcher removed its
clients/services; the guest halted cleanly and the source CHD was unchanged.

The qualifier checked the matching module build manifest before promotion.
`./xiri run` now selects this bundle. The previous built-in bundle and its
manual NVRAM/overlays are untouched. All owned test emulators were stopped.

After promotion, `./xiri doctor` verified 11 immutable artifacts and host
tools. `./xiri seed --output .work/xiri-image/prepared-seed-20261103-module`
created the reusable raw seed from the verified extraction; `./xiri run
--dry-run` selected the new bundle's pinned launcher. Documentation JSON and
335 local links were checked. The final process check found no IRIS,
iris-ci or Xvfb processes.

## Reproduction and limits

The selected bundle is `.work/images/xiri-netbsd-desktop-20261103-module/`.
Its CHD is **481,180,579 bytes**, representing an 8 GiB disk:

- CHD SHA256: `0d15ff1cb41eb28d5f411cc296f249fb30fa9f356b2f6e84d46f2ef86ba68629`
- Raw SHA256: `d345b4822829d9c5839d0adc3c46c2b784a31f18546e3c9b7e9638fd95400a9b`

After the module lab's preparation command, package its passed run:

```sh
python3 scripts/build-xiri-image.py \
  --seed-run .work/desktop-usability/ordinary-f4_m0gbc \
  --output-directory .work/images/xiri-netbsd-desktop-20261103-module \
  --baseline lab/irix-module/image-baseline.json \
  --kernel .work/netbsd-module-build/tftp/netbsd-XIRI_INDY \
  --iris-bin-dir .work/images/xiri-netbsd-desktop-20261103-newport-xmahjongg/emulator
python3 scripts/probe-xiri-image.py \
  .work/images/xiri-netbsd-desktop-20261103-module \
  --iris-bin-dir .work/images/xiri-netbsd-desktop-20261103-module/emulator \
  --arrange-winterm
```

Use a fresh output directory when repeating packaging. The builder retains
the exact extracted raw round trip for reusable automation seeds. The CHD
probe must boot from disk, verify the module and normal securelevel, and pass
the established desktop checks before the qualifier can promote it.

The ordinary build configuration now selects `XIRI_IRIX_MODULE`;
`./xiri build kernel` builds that kernel in `.work/builds/netbsd`, followed
by `python3 scripts/build-irix-module.py --build .work/builds/netbsd` for
its matching personality and audit. The configuration was checked with
`--dry-run`; this image reuses the qualified artifacts, not a new source build.

Root still launches services; desktop clients and winterm run as xiritest.
The kernel still requires the Xiri fork's `selcommon_kern` and `emul.e_sigmask`
hooks. Service/session separation, normal xdm login, stock-NetBSD delivery,
physical hardware and broader application compatibility remain open.
Winterm is explicitly resized by the interaction probes; its unassisted
startup/font-metric issue remains. The older closed/opened/closed icon-pixel
qualification is inherited; transient launch animation and full Dumpster
operations are not added by this image.

Boot still reports `savecore: (null): kvm_nlist: bad namelist` and `_dumpdev
not in namelist`. The previous built-in image's cold-boot run
`.work/xiri-image/runs/chd-qi6uyd7c` has the same messages. Boot continues;
automatic crash-dump collection is not qualified by this cycle.

IRIS upstream was checked at `28fa516684c54e00e35b258c65e5dcac3a36165c`,
already contained in integration `1aed0df`; no merge was needed. Host tests
pass **23 checks**, including mismatched kernel/module rejection, absent or
built-in personality rejection, normal securelevel, boot configuration and
module-build manifest integrity.
