Xiri development desktop: native NetBSD xdm + original IRIX applications

Machine: Indy IP24, R4400, Newport, 256 MiB RAM, disk at SCSI ID 1.
Run ./run-iris.sh from this bundle to use the included qualified emulator.
Prismatic: --config prismatic.cfg --state-dir prismatic-state
Prismatic must use the IRIS revision recorded in manifest.json.
Use a fresh state directory for this CHD; preserve older image overlays.

The graphical profile boots from disk automatically into native NetBSD xdm.
In Prismatic press Ctrl+P to start, then click the display to capture input.
Log in using these public, disposable development-image credentials:

  xiritest / xiritest   Original IRIX 4Dwm desktop
  netbsdtest / netbsdtest   Standard native NetBSD ctwm desktop

The IRIX session uses UID 1234 and HOME/cwd /usr/people/xiritest.
The native account uses UID 1236 and HOME/cwd /home/netbsdtest.
netbsdtest belongs to wheel: run su - in its terminal for a root login shell.
Root has no password in this development image.
Only xiritest selects the Xiri .xsession; the system Xsession/PAM stay native.
FAM still supports one configured IRIX desktop account, not multiple users.
Xorg uses the full 1280x1024 accelerated Newport configuration. The pinned
emulator scanout adds two right-hand columns. A greeter-only Xft resource
workaround restores text while preserving XAA and the Render extension.

IRIX Log Out through Toolchest or the desktop right-click menu returns to xdm.
For the root menu, hold the right button, move to Log Out and release.
System FAM/rpcbind and xdm remain running across user sessions.
Native ctwm's Quit menu is available; automated qualification ends the native
window manager from its own terminal and checks return to the greeter.
Saved IRIX sessions are not restored.

Root (no password) remains available on serial B at localhost:8891 for
administration. The graphical ttyE0 getty is disabled to leave keyboard
ownership to xdm. For manual fallback, stop xdm with /etc/rc.d/xdm stop,
then run xiri-desktop as root. Do not start a second X server over xdm.
Use shutdown -h now on serial B and wait for the halt/PROM before closing IRIS.

The IRIX personality loads at boot as compat_irix_o32.kmod for both o32/n32.
modstat should show compat_irix_o32 as exec / filesys at securelevel 1.
Keep the included kernel and module together; they still require our fork.

Suggested manual checks:
- Log in as xiritest. In winterm run id -un, echo "$HOME" and pwd.
- Open Unix Shell from Toolchest and try a second terminal.
- Run stty size, resize the terminal, and run stty size again. Dimensions
  should follow the visible character grid. Type exit in the extra terminal;
  its window should close without ending the desktop.
- Close the initial xmahjongg, then double-click its Freeware catalog entry.
- Check running-icon feedback, granite, filesystem/home and Dumpster icons.
- Log out through both IRIX menus, logging in again between checks.
- Log in as netbsdtest, use the native terminal/ctwm, then return to xiritest.

Terminal defaults use the imported SGI Screen bitmap font (8x15 cells).
/etc/xiri/Xresources supplies these defaults below existing display resources.
Known limits: Xorg's scalable IBM Courier face can return collapsed 12x2
metrics to native and IRIX clients; that underlying Type1 failure remains open.
Window resizing and normal shell exit are covered by the new checks.
Winterm uses NetBSD /bin/sh; original IRIX /bin/sh
handles catalog command launches. Application support depends on the module
and resource set recorded in this bundle; see any application notes below.
Continued-child notifications, IRIX nanosleep, xosview statistics,
complete Dumpster actions, preferences and
saved-session behavior remain unfinished. A catalog icon does not certify
the corresponding application. Boot's inherited savecore namelist warnings
do not prevent boot, but automatic crash-dump collection remains unqualified.

Logs: ~/.xsession-errors, ~/.xiri/sessions/, /var/log/xdm.log,
/var/log/xiri-fam.log. Retain the image overlay and exact failed action.

If PROM settings need restoring:
  setenv systempartition scsi(0)disk(1)rdisk(0)partition(8)
  setenv osloadpartition scsi(0)disk(1)rdisk(0)partition(0)
  setenv osloader boot
  setenv osloadfilename netbsd.boot
  setenv osloadoptions auto
  boot

To return to the supplied IRIX image: halt NetBSD, stop the emulator, attach
the original IRIX CHD at SCSI ID 1 and use its separate NVRAM/state directory:
  setenv osloader sash
  setenv osloadfilename /unix
  setenv osloadoptions auto
  boot
Other IRIX images may use different names.

See docs/XIRI-IMAGE.md and manifest.json for exact qualification/provenance.
Imported IRIX files in this local image are not part of the Git repository.
