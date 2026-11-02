Xiri development desktop: NetBSD + original IRIX applications

Machine: Indy IP24, R4400, Newport, 256 MiB RAM, disk at SCSI ID 1.
Standalone IRIS: run from this directory with --config iris.toml.
Prismatic: run from this directory with --config prismatic.cfg
           --state-dir prismatic-state.
The two configuration formats differ. Both use the same CHD.
Use a fresh copy for another machine; do not share a writable overlay.

When nvram-graphics.bin is included, the default manual profile boots on the
display automatically. In Prismatic press Ctrl+P to start, click the display
to capture input, log in as root (no password), then run xiri-desktop.
The separate nvram.bin retains the serial PROM profile for automated tests.
Serial B remains available at localhost:8891 for a diagnostic login.

At a PROM menu, select Start System or enter these commands in the monitor:
  setenv systempartition scsi(0)disk(1)rdisk(0)partition(8)
  setenv osloadpartition scsi(0)disk(1)rdisk(0)partition(0)
  setenv osloader boot
  setenv osloadfilename netbsd.boot
  setenv osloadoptions auto
  boot
The promoted NVRAM already contains these settings.

For a serial-profile boot, log in as root on serial B and run xiri-desktop.
In the graphical profile, Log Out in Toolchest or the desktop's right-click
menu ends the session and returns to the launching shell. For the desktop
menu, hold the right button, move to Log Out, then release it.
This does not yet save an IRIX desktop session.
Ctrl-C in the launching serial terminal remains an alternative.
Use shutdown -h now and wait for the halt/PROM before closing the emulator.

Xiri uses a 1280x1024 X screen. Default PROM timing may add two right pixels.
Desktop > Open Unix Shell opens IRIX xwsh with NetBSD's /bin/sh.
Toolchest retains its original menus, without an added Applications menu.
Find > Icon Catalog also uses the native launch bridge.
Icon Catalog now discovers its pages and lists application names, including
the 21 Freeware entries. Native FAM runs for this single-user session and
is stopped with it. FileManager can list native files and folders.
Application-specific Freeware icons and FileManager folder/document icons
now render. The kernel supplies the measured IRIX locks and seek offsets;
native FAM resolves imported paths beneath /emul/irix while retaining the
original client event names. Catalog launch actions remain to be qualified.
Other original menu actions and complete desktop services remain unfinished.
Typing exit can leave a blank xwsh window after the native shell exits;
automatic terminal closure remains unfinished. An intermittent xwsh startup
SIGFPE was also captured during a repeated desktop session and remains open.
Stopping xiri-desktop
removes the session's remaining clients.
Client UID is 1234; HOME is /usr/people/xiritest. Logs: /var/tmp/xiri-desktop.

Suggested manual checks:
- Open the Freeware page and inspect the application-specific icons.
- Open Unix Shell from Toolchest, type commands, and open a second shell.
- Close the initially launched xmahjongg, then try its catalog entry.
- Try other catalog entries individually; an icon does not certify the app.
- Inspect files/folders in /usr/people/xiritest/XiriTest with FileManager.
- Log out through Toolchest, restart the desktop, and try the desktop menu.
Record the exact entry/action and any dialog or terminal output. Session logs
are in /var/tmp/xiri-desktop/session.*; retain the CHD overlay for diagnosis.

To return to IRIX: halt NetBSD, stop the emulator, attach the original IRIX
CHD at SCSI ID 1, then at the PROM:
  setenv osloader sash
  setenv osloadfilename /unix
  setenv osloadoptions auto
  boot
These names match the supplied irix65 image. Other images can differ.
Keep separate NVRAM/state directories for IRIX and NetBSD.

See docs/XIRI-IMAGE.md, docs/IRIX-IMPORT.md and the bundle manifest.json.
Vendor files in this local image are not part of the public Git repository.
