# Desktop power-off on NetBSD/sgimips

The donor's **Toolchest → System → Shut Down System** calls
`/usr/sysadm/bin/runtask /usr/sysadm/taskdf/SaDtShutdownTask.tdf`.
Xiri keeps the label and supplies the same action in the 4Dwm desktop
menu next to **Log Out**. The session runs as the authenticated user.
NetBSD's base `/sbin/shutdown` grants execution to root and the
`operator` group. On the two development disks `xiritest` is an operator.

**Cancel** is the default. Confirming **Shut Down** records a request in
the user's private session directory and initiates normal logout. After
saving the session and reaping its descendants, the desktop supervisor
executes the fixed command `/sbin/shutdown -p now`. Starting `shutdown`
earlier made the initiating session count the privileged shutdown process
as a remaining application. Other active desktops are saved by
`xiri_sessions` during NetBSD shutdown.

## Build and install the v6 update

Use the NetBSD/sgimips o32 `session-guard` produced by the runtime build.
From the Xiri checkout, package it with the matching menu resources.

```sh
sh lab/desktop-power/package.sh /path/to/sgimips/build/session-guard menu.iso
```

Mount the CD on the installed guest. From a NetBSD root shell use
`sh /cdrom/install.sh` to install the menu and supervisor. Add
`--allow-xiritest` to grant the development account operator membership.
Log out and back in to pick up the new supervisor, group and menus.
The installer checks the v6 files before replacing them and accepts a
repeat installation. The two release disks and their overlays remain separate.

## Indy checks on November 26, 2026

| IRIX desktop | Confirmed power-off from | Session save | Clients left at logout |
| --- | --- | --- | --- |
| 6.5.22f | 4Dwm desktop menu | Acknowledged by 4Dwm | 0 of 47 |
| 6.5.30f | Toolchest System menu | Acknowledged by 4Dwm | 0 of 45 |

Both menus opened the confirmation dialog on each release. Cancelling left
the same session and Icon Catalog running. Confirming powered off the emulated
Indy, and the next cold boot reached xdm. Under `netbsdtest`, the same action
displayed the permission message on both releases. That account retained its
existing `wheel` membership.

[Manual launchers and confirmation screenshot](../../docs/XIRI-IMAGE.md#power-off-from-toolchest-or-4dwm).
