# SGI Screen Saver on the Indy v6 desktop

Both release-specific saver v2 CDs add the original xlock presets and enable
the SGI `SCREEN-SAVER` extension in NetBSD Xorg. Open **Icon Catalog →
ControlPanels → screensaver**, enable the saver, leave screen locking off,
select **Qix** and click **Demo**. Qix draws moving lines across the screen.
Press **Space** to return to the panel. The same animation runs on inactivity.

| Release | Emulator | Framebuffer |
| --- | --- | --- |
| IRIX 6.5.22f | R4400 Indy | [Qix](2026-11-26-sgi-saver-6.5.22f.png) |
| IRIX 6.5.30f | R5000 Indy | [Qix](2026-11-26-sgi-saver-6.5.30f.png) |

On each clean disk copy the test installed the CD, restored the stock Xorg
module, installed the update twice and restarted xdm. Three frames sampled
two seconds apart showed animation in both Demo and ordinary idle (the test
temporarily shortened the 600-second timeout to eight seconds). Space woke
both. Disabling the saver returned the timeout to zero, logout returned to
xdm and both guests halted cleanly.
[6.5.22f measurements and CD digest](2026-11-26-sgi-saver-6.5.22f.json) ·
[6.5.30f measurements and CD digest](2026-11-26-sgi-saver-6.5.30f.json).

## Update an existing v6 disk

From the Xiri checkout, attach the CD that matches the vendor desktop.

```sh
release=6.5.22f  # or 6.5.30f
.work/images/xiri-clean-indy-${release}-v6-20261126/run-iris.sh \
  --cdrom4 "$PWD/.work/installers/indy-11.99.11/savers-v2/${release}.iso"
```

Log out of the desktop. From the NetBSD root console run the following
commands. Restarting xdm loads the new extension for the next login.

```sh
mkdir -p /cdrom
mount -rt cd9660 /dev/cd0a /cdrom
/etc/rc.d/xdm stop
sh /cdrom/install.sh
/etc/rc.d/xdm start
umount /cdrom
```

To restore the stock Xorg module, repeat the procedure with
`sh /cdrom/install.sh --restore-xorg`. The supplied IRIX presets stay
installed. The installer checks the release and the original native module
before replacing it. It retains a verified copy of the stock module alongside
`/usr/X11R7/lib/modules/extensions/libextmod.so.0`.

## Scope of the test

The native extension lets SGI xlock register one owner per screen and receive
activation and wake events from the X server. The MIT screen saver extension
remains available. Each CD contains its own release's 16 donor files and the
same native NetBSD 11.0/sgimips Xorg module. Password locking, monitor power
management and the other animations have separate qualification needs.
[Build and regression instructions](../../lab/sgi-saver/README.md) ·
[Original donor files and baseline](2026-11-26-indy-controlpanels.md#the-empty-screen-saver-list).
