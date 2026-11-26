# Keeping shared Freeware libraries when removing GIMP

On the IRIX 6.5.22f R4400 and 6.5.30f R5000 Xiri Indys, SGI Software Manager
4.1 identifies three installed subsystems that depend on the gettext library.
With GIMP, GTK+ and wget installed, requesting removal of `fw_gettext.sw.lib`
opens **Conflicts**. The first choice, **Do not remove fw_gettext.sw.lib**,
keeps all three. The second choice proposes removing their dependent
subsystems. SGI's command-line `inst conflicts` listed the same choices.

| Release | SGI dependency dialog | Freeware page after GIMP removal | Saved image after reinstall |
| --- | --- | --- | --- |
| 6.5.22f | [Conflict](2026-11-26-gimp-removal-6.5.22f-conflict.png) | [Catalog](2026-11-26-gimp-removal-6.5.22f-removed.png) | [Reopened image](2026-11-26-gimp-removal-6.5.22f-reopened.png) |
| 6.5.30f | [Conflict](2026-11-26-gimp-removal-6.5.30f-conflict.png) | [Catalog](2026-11-26-gimp-removal-6.5.30f-removed.png) | [Reopened image](2026-11-26-gimp-removal-6.5.30f-reopened.png) |

## What the checks establish

1. Each test starts with a private copy of the release's clean Mozilla Indy,
   installs the 19 selected Freeware subsystems and paints and saves a PPM as
   `xiritest`. The test also sets a nondefault image size in `~/.gimp-1.2/gimprc`.
2. After choosing to keep gettext and exiting Software Manager, SGI's installation
   history, the artwork table, the image and the preferences match their earlier
   values. The user can reopen the image in GIMP and run the original wget.
3. Removing the GIMP product clears its four subsystems, executable, catalog
   link and filetype rule. The other 15 subsystems stay installed. The desktop
   filetype table and every catalog symlink and target match the pre-GIMP
   desktop. At the next login the **Freeware** tab is still present and empty
   on these clean installations.
4. Reinstalling from the same disc restores the installed history, catalog links
   and artwork table. After a fresh xdm login, `xiritest` double-clicks **gimp**
   and opens the saved image. Its bytes, owner and the preferences survive.
   All 30,020 interior RGB pixels in the GIMP window match the saved image.

At each of four stages, the IRIX wget binary downloaded 31 bytes from an
HTTP server on the guest's loopback address. The bytes, wget binary and
`libintl.so.3` matched their respective originals. Wget printed
`utime: Function not implemented` when applying the remote timestamp,
then exited successfully. This covers HTTP transfer and content integrity.

The maintenance ISO contains the same 43 original Freeware distribution files
as the earlier installation CD. It adds a GIMP-only removal option to the
NetBSD helper. Both release-specific prerequisite discs are still required
for their respective desktops. The existing clean CHDs can be used directly.
[Manual procedure](../../lab/irix-installer/README.md#remove-and-reinstall-gimp) · [Per-release checksums and results](2026-11-26-gimp-removal.json).
