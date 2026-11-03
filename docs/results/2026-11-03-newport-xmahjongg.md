# Accelerated xmahjongg texture repair

The original IRIX xmahjongg 3.6.1 now renders its artwork correctly with XAA
and Composite enabled. Its 1006×614 window on board 12345 matches the software
control exactly: **617,684 pixels, zero differences**. The fix is in the
native Xorg Newport module, with the existing framed NetBSD kernel and corrected
IRIS renderer unchanged. The user's accepted accelerated development baseline
and its manual overlay/NVRAM are preserved.

[Patched game PNG](images/2026-11-03-newport-xmahjongg-patched.png),
[original failure PNG](images/2026-11-03-newport-xmahjongg-original.png),
[software control PNG](images/2026-11-03-newport-xmahjongg-software.png),
and [machine-readable measurements](2026-11-03-newport-xmahjongg.json).

## Cause and correction

The matching [public xmahjongg source](https://www.lcdf.org/xmahjongg/)
chooses the deepest TrueColor visual. The installed IRIX game therefore selects
Composite's 32-bit visual `0x41`, even though the Newport screen is depth 24.
We verified its actual window depth with `xwininfo`. Disabling Composite keeps
XAA enabled but makes the game select depth 24, where its artwork is correct.
That control narrows the failure to the redirected/Render path; it is not the
proposed fix.

The [XAA caller](https://github.com/NetBSD/xsrc/blob/b2f7e3892002986f53e61cb0540e281fcbfab335/external/mit/xorg-server.old/dist/hw/xfree86/xaa/xaaPict.c)
rejects transforms and sends clipped source rectangles to the driver's
CPU-to-screen texture callback. Newport incorrectly interpreted those extents
as scaling requests. Its direct copy also added `srcx` again between rows;
its repeated copy failed to reset the X origin between rows and mishandled
negative origins. The alpha-mask setup used RGB instead of HOSTRW's BGR byte
order for solid colors.

The [patch and build recipe](../../lab/newport-xaa/README.md) correct these
operations. They live in Xiri because NetBSD **xsrc** is separate from the
NetBSD kernel fork. No vendor binary/data or additional kernel/emulator change
is needed. XAA and Composite remain enabled.

## Validation

| Check | Original | Patched / control |
| --- | --- | --- |
| Native ARGB/A8 Render regression, 8,536 pixels | Installed module: 5,136 mismatches; source-built module: 5,109 | Patched: zero; software: zero |
| Original game, board 12345, depth 32 | Corrupt artwork | All 617,684 window pixels equal the software control |
| Native depth-24 image/blit/atlas regression | Earlier control passes | 165 cases / 2,207,595 pixel comparisons pass, plus fill/plane-mask checks |

The Render test covers full and clipped copies, nonzero source origins,
right/bottom edges, repetition, negative repetition and untouched borders.
It uses opaque ARGB, binary A8 masks and PictOpOver. Original source builds
against the same guest SDK reproduce the defect, ruling out a module-build
change alone as the explanation. Rebuilding the pinned patched source succeeds
without warnings in the native build log. The focused test itself also compiles
with `-Wall -Wextra -Werror`.

The ordinary game comparison uses unchanged installed IRIX bytes and the same
kernel/emulator. It compares the full game client area, with the pointer moved
outside both windows. The depth-24/no-Composite control is also visually correct,
but its color precision differs by up to two levels, so the exact comparison
uses depth 32 with Composite for both XAA and software rendering.

A separate depth-32 core-GC partial-mask check still reports
`mask=ff0000 expected=ff0000 fill=ffffffff copy=ffffffff` with both the original
and patched driver. Keep that diagnostic open; it does not invalidate the
bounded Render cases or the exact game comparison. Partial-alpha blending,
other Render operators, physical Indy hardware and a complete game remain
unqualified. Window-management and font-metric glitches outside this patch
remain separate work.

## Full desktop replay

The corrected `.work/desktop-usability/ordinary-mhxltfzz` run passed graphical
boot/root login, the xiritest shell identity and HOME/cwd
`/usr/people/xiritest`, both logout routes, service cleanup, native controls,
payload/support-file checks and clean halt. The Render probe passed in both
XAA sessions. Winterm was explicitly resized for the input checks; this does
not qualify its unassisted startup font metrics.

The game accepted hint/take and undo, with visually verified tile counts
**144 → 142 → 144**. Its client area after resize/restore matched the post-undo
frame exactly (617,684 pixels). See the [initial desktop](images/2026-11-03-newport-xmahjongg-desktop-initial.png),
[removed pair](images/2026-11-03-newport-xmahjongg-desktop-move.png),
[undo](images/2026-11-03-newport-xmahjongg-desktop-undo.png), and
[restored window](images/2026-11-03-newport-xmahjongg-desktop-redraw.png).
The initial/post-undo frames differ only in the pointer's 10×16 bounding box
inside the game (93 changed pixels); tile artwork is restored. This is bounded
interaction evidence, not a complete-game qualification.

Reproduce the prepared-disk qualification after building/exporting the module:

```sh
python3 scripts/probe-xiri-desktop-usability.py \
  --seed .work/xiri-image/prepared-seed-20261102-behavior \
  --kernel-build .work/netbsd-newport-frame-build \
  --baseline lab/newport-accel/corrected-baseline.json \
  --iris-bin-dir .work/target-newport-accel/release \
  --xorg-config lab/newport-accel/xorg.conf \
  --newport-driver .work/newport-xmahjongg/newport_drv.so \
  --arrange-winterm --check-xmahjongg
```

## Reproduction and provenance

- Kernel: `XIRI_NEWPORT_FRAME_20261102`, snapshot equivalent to NetBSD
  `a536d8c4da2`; boot SHA256
  `58888643294a2794770d8b6a7b4dcfb89b77449511160d91100130f6d774fd88`.
- Emulator: IRIS `xiri` `819c682`, using the existing pinned corrected binaries.
  Upstream `2eb811f` was rechecked and is already included; no merge needed.
- Driver: NetBSD xsrc `b2f7e3892002986f53e61cb0540e281fcbfab335`, Newport 0.2.4,
  plus the recorded patch. Native GCC 12.5.0, Xorg 1.10.6, driver ABI 10.0.
- Patched module SHA256:
  `ce4f780398641bf90cc8ebe517dd03617df7bb447ba89da22c28357d4d898a74`.
  [Build manifest](../../lab/newport-xaa/build.json) pins source, inputs and SDK headers.
- Original/patched isolated run: `.work/newport-xmahjongg/isolated-_k6qp88q`.
  The original and patched Render responses, game screenshot and complete
  native regression log are retained there.
- Control run: `.work/newport-xmahjongg/isolated-trw4se_g`. Its initial command
  incorrectly used `--seed` and did not start a game; that initial observation
  is excluded. Explicit later responses record the valid `--number 12345`
  controls, native source build, software Render pass and final software PNG.
- One native regression launch selected the wrong diagnostic CD and failed to
  find its source. After switching to the intended ISO, the same source built
  and the complete 165-case log passed. The failed attempt is retained.
- The first full-desktop replay was interrupted after spotting ambiguous
  duplicate game names in the test. Its disk is not a packaging source; the
  corrected replay closes the startup game before selecting board 12345.

The earlier release-set Xorg module, accelerated CHD and software CHD remain
available as controls. Use fresh diagnostic copies; preserve manual overlays.

## Manual test image

The new bundle is
`.work/images/xiri-netbsd-desktop-20261103-newport-xmahjongg/`.
The 8 GiB disk compresses to 480,615,682 bytes. CHD SHA256:
`1fa5c92ffac3706680e16acd1270df4707928106529cf94084152f9dfac14ab5`.
Decoded raw SHA256:
`2d19c840bcc5d5e5d424a5f12b4def72b9e8681e6b9e172b22bd51943bf7bb82`.

The builder verified the CHD and its exact raw round trip. A disposable copy
then booted directly from disk in `.work/xiri-image/runs/chd-qi6uyd7c`.
Its native Render test passed all 8,536 pixels; the installed module hash and
support files passed; Icon Catalog double-click launched a new xmahjongg
process, with correct artwork. Native controls, HOME, backdrop/home links,
FAM execution notification, service cleanup and clean shutdown passed.
See the [cold-boot qualification](2026-11-03-newport-xmahjongg-image.json) and
[unaltered framebuffer PNG](images/2026-11-03-newport-xmahjongg-image.png).

`lab/irix-installed-desktop/image.json` now selects this accelerated development
image. Older images, manually used NVRAM and overlays were preserved. The
bundle contains the exact tested backend; its launcher passes shell syntax,
executable-help and hash checks:

```sh
/var/home/salvogendut/Dev/xiri/.work/images/xiri-netbsd-desktop-20261103-newport-xmahjongg/run-iris.sh
```

Log in as `root`, then run `xiri-desktop`. The service launcher remains root;
the desktop runs as xiritest with HOME/cwd `/usr/people/xiritest`. Keep the
image's development limitations explicit: the source-disk tests exercise one
move, undo and redraw, not a full game, and winterm was explicitly resized for
typed-input checks. See [manual image instructions](../XIRI-IMAGE.md).

All owned test emulators were stopped. Both fork integration branches remain
clean and pushed; this cycle changes Xiri's reproducible xsrc patch and image
workflow, without repinning the kernel or emulator.
