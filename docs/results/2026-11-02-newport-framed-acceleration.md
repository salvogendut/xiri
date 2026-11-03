# Framed Newport console and XAA colors

The requested `feature/newport-framed-console` kernel boots with its framed
console. The accelerated color failure was in IRIS: it treated physical
COLORVRAM and WRMASK bits as packed BGR pixels. IRIS `xiri` commit
`819c6825504d40ad9f9aa00554249affd2da9446` fixes that interpretation for RGB24.
The installed NetBSD Xorg Newport driver needs no color-encoding patch.

## Evidence and scope

The additional `../sgi` documentation catalog led to the SGI RB2 specification.
RB2 section 4.2 and table 4.4, together with REX3 section 3.9/table 22,
describe fast-clear bypass, direct plane masks and the physical RGB24 bit
order. NetBSD's `NewportColor2Planes24` follows that layout. IRIS now decodes
those values into its framebuffer representation while preserving raw
register readback. COLORI and image-upload formats retain their existing
meaning. See the [source manifest](../../lab/newport-accel/hardware-sources.json)
and [Newport notes](../NEWPORT.md). This is emulator validation; physical
Indy hardware and other pixel-depth/plane formats remain separate work.

| Check | Before correction | Corrected IRIS |
| --- | --- | --- |
| Solid fills and screen copies | Eight sampled colors wrong; red `0xfe` became `0x092492` | Exact expected colors |
| Image uploads | Four sampled colors correct | Still correct |
| Channel masks | Independent renderer regression fails | Correct fill/copy masks |
| Native XGetImage and composed frame | Accelerated mismatch | All 20 expanded samples match in XAA and software runs |
| Keyboard, three mouse buttons, xterm command | Pass | Pass |

The corrected accelerated and software PNG files are byte-for-byte identical:
SHA256 `0abbbddca327dabeff31e12c92bbcbd87b3ce9eecc11f93c26d4f214210be8a2`.
Xorg's actual server log confirms XAA enabled in one run and disabled in the
other. Both disposable disks halted cleanly and the source seed stayed
unchanged. Run times include boot, compilation and input checks; they are
not performance benchmarks.

- [Original accelerated failure](2026-11-02-newport-frame-accelerated.json)
  and [PNG](images/2026-11-02-newport-frame-accelerated.png).
- [Corrected accelerated run](2026-11-02-newport-frame-accelerated-fixed.json)
  and [PNG](images/2026-11-02-newport-frame-accelerated-fixed.png).
- [Software control](2026-11-02-newport-frame-software-fixed.json)
  and [PNG](images/2026-11-02-newport-frame-software-fixed.png).
- [Renderer regressions](2026-11-02-newport-plane-tests.json): both new tests
  fail before the fix; 183 Newport tests pass afterward, with 5 benchmarks
  ignored. Each renderer checks 1,044 draws against an independent table of
  all 24 bits, colors, masks and expected destination pixels. Block/span,
  line, XOR and copy paths are covered, with register and auxiliary-plane
  preservation checks. Compiled dispatch is explicitly asserted.

## Desktop follow-up

The corrected emulator fixes desktop colors, but the full XAA desktop still
corrupts xmahjongg tile/control artwork. A same-kernel, same-emulator software
control renders that artwork correctly. Disabling accelerated screen copies
alone does not resolve it. Separate image-write and color-expansion disables
also fail to fix it and introduce missing backgrounds/text. Both selective
controls complete with clean shutdown. See the [control record](2026-11-02-newport-desktop-controls.json),
[XAA screenshot](images/2026-11-02-newport-desktop-full-xaa.png) and
[software screenshot](images/2026-11-02-newport-desktop-software.png).
The software and no-screen-copy control harnesses captured the intended
screenshots and server logs but reported cleanup-command errors; both then
halted cleanly. They are diagnostic observations, not passing qualifications.

An [expanded native probe](2026-11-02-newport-image-paths-accelerated.json)
passes nonuniform image upload, shaped pixmap copy,
monochrome expansion, explicitly little-endian image data and eight directions
of overlapping screen copy. A follow-up adds narrow subrectangles, shifted clip origins and GXor copies:
1,404,075 pixel comparisons across 75 passes, in addition to the twenty
composed color samples. The [software control](2026-11-02-newport-image-paths-software.json)
passes the same workload and its [screenshot](images/2026-11-02-newport-image-paths.png)
is byte-for-byte identical to the accelerated one. Both halt cleanly.
The passing native workload does not
yet reproduce the full application's artwork failure. A reusable accelerated
image must retain this distinction until the remaining path is isolated.

## Kernel and console

The kernel was built from the feature branch's then-uncommitted snapshot
based on `314c8c32e84e41a0eda05366d3004bb10a68c86e`. Its owner subsequently
committed the same twelve changed files as
`a536d8c4da20c1eef2c7ff209ba51223dde00b61`. Their contents match the build
snapshot byte-for-byte; the commit's parent matches the snapshot's base.
The [equivalence record](../../lab/newport-accel/committed-source-equivalence.json)
retains that proof without rewriting the original build provenance.
The checkout is now `../NetBSD-xiri`, with the old directory name retained
as a symlink.

`XIRI_NEWPORT_FRAME_20261102` enables COMPAT_IRIX_O32 and NEWPORT_FRAME on
GENERIC64_IP2x, using the existing mips64eb toolchain. NEWPORT_DECOR is implied.
The [baseline](../../lab/newport-accel/corrected-baseline.json) records all
kernel, emulator and runtime hashes. The boot kernel SHA256 is
`58888643294a2794770d8b6a7b4dcfb89b77449511160d91100130f6d774fd88`.

The first completed graphical trial verified root console login, an xiritest
desktop with HOME and cwd `/usr/people/xiritest`, native shell input, both
logout routes and service cleanup. Every one of the 839,680 pixels outside
the console text rectangle matched the source frame before Xorg and after
logout. See [the console result](2026-11-02-newport-frame-console.json) and
[PNG](images/2026-11-02-newport-framed-console.png). That trial still used the
old emulator and is explicitly not a color qualification. The
[corrected emulator comparison](2026-11-02-newport-frame-console-fixed.json)
also has zero mismatches across all 839,680 outside pixels before and after X.

Winterm's intermittent initial vertical-font/sizing problem remains open.
The diagnostic probes record the original geometry and explicitly resize
it before typing; they do not change the installed launcher or claim to
fix unassisted startup sizing.

## Reproduction and image

[The lab instructions](../../lab/newport-accel/README.md) retain the original
and corrected emulator baselines, build snapshot and commands. The established
`.work/images/xiri-netbsd-desktop-20261102-behavior/` software-rendered image
remains intact. An accelerated CHD requires the corrected emulator as well
as its Xorg configuration; changing a disk image cannot update Prismatic's
embedded IRIS backend.

The [first direct CHD diagnostic](2026-11-02-newport-serial-console-size.json) (`chd-cc9bzcpv`) booted successfully but
stopped at an added `stty -f /dev/ttyE0 size` assertion: it returned `0 0`
while the boot console was `ttyZ0`. Allocating screen zero again reported
that it already existed and did not change that result. This observation
is retained as a failed console-size diagnostic; the independent graphical
console captures remain valid. The subsequent CHD desktop run omits that
serial-boot geometry assertion and does not claim to resolve it.


## Manual experimental bundle

The [direct CHD result](2026-11-03-newport-framed-image.json) verifies cold
boot, the exact installed kernel/resources, native Xorg with XAA enabled,
1280×1024 geometry, winterm's `/usr/people/xiritest` working directory, catalog
double-click launch, execution notification, granite/home links, service
cleanup and clean halt. The source CHD stayed unchanged. The
[unaltered framebuffer PNG](images/2026-11-03-newport-framed-image.png) also
shows the unresolved xmahjongg artwork corruption; this is a verified boot
and interaction observation, not a fully correct accelerated desktop.

Bundle: `.work/images/xiri-netbsd-desktop-20261102-framed-accel/`.
The CHD is 480,575,544 bytes (8 GiB logical), SHA256
`483560d87b3002a0a8fdae3d170caebcf4fed47c0d6bf87c9de69d1d50d71826`.
Its decompressed disk exactly matches source SHA256
`e4cb1f1b9fb6f8465434524aaacf33c848731f54da7f03416f1150897fb3e220`.
Use the included `run-iris.sh`; it selects the exact pinned corrected backend.
The launcher passes shell syntax and executable-help checks. Prismatic's
embedded backend must be updated separately to receive the color correction.

`--record-bundle` records verification in this experimental bundle while
leaving the default image pointer on `20261102-behavior`. The manual graphical
NVRAM remains unchanged. Root launches the services; xiritest owns the desktop.
See [manual image instructions](../XIRI-IMAGE.md#experimental-framed-console-acceleration-image).

All owned emulator instances were shut down after testing. The November 3
active-day upstream check still found `2eb811f` already integrated; no merge
was needed. The color fix is pushed on IRIS `xiri` as `819c682`.

## User acceptance and next cycle

On November 3 the user reported that acceleration is substantially snappier
and more usable, and accepted this as the base for further work. The next
priority is xmahjongg's corrupted artwork. This feedback does not erase the
recorded failures or establish a timed performance result. The manually used
NVRAM has changed since packaging and must be preserved; investigation uses
the frozen prepared raw disk and disposable copies instead.

The subsequent [xmahjongg cycle](2026-11-03-newport-xmahjongg.md) resolves the
reproduced artwork corruption in the Xorg driver and preserves this image
as the original accelerated comparison.
