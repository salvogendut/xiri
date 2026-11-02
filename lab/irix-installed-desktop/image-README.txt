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
Filetype icon artwork and catalog launch actions remain unfinished. The
next measured gap is file locking while opening the desktop type database.
Other original menu actions and complete desktop services remain unfinished.
Typing exit can leave a blank xwsh window after the native shell exits;
automatic terminal closure remains unfinished. Stopping xiri-desktop
removes the session's remaining clients.
Client UID is 1234; HOME is /usr/people/xiritest. Logs: /var/tmp/xiri-desktop.

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
