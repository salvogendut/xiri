# 4Dwm windows and desks

Use **Toolchest → Desktop → Extra Desks** to open the original **Desks
Overview**. The older images omitted its executable even though the menu,
resources and libraries were present. The new resource package adds
`/usr/sbin/ov` at `/emul/irix/usr/sbin/ov`; it does not replace 4Dwm or its menus.

The [cold-image checks](results/2026-11-13-desks.md) cover the controls below,
two users' separate desks, saved window geometry and restoration after logout
and orderly reboot. Additional Overview commands remain outside that check.

## Window controls

The small title-bar button minimizes a window; click its minimized icon to
restore it. The large square maximizes it. These original keyboard bindings
are also available while the window has focus:

| Action | Keys |
| --- | --- |
| Window menu | Alt+Space |
| Minimize | Alt+F9 |
| Maximize | Alt+F10 |
| Restore normal size | Alt+F5 |
| Raise / lower | Alt+F1 / Alt+F3 |
| Move / resize | Alt+F7 / Alt+F8 |

The window menu's **Move** and **Size** commands accept arrow keys; Return
accepts and Escape cancels. A terminal resizes in character cells.

The default **Point to type** policy sends keyboard input to the window under
the pointer. For Alt+Tab and Shift+Alt+Tab focus navigation, select **Click to
type** in **Desktop → Customize → Windows**. If the panel asks to restart the
window manager, Cancel that prompt and log out normally, then log back in.
This is the original policy distinction, also described in SGI's
[keyboard-focus instructions](https://techpubs.jurassic.nl/manpages_0530/cat6/rawks.html).

## Desks Overview

1. In Overview, press **Ctrl+N** to create another desk.
2. Drag a small window representation from one desk to another to move it.
3. Double-click a desk to switch to it. Windows assigned to other desks are
   hidden, while their applications continue running.
4. Toolchest and Overview stay visible across desks. **Global** holds windows
   that appear on every desk.

Select a desk, then use **Desk → Rename Selected** (`Ctrl+R`), type its name
and press Return. **Copy Selected** (`Ctrl+C`) makes another desk. Use
**Desk → Delete Selected** to remove the selected extra desk. In the measured
occupied-desk case, its xclock window returns to the remaining desk without
closing the application.

The desk where the session starts is protected. Overview displays **Desk
Overview Error** with instructions: in continuous-save mode switch to another
desk first; in explicit-save mode set a new home session from Windows settings.
Dismiss that message with **OK**. The original
[Overview manual](https://techpubs.jurassic.nl/manpages_0530/cat1/ov.html) describes
the wider command set; complex arrangements remain separate checks.

## Saving an arrangement

The [saved-session guide](IRIX-SOFTWARE.md#saved-desktop-sessions) explains
**Continuously**, **Explicitly**, and **Set Home Session**. Each user's
`~/.desktop-127.0.0.1/0.0/` holds the window list, desk assignments and current
desk in `4Dwmsession`, `4Dwmdesks` and `4Dwmdeskname`. Preserve all three when
backing up a layout. Preferences and desktop files remain in that user's
native home under `/usr/people/<username>`.

Save work inside applications separately. Restoring a window requires a
usable X11 restart command and does not resume its former process or shell
jobs. Use normal logout or `shutdown -r now` / `shutdown -h now` so the session
can save before X stops.
