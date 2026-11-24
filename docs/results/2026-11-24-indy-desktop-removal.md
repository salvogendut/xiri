# Indy desktop removal, native login and reinstall

Both releases passed the full lifecycle test using the [November 23 clean Indy CHDs](2026-11-23-clean-indy-desktops.md).
The 6.5.22f R4400 and 6.5.30f R5000 each have a separate ISO and a separate
writable overlay. Each release starts from its published CHD. Both the native
package and the vendor archive on the new CD match the existing receipt.
All eight qualified boots recorded a clean unmount and halt. Both original
CHDs retained their published hashes.

| Boot | Kernel | Checks |
| --- | --- | --- |
| Uninstall | Xiri 11.99.11 | Require explicit selection of the older clean-image ownership rules. Restore the stock Newport driver link and rpcbind. Recover a local edit to rpcbind and extra files in the IRIX software and font trees. Run removal a second time. |
| Native recovery | Stock NetBSD 11.0 | Use normal xdm authentication as `netbsdtest`. Open the native ctwm desktop, focus its UXTerm, type a command, verify the resulting private file and return to xdm. |
| Reinstall | Xiri 11.99.11 | Install from the matching CD. Retain an independently created desktop alias and rc configuration. Interrupt a second removal after detaching the IRIX tree, resume it using the receipt, and reinstall again. |
| Desktop recovery | Xiri 11.99.11 | Log in through xdm as `xiritest`, check 4Dwm, Toolchest, Icon Catalog, winterm and xclock at 1280×1024, read the saved winterm colour from the active X resource database, execute the original IRIX shell and log out. |

The fixture enables native xdm in the site's `/etc/rc.conf` and configures
the stock Newport driver in `/etc/X11/xorg.conf` before removing Xiri. The
uninstaller leaves that policy in place. User homes, the Xiri session selector,
the edited site configuration, native account databases, tty policy and module
policy are checked by checksum, owner, group and mode across the four boots.

| Release | Native ctwm | Restored 4Dwm | Active winterm foreground |
| --- | --- | --- | --- |
| 6.5.22f | [Stock NetBSD](2026-11-24-indy-6.5.22f-ctwm.png) | [Xiri](2026-11-24-indy-6.5.22f-restored.png) | `#c9ecc9` |
| 6.5.30f | [Stock NetBSD](2026-11-24-indy-6.5.30f-ctwm.png) | [Xiri](2026-11-24-indy-6.5.30f-restored.png) | `#c9d9ec` |

The older-receipt test also verifies that an ordinary uninstall refuses to
guess ownership. New installations record their own paths. A fresh install
creates new vendor trees, while complete retired trees remain available for
recovering local software or fonts. Physical Indy validation and in-place
upgrades are separate work.

The native xdm server invokes `/usr/X11R7/bin/X`, while Xiri's Xservers
file invokes `/usr/X11R7/bin/Xorg`. The first probe found the server only
by the second name. The corrected check finds the authorization file for
display `:0` under either spelling. One R4400 host run was interrupted and
repeated from a fresh private CHD. The host regression suite passed 85 tests.

The new per-release CDs and compressed test logs are in
`.work/installers/indy-11.99.11/removal`. See the [operator commands](../NATIVE-PACKAGE.md#remove-the-desktop-and-return-to-native-netbsd),
[lab procedure](../../lab/native-package/README.md#desktop-removal-and-reinstall)
and [per-boot records and hashes](2026-11-24-indy-desktop-removal.json).
