# Cumulative GNOME, preferences and Acrobat image

The new bundle passes separate cold-application and xdm/session checks and
is now the selected image for `./xiri run`. All owned test guests have halted
cleanly; previous images and manual state remain available.

The bundle is `.work/images/xiri-netbsd-desktop-20261104-acrobat/`.
Its 8 GiB disk compresses to **496,114,811 bytes**. CHD SHA-256:
`c10185ffd95a08a1db31d325ad6fe6ee537e9f18de230347f435960858388b6d`.
The prepared and extracted raw disk both hash to
`78ade8bdfad21c80f547eab4a4b8597ab18581b334d1d062acf3c462c0356b5d`.
Creation, `chdman verify` and the complete raw-disk round trip pass.

## Included changes

The module is source-equivalent to NetBSD `xiri`
`2ca3d76a4384cd73dbef1bd09b9cace12afadf41`, including the preceding
`d35accbc0f8` rename repair and the earlier GNOME Unix-socket, PTY and original
shell support. Module SHA-256:
`37c8a5114483ad834d0dbef551175e506a1874599aa8caf70366481be7559b2f`.
The [build ledger](../../lab/irix-acrobat/build.json) pins the unchanged core
kernel from `9390bc04900` and the image retains its tested `819c682` IRIS backend.
IRIS `xiri` has a newer integrated upstream tip; this does not repin the emulator.

The image imports the expanded 53-path GNOME resource set, the original PTY
helper and the complete 86-path Acrobat set. It preserves GIMP resources and
all prior desktop/font/catalog data. Original bytes, installed file hashes,
ownership, modes and link targets are verified. Separate bundle ledgers and
[import notes](../IRIX-IMPORT.md#preferences-and-complete-acrobat-resources-2026-11-04)
record every source and destination. No vendor binaries or image are in Git.

The maintained runtime exposes the unused native `/usr/adobe` prefix and
exports the original wrapper's supported `ACRO_CONFIG=mipsirix` option.
The synthetic IRIX account file uses HOME `/usr/people/xiritest` for xiritest
and `/` for root. Native accounts/passwords remain unchanged: native root
keeps `/root`, and netbsdtest remains in wheel. Fresh per-user profiles are
retained; diagnostic GNOME, GIMP and Acrobat settings are excluded.

The prepared run is `.work/xdm-image/prepare/ordinary-ogo_mvl0`, refreshed from
`.work/xiri-image/prepared-seed-20261103-gimp`. The previous selected GIMP CHD
and its manual NVRAM/overlay remain untouched. Preparation halts cleanly and
leaves its source raw disk unchanged. The first packaging attempt stopped on
a README hash change; the builder now verifies the saved preparation snapshot
and still requires every runtime code input to match. The original README
hash remains in the bundle's provenance; documentation can advance independently.

## Acceptance

The [direct-CHD record](2026-11-04-irix-acrobat-image.json) verifies graphical
Autoload boot with no TFTP kernel, filesystem module loading at securelevel 1,
all installed support-file hashes and a 1280×1024 XAA display. Three xiritest
logins each pass an 8,536-pixel rendering comparison with zero mismatches and
untouched winterm geometry/foreground-resize checks. The first also closes
an extra terminal through typed `exit`.

Both Toolchest and root-menu logout return to xdm with complete session
cleanup, while FAM, rpcbind, xdm and an independent login survive. A wrong
password starts no desktop. An intentionally failed startup exits 7, cleans
up and returns to the greeter; the next login succeeds. netbsdtest reaches
standard native ctwm with its correct home and wheel membership, then returns
to xdm. The final IRIX session double-clicks xmahjongg from Freeware with FAM
execution feedback. The source CHD remains unchanged and the guest halts
cleanly. PNGs show [4Dwm](images/2026-11-04-irix-acrobat-image.png),
[ctwm](images/2026-11-04-irix-acrobat-image-native.png), the
[greeter](images/2026-11-04-irix-acrobat-image-greeter.png) and
[untouched winterm](images/2026-11-04-irix-acrobat-image-winterm.png).

The separate [cold-application record](2026-11-04-irix-acrobat-cold.json)
uses a fresh disposable copy with no runtime replacement. GNOME Terminal runs
the original interactive IRIX shell under UID 1234 in `/usr/people/xiritest`;
its preferences save and reopen with [257 scrollback lines](images/2026-11-04-acrobat-cold-gnome-reopened.png).
Applications / acroread starts the original Reader, presents first-run setup,
opens the byte-identical [sample PDF](images/2026-11-04-acrobat-cold-acrobat-pdf.png)
and closes through Ctrl+Q. Desktop logout leaves no session processes; the
verified boot-managed FAM PID correctly survives under UID 1234. This guest
also halts cleanly with its source CHD unchanged.

One native XTest focus helper hits its ten-second alarm after PDF rendering.
Reader is idle, later X queries succeed and retrying the focus/exit succeeds;
its cause remains open. Early framebuffer captures retain stale frames and
are excluded in favor of fresh readback. The first cleanup assertion also
incorrectly includes the persistent FAM service; the accepted check verifies
its service PID separately from session ownership. These diagnostics remain
in the cold record. No claim is made that all input/rendering glitches are fixed.

The full gedit/GIMP preference and Acrobat page/zoom/reopen checks are linked
in the [preference](2026-11-04-irix-preferences.md) and
[Acrobat](2026-11-04-irix-acrobat.md) reports; they are not all repeated by the
cold-image check. The cycle also passes 38 host workflow/runtime tests, Python
compilation and shell syntax checks. The [catalog checklist](../ICON-CATALOG.md)
keeps unresolved behavior explicit.

## Reproduction and manual use

Preparation uses a new disposable disk and the separately staged resources:

```sh
python3 scripts/prepare-xiri-xdm-image.py \
  --seed .work/xiri-image/prepared-seed-20261103-gimp \
  --kernel-build .work/netbsd-acrobat-build \
  --baseline lab/irix-acrobat/baseline.json --keep-accounts \
  --gnome-resources .work/irix-gnome-preferences-resources \
  --terminal-resources .work/irix-terminal-resources \
  --acrobat-resources .work/irix-acrobat-resources
```

Package the printed clean run with `build-xiri-image.py`, this baseline,
`.work/netbsd-acrobat-build/tftp/netbsd-XIRI_INDY` and the preceding bundle's
pinned `emulator/` directory. Use a fresh output directory. Then run
`probe-xiri-xdm.py --bundle NEW_BUNDLE --winterm` and the separate application
checks before `qualify-xiri-image.py --promote`.

Launch the bundle directly with:

```sh
/var/home/salvogendut/Dev/xiri/.work/images/xiri-netbsd-desktop-20261104-acrobat/run-iris.sh
```

Log in as `xiritest` / `xiritest` for 4Dwm, or `netbsdtest` / `netbsdtest` for
native ctwm. These are public lab credentials. Applications / acroread opens
Reader; its bundled sample is `/usr/adobe/Acrobat4.0/Reader/Acrobat.pdf`.
The first-run dialog is expected. Reader's catalog icon currently does not
change while running. Wider PDFs, printing and browser integration remain
unqualified. See the [manual guide](../XIRI-IMAGE.md) for PROM, Prismatic,
shutdown and previous-image instructions.
