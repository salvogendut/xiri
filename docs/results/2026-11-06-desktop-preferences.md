# Per-user IRIX desktop preferences

Original Background, Color Scheme Browser and Window Settings choices now
survive logout/login and reboot under native NetBSD xdm. Two users retain
different profiles. The change is in native session startup; the kernel,
IRIX module and vendor program bytes are unchanged.

| User | Backdrop | Scheme | Focus | Window dragging |
| --- | --- | --- | --- | --- |
| xiritest | Reef | Inverness | Click to type | Opaque |
| xiritest2 | Sand | KeyWest | Point to type (default) | Outline (default) |

Backdrop/scheme changes and xiritest's window settings were selected through
the original panels. The second user's default focus/move behavior also checks
that the first user's overrides do not leak across logins. Before the fix, a
relogin restored granite, omitted the scheme/focus resources and overwrote
the saved backdrop. The original panels already saved successfully; startup
did not load their files and forced its own appearance on the command line.

`xiri-session` now loads `.Xresources` and `.Sgiresources` and supplies the
per-host `XUSERFILESEARCHPATH` used by the supplied IRIX 6.5.22m `Xsession.dt`.
4Dwm and Toolchest no longer receive forced backdrop/background colours.
Toolchest retains the numeric equivalent of SGIDarkGray for its decal,
because Xorg lacks that vendor colour name. Existing defaults still give a
new profile the granite pattern.

Solid fills publish a description without a pixmap. The old readiness check
therefore rejected a saved Solid choice at the next login. Startup now accepts
that case as well as patterned backdrops. The vendor's default `sgiLightBlue`
name remains unresolved in native Xorg and appears black; SGI colour-name
coverage is a separate resource gap.
A numeric `#7d9ec0` control permits login and a visible blue fill (observed
`#7c9cbe`); this does not establish exact colour fidelity or qualify the
Solid colour picker, which did not display its controls in the reopened panel.

The browser import contains the original `schemebr` executable under its
`colorscheme` alias. Toolchest uses the canonical name. The installer adds
`/emul/irix/usr/sbin/schemebr -> colorscheme` only when that name is absent,
preserving imported bytes and existing installations. No new vendor resource
copy is needed.

Xmahjongg's automatic launch was a remaining test fixture in normal startup.
It has been removed. The catalog regression now launches its initial game
explicitly through winterm, then checks a new double-click launch as before.
The application remains installed in Freeware.

## Persistence evidence

The disposable test starts from the qualified multi-user CHD and uses the
same pinned emulator, kernel and module. Each profile is checked after
logout/login and after a real guest reboot. Saved resource files, X resource
values and a clear backdrop pixel region match across the reboot; the two
users' backdrop samples differ. Files belong to their respective native
users and have mode 0600. Neither user's post-change login starts xmahjongg.

The [native pointer fixture](../../lab/irix-desktop-behavior/preferences-probe.c)
creates two real X windows. It clicks the first and moves the pointer to the
second, then drags the second window while holding the mouse button. This
verifies actual focus and movement behavior, rather than only checking
configuration strings. Both opposing policies pass before and after reboot.
The fresh second profile also verifies the vendor fallback that saves
`4DWm*…` resources in `.Sgiresources` when a separate `4DWm` file is absent.

The [preference evidence](2026-11-06-desktop-preferences.json) records both
profiles before/after reboot, followed by both profiles again with the final
startup script that also accepts solid backgrounds. It records focus/drag results,
resource and runtime hashes, menu launch and clean guest shutdown. PNGs show
[Reef/Inverness](images/2026-11-06-preferences-reef.png),
[Sand/KeyWest](images/2026-11-06-preferences-sand.png),
[Color Schemes opened from Toolchest](images/2026-11-06-preferences-color-schemes.png)
and the [numeric solid control](images/2026-11-06-preferences-solid.png).

Local evidence is under `.work/desktop-preferences/ordinary-bculflrl/`.
Background creates hidden helper windows with the same title as its panel;
the initial name-only visibility check inspected a helper. Checking the real
large window by ID confirms it is viewable. This was a fixture error.
The maintained host suite passes all 55 tests. The installer also resolves
the canonical browser name while preserving an existing path. The required
[IRIS upstream integration](../FORKS.md#iris-upstream-updates) is independently
built, tested and pushed; these guest checks retain the qualified emulator.

## User state and scope

The [user guide](../IRIX-SOFTWARE.md#desktop-preferences) describes the panels,
paths and login behavior. Keep `.Sgiresources` and
`.desktop-<hostname>/4DWm` in profile backups. The tests exercise both storage
forms; no source-image home directory is copied into a native account.

The Window Settings restart prompt was deferred with Cancel, then applied
through logout/login. Immediate window-manager restart, other control panels,
additional backdrop formats, and arbitrary scheme edits remain separate
checks. **Save Windows & Desks** still does not enable application-session
saving/restoration: the launcher deliberately keeps `SG_manageSession` and
`SG_autoSave` disabled. Those controls belong to the next desktop milestone.

## Manual image

The selected bundle is `.work/images/xiri-netbsd-desktop-20261106-preferences-v2/`.
Use `./xiri run`, then log in as `xiritest` or `xiritest2` (password matches
the username). `netbsdtest` keeps the standard ctwm desktop and wheel membership.
The image starts with the normal granite appearance; the diagnostic Reef/Sand
profiles are not preseeded. Xmahjongg launches on demand.

The [image qualification](2026-11-06-desktop-preferences-image.json) passes
full-screen xdm, both IRIX accounts and native ctwm, simultaneous FAM identity
checks, fonts, winterm startup/resizing, both logout routes, startup recovery,
catalog launching and clean shutdown. The final catalog screenshot contains
xmahjongg because the test explicitly launches it. The unchanged core/module
retain their prior shell-job qualification; those separate job sequences were
not repeated in this runtime-only cycle.

The [build ledger](2026-11-06-desktop-preferences-build.json) records preparation,
CHD verification, host checks and cleanup. The complete 8 GiB decompression
matches the prepared disk. Redundant decompression caches and duplicate test
base images were removed; the final source disk, canonical CHDs, overlays and
evidence remain. The earlier manual bundle is preserved.

Preliminary preparation/test attempts were superseded while adding the canonical
browser alias and solid-background readiness. A later cold-test supervisor returned 143 during
file verification, leaving its emulator running. That guest was reconnected,
halted cleanly and excluded from qualification; the subsequent direct test is
the accepted run. These attempts are recorded in the build ledger.

Reproduce the runtime refresh from the previous qualified bundle:

```sh
python3 scripts/prepare-xiri-seed.py \
  .work/images/xiri-netbsd-desktop-20261105-multiuser \
  --output-directory .work/xiri-image/prepared-seed-20261106-multiuser
python3 scripts/prepare-xiri-xdm-image.py \
  --seed .work/xiri-image/prepared-seed-20261106-multiuser \
  --kernel-build .work/netbsd-wait-accounting-build --keep-accounts
```

This cycle reused the matching retained raw seed through a verified symlink,
without another extraction. The final prepared run is
`.work/xdm-image/prepare/ordinary-2njhn1pq`. Package it using
`lab/native-wait/baseline.json`, the matching
`.work/netbsd-wait-accounting-build/tftp/netbsd-XIRI_INDY` boot kernel, and
the previous bundle's pinned emulator. Then check it with:

```sh
python3 scripts/probe-xiri-xdm.py \
  --bundle .work/images/xiri-netbsd-desktop-20261106-preferences-v2 \
  --multiuser --winterm --fonts
```

CHD SHA256: `9442ee066e567c587b0f88a5fac262c50ab7983f464dd5e6c0967867a2159e68`.
