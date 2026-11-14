# File Manager dialogs, desks and everyday preferences

The retained File Manager collision dialog was an actual mapped window.
The earlier probe sent Escape and checked unchanged files, which did not
prove the Cancel button had been activated. Both XTest Escape and emulator
keyboard Escape left the popup mapped. Clicking the original Cancel and
Overwrite buttons dismisses it. The maintained probe now checks `WM_STATE`
and actual client mapping after each dialog and after the directory move.
Xt retains an unmapped popup for reuse, so its name remaining in the X window
tree is not itself a failure. This finding does not establish a Newport
repaint defect or qualify keyboard cancellation against original IRIX.

The [fresh two-user run](2026-11-14-desktop-controls-filemanager.json) passes
all file operations, collision buttons, permission/retry and read-only
destination checks, with 18 dialog mapping observations. The
[first user's moved directory](images/2026-11-14-controls-xiritest-directory-moved.png)
and [second user's result](images/2026-11-14-controls-xiritest2-directory-moved.png)
show the destination without the old popup. The guest halted cleanly and its
base CHD remained unchanged. Its disposable media have been removed.

## Preference restoration

The original Desktop and Icon Views panels save their grid/hidden-file choices
in user resources and layout files. Mouse and Screen Saver instead write
shell commands to `~/.desktop-<hostname>/panelsession`. Those commands were
not replayed after xdm reset the display: the file survived, but the pointer
and blanking settings returned to Xiri's defaults.

`runtime/libexec/desktop-clients.sh` now replays a private copy as the normal
desktop user, after the initial X defaults and inside the session guard.
It translates the original X utility paths to NetBSD's paths. The user's
original file remains unchanged. The measured presets are Mouse Fast 1
(`7/1`, threshold 6) and Slow 2 (`1/4`, threshold 10), with standard X blanking
at 600 seconds or off.

The Keyboard executable initially failed with `ENOEXEC`. Its n32 initialized
data starts halfway through a native 8 KiB page. The module now admits that
specific executable layout; the existing core mapper already supports the
matching file prefix. No additional core-kernel edit was needed. The imported
Keyboard executable is unchanged, SHA256
`5a627a6ef06691381a71800b5b0f60f8981f8fdb79d89c18b0029ac15689cf8b`.

The normal Key Repeat toggle works. Repeat Speed and Repeat Delay remain
disabled because Xorg lacks `XSGI-Misc`. The panel nevertheless writes a
zero-valued SGI timing command when saving. Xiri omits that command in its
private replay copy, preserving Xorg's native timing and avoiding an invalid
option error. Animated screen savers, DPMS, all mouse options and the wider
keyboard controls are not covered by these checks.

The separate [Icon Views check](2026-11-14-desktop-controls-iconviews.json)
opens the original panel from winterm, saves opposite **Hidden Files** choices
for the two users, logs out/in and opens previously unseen folders. Both
folders contain the same two files. The [first user](images/2026-11-14-controls-xiritest-hidden-files-shown.png)
sees `.hidden.txt` and `visible.txt` with “2 of total 2” shown; the
[second user](images/2026-11-14-controls-xiritest2-hidden-files-hidden.png)
sees only `visible.txt`, with “1 of total 2” shown. The reopened panels retain
the corresponding checked/unchecked choices. These PNGs were visually
reviewed; the script separately verifies saved values and logout cleanup.

The [fresh-image restoration check](2026-11-14-desktop-controls-cold.json)
passes both users' native X values, grid resources, unchanged private preference
files and named desk layouts. The first user's choices remain intact after the
second user's session and after `shutdown -r now` with an active desktop.
Final logout and halt complete cleanly, and the base CHD is unchanged.

| Restored value | xiritest | xiritest2 |
| --- | --- | --- |
| Key Repeat | Off | On |
| Pointer acceleration / threshold | 7/1 / 6 | 1/4 / 10 |
| X screen blanking timeout | 600 seconds | Off |
| Align-to-grid resource | Off | On |
| Hidden Files default | On | Off |
| Selected extra desk | [Work](images/2026-11-14-controls-xiritest-restored-controls.png) | [Reading](images/2026-11-14-controls-xiritest2-restored-controls.png) |

## Desks

The original Overview supports create, rename, copy and delete. Rename uses
the selected desk's editor and Return. Input must retain focus in that child
widget; the test helper that forcibly focused its parent did not edit it.
An empty copied desk can be deleted. Deleting an occupied extra desk returned
its xclock to the remaining desk without closing it in the diagnostic run.
Deleting the starting desk displays the original explanatory error, dismissed
with OK. The [desk guide](../IRIX-WINDOWS.md) records these actions and the
continuous/explicit home-session distinction.

The first cold preference run restored the expected settings and desk, then
failed an overbroad file comparison: creating desks adds background entries
to `.Sgiresources`. The [retained difference](2026-11-14-desktop-controls-snapshot.json)
contains only those expected desk resources. The corrected test snapshots the
complete profile after desk edits and logout, before comparing restoration.
No image or runtime change was required for that test correction.

The corrected GUI run recorded both users' panel changes and desk operations,
then its host driver was interrupted during the second user's restoration
checks. The [panel checkpoint](2026-11-14-desktop-controls-panels.json) is
explicitly partial. Attempts to reattach to its saved disk did not complete
the remaining checks; that disposable disk was removed. The independent
`probe-xiri-controls-restore.py` starts from a fresh CHD and replays the exact
files saved by those original panels. This separates the observed GUI actions
from qualification of profile consumption, user isolation and active reboot.
Its first transfer attempt was rejected: literal tabs sent through the
interactive serial shell altered a saved `xset` command. The
[failed transfer record](2026-11-14-desktop-controls-transfer.json) is retained.
The helper now sends encoded data and checks each guest file's SHA256 before
opening a desktop; this correction changes the test setup only.

## Source and executable checks

NetBSD `xiri` commit
`a4a7095680588b1f0533a83153a77930b0f339ca` contains the n32 admission change.
The new module SHA256 is
`ad6ec8756c835bec4395c62428550a0d2877ec6c587b1ca1d793254798f6d8ea`.
The [build and source-equivalence ledgers](../../lab/irix-desktop-controls/README.md)
preserve the original dirty build inputs and prove they match the committed
fork. The native-wait core remains unchanged.

All 99 executable layouts pass as root and UID 1234: **198 records**. They
retain the previous admission suite and add prefix initialization/private
write, shared-file-page alias, full-file-page and BSS controls, plus malformed
alignment, extent, overlap and protection cases. Pure-BSS half-page starts,
interpreters and o32 do not gain the new exception. Each child group is absent
afterward and executable file contents remain unchanged. The fixtures are
synthetic; they contain no vendor source.
The [executable evidence](2026-11-14-desktop-controls-exec.json) records all
198 observations and clean shutdown; the
[diagnostic ledger](2026-11-14-desktop-controls-diagnostic.json) retains the
loaded module, native X settings and desk/window observations.

IRIS upstream `49210388ed5559667d7859dd46103b42b07d3fed` was integrated and
pushed on `xiri` as `55848d5383a5176f7292d77d06150bd174f8a426`. The shared flat-fill
path needed the fork's physical RGB24 mask conversion. Default Newport/display
checks pass 126/5, feature checks 226/5, and actual Vulkan resident/scanout
checks 10/6. The [upstream ledger](2026-11-14-desktop-controls-upstream.json)
records the initial detected mismatch and final results. The desktop image
retains its separately qualified emulator revision `819c682`.

The [full image qualification](2026-11-14-desktop-controls-image.json) passes
graphical disk autoboot, both IRIX accounts, native ctwm, authentication and
startup-failure recovery, both desktop logout menus, catalog launching,
session cleanup, 1280×1024 XAA, native/IRIX font checks and SGI colour aliases.
Its host driver was also interrupted near the final session. The final
session checks were repeated on that same running guest, using unchanged
probe functions; the evidence records this continuation. Final source,
artifact and screenshot checks pass, with a clean guest halt and unchanged
base CHD. It is not presented as an uninterrupted host test run.

## Manual image

The selected bundle is
`.work/images/xiri-netbsd-desktop-20261114-controls`. Start its graphical
Indy with `./xiri run`. The same public development credentials apply:
`xiritest` / `xiritest`, `xiritest2` / `xiritest2`, and native
`netbsdtest` / `netbsdtest` (in `wheel`; root's password is empty).

- CHD: `61f9b9883303470b68877083547d203bf3b177fe4ccb93136096ee9ed770611d`
- Decoded raw disk: `22ff75e9c8fd8f19aff91338f0965329e19b59e85f3fbd8fa9b6473e888c57db`
- Size: 497,997,967 bytes compressed; exact 8 GiB round-trip verified.

Only the compatibility module and `desktop-clients.sh` differ in the
[installed-file inventory](2026-11-14-desktop-controls-inventory.json).
The previous qualified CHD remains available. Test users' changed settings
were confined to disposable guest disks; they are not seeded into this image.

The [desktop PNG](images/2026-11-14-controls-desktop.png),
[native ctwm PNG](images/2026-11-14-controls-desktop-native.png) and
[post-reboot desk PNG](images/2026-11-14-controls-preferences-and-desks-after-reboot.png)
were visually reviewed. The host regression suite passes **63/63**;
Python compilation, shell syntax and diff checks also pass.

## Cleanup

All owned test IRIS groups are stopped. Disposable CHDs/overlays, test CDs,
media copies, temporary compilation outputs, the redundant decoded verification
disk and the superseded raw seed were removed. The new qualified image,
one reusable raw seed, compact evidence and pinned source/build artifacts remain.
The [cleanup ledger](2026-11-14-desktop-controls-cleanup.json) records **9.53 GiB**
of measured free-space recovery. Its separate apparent allocation total includes
shared reflink blocks and must not be described as additional physical space.
