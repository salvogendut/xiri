Xiri development desktop: NetBSD + original IRIX applications

Machine: Indy IP24, R4400, Newport, 256 MiB RAM, disk at SCSI ID 1.
Standalone IRIS: run from this directory with --config iris.toml.
Prismatic: run from this directory with --config prismatic.cfg
           --state-dir prismatic-state.
The two configuration formats differ. Both use the same CHD.
Use a fresh copy for another machine; do not share a writable overlay.

At the PROM, select Start System or enter these commands at option 5:
  setenv systempartition scsi(0)disk(1)rdisk(0)partition(8)
  setenv osloadpartition scsi(0)disk(1)rdisk(0)partition(0)
  setenv osloader boot
  setenv osloadfilename netbsd.boot
  setenv osloadoptions auto
  boot
The promoted NVRAM already contains these settings.

Log in as root (no password) on serial B, TCP localhost:8891.
Run /usr/local/bin/xiri-desktop. Press Ctrl-C in that serial console to stop.
Use shutdown -h now and wait for the halt/PROM before closing the emulator.

Xiri uses a 1280x1024 X screen. Default PROM timing may add two right pixels.
Desktop > Open Unix Shell opens IRIX xwsh with NetBSD's /bin/sh.
Applications contains Unix Shell, Clock, Icon Catalog and Mahjongg.
Find > Icon Catalog also uses the native launch bridge.
Other original menu actions and complete desktop services remain unfinished.
Icon Catalog still has its known Blank/communication limitation.
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
