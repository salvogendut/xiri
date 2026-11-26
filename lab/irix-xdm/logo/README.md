# XiriBSD logo for the xdm login form

NetBSD's xdm draws the image beside the login fields from the
`xlogin*logoFileName` resource. On the Indy images the system resource
names `/usr/X11R7/include/X11/pixmaps/NetBSD.xpm` for colour displays.
Xiri includes those resources from `/etc/xiri/xdm/Xresources`. The default
then sets `xlogin*logoFileName` to `/usr/local/share/xiri/xdm-logo.xpm`.
Both release lines install the same artwork through the native runtime.
[Stock login form](../../../docs/results/2026-11-26-xdm-stock-form.png) ·
[XiriBSD logo on the same greeter](../../../docs/results/2026-11-26-xdm-logo-form.png).

On both the 6.5.22f and 6.5.30f Indy audio images, the live greeter measured
690×304 pixels with either logo. The login checks reached 4Dwm as `xiritest`
on 6.5.22f and native ctwm as `netbsdtest` on 6.5.30f. Both returned to xdm.
After removing the override, the flag's pixels matched the original capture
on each machine.

## Apply it to an existing image

An updated runtime installs the pixmap and a new
`/etc/xiri/xdm/Xresources.example`. Merge its logo setting into the active
`Xresources` after the system include, keeping other site preferences.
On an older image, use `.work/installers/xdm-logo-preview/xiri-xdm-logo.iso`
or build the small CD from the Xiri checkout.

```sh
genisoimage -quiet -R -V XIRI_XDM_LOGO -o /tmp/xiri-xdm-logo.iso \
    -graft-points xiri-logo.xpm=runtime/etc/xiri-logo.xpm
```

Attach it as the first CD in IRIS or Prismatic. Log out of the graphical
session. At a NetBSD root console, run:

```sh
mkdir -p /cdrom
mount -rt cd9660 /dev/cd0a /cdrom
install -m 444 /cdrom/xiri-logo.xpm /usr/local/share/xiri/xdm-logo.xpm
setting='xlogin*logoFileName: /usr/local/share/xiri/xdm-logo.xpm'
grep -Fqx "$setting" /etc/xiri/xdm/Xresources || \
    printf '\n%s\n' "$setting" >> /etc/xiri/xdm/Xresources
/etc/rc.d/xdm restart
```

If the logo CD is already mounted, start at the `install` command. To
restore the NetBSD flag, remove the added `xlogin*logoFileName` line from
`/etc/xiri/xdm/Xresources` and restart xdm from the console.

## Prepare the artwork

The source is the supplied [XiriBSD PNG](../../../xiri-logo.png). The
NetBSD flag's canvas is 185×150 pixels. This conversion fits the visible
emblem proportionally into the same canvas, centers it and gives xdm a
transparent XPM mask. Run from the Xiri checkout to regenerate it.

```sh
magick xiri-logo.png -channel A -threshold 2% +channel -trim +repage \
    -resize 185x144 -gravity center -background none -extent 185x150 \
    -channel A -threshold 50% +channel +dither -colors 64 -depth 8 \
    runtime/etc/xiri-logo.xpm
```
