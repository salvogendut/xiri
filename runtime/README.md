# Native services and desktop sessions

This is the maintained NetBSD userspace integration for the imported IRIX
6.5.22m desktop. Historical `lab/` launchers remain for reproducing their
original images. Installing this runtime does not import applications or
change the kernel or selected CHD. Native xdm configuration is opt-in.

## Ownership

| Entry point | Owner and lifetime |
| --- | --- |
| Native `rpcbind` rc.d service | System portmapper; survives desktop logout |
| `xiri_devices` rc.d service | Prepares native/IRIX PTY aliases once per boot, before LOGIN |
| `xiri_famd` rc.d service | Owns one native FAM v1 daemon and its PID file; survives logout |
| Native `xdm` rc.d service (opt-in) | Starts Xorg, authenticates the native account, supplies X authority and resets the display after logout |
| `xiri-session` | Runs clients as the current native user on an existing authenticated X display; leaves X and system services running |
| `xiri-desktop` | Root convenience wrapper: ensures services are available, starts an authenticated X server, uses `su -l` for the configured user, and stops its own X server after logout |
| `xiri-launch`, `xiri-logout` | Native menu helpers; launched applications belong to the session's descendant tree; logout requests cleanup through its private directory |

`session-guard` uses NetBSD `EVFILT_PROC`/`NOTE_TRACK`, registered before the
first fork, to follow descendants across fork, setsid and double-fork. It
sends TERM, then KILL after a one-second grace period, and waits up to six
seconds for exit events. It waits for fork initialization before recording process start times,
drains intervening exit events, and checks identity again before signaling.
Dying processes are retired by exit events rather than invalid start-time
comparisons.
It does not scan or kill an entire UID. Failed tracking or incomplete cleanup
returns an error; there is no UID-wide fallback. The guard's log records its
owned PIDs and final cleanup result. A client launcher that exits also ends
its remaining descendants, including on failed startup.

The native account's HOME, working directory, supplementary groups and
XAUTHORITY are preserved. The manual wrapper creates an MIT-MAGIC-COOKIE-1
file for its X server. The direct user entry accepts the login's existing
authority file. Neither entry starts an X server with `-ac`.

FAM still maps local IRIX v1 clients to **one configured account**, currently
`xiritest`. This split does not implement authenticated multiuser FAM. Keep
`xiri_user` in `/etc/xiri/session.conf` and `untrusted_user` in
`/etc/xiri/fam.conf` consistent. Native xdm uses the same configured account;
original IRIX clogin remains a later integration step.

## Build and install

Build natively on the prepared NetBSD/sgimips system with its compiler and
X11 headers/libraries:

```sh
cd runtime
make
sh install.sh --enable-services
```

Run installation as root. `make install` or `sh install.sh` installs without
enabling services. `DESTDIR` supports staging; `BUILDDIR` selects compiled
helpers. Reinstallation replaces programs and `.example` files while
preserving existing configuration, including existing `rc.conf.d` policy.
Review any preexisting service configuration when enabling the runtime.

The opt-in service settings are:

```sh
# /etc/rc.conf.d/rpcbind
rpcbind=YES
rpcbind_flags="-h 127.0.0.1"
# /etc/rc.conf.d/xiri_devices
xiri_devices=YES
# /etc/rc.conf.d/xiri_famd
xiri_famd=YES
```

Reboot after initial deployment so PTY setup precedes login/PTY allocation.
`xiri_devices` uses `/var/run/xiri-pty-ready` to prevent repeated remounts in
the same boot. Re-running it during a desktop restart is a no-op. FAM logs to
`/var/log/xiri-fam.log`; its service PID is `/var/run/xiri_famd.pid`. Stopping the owned FAM daemon also unregisters its RPC program/version, so
`/etc/rc.d/xiri_famd restart` can register a new listener. Startup refuses a
daemon outside its PID file. Native rpcbind retains its own standard PID
file and rc.d lifecycle.

The candidate PTY setup maps both IRIX `/dev/ptc` and `/dev/ptmx` to native
ptm minor 2, which grants a new slave to the caller. Its `/emul/irix/dev/pts`
symlink targets `/../dev/pts`: NetBSD's explicit native-root lookup reaches
the native vnode even from an IRIX process. This replaces the earlier nullfs
view, whose controlling-terminal vnode could panic during session teardown.
An already configured ptyfs mount is retained; changing its group/mode still
requires setup before PTYs are in use. An occupied old mount is never forcibly
unmounted. The existing native winterm shell handoff remains in place.

Run `xiri-desktop` as root for the existing manual workflow. On a display
already owned by a login session, run `/usr/local/bin/xiri-session` as
`xiritest`. The user entry refuses an inaccessible display, a root caller,
a different configured account, missing services, or an existing window
manager. Session logs are under `$HOME/.xiri/sessions/session.*`; the manual
wrapper uses `/var/tmp/xiri-desktop/session.*` and labels the user explicitly.
An optional `XIRI_SESSION_MS` duration is in milliseconds (zero means no time
limit). Both original logout menus call the native request helper.

`/etc/xiri/Xresources` supplies terminal font defaults. It explicitly selects
NetBSD's existing 100dpi Adobe Courier Bold bitmap (11×20 winterm cells).
This closely matches IRIX's XWsh request and avoids the wildcard resolving to
scalable IBM Courier, whose intermittent 12×2 result was observed by both
native and IRIX Xlib. The underlying Type1 issue remains open. The session merges
these defaults below existing display resources, preserving an explicit user
font choice. `xiri_xresources` in `session.conf` can select another resource
file. Reinstallation preserves the administrator's file and updates its
`.example`, just like the other configuration files.

The native shell handoff preserves initialized PTY dimensions. The compatibility
module translates the measured window-size ioctls, so foreground native jobs
receive SIGWINCH and updated dimensions when original winterm is resized.

## Native xdm login

The prepared system includes NetBSD's native xdm and PAM configuration.
The optional configuration uses those standard files and selects the qualified
Newport server command via `xdm -server /etc/xiri/xdm/Xservers`. The greeter
resource overlay includes NetBSD's layout and normal Xft selection. This
requires the [corrected Newport driver](../lab/newport-text/README.md):
its software-fallback refresh restores Xft/Render glyphs and grey Toolchest
labels while keeping XAA enabled. Older images retain their `Xft.render:false`
workaround until explicitly upgraded with the matching driver. It retains
native X authorization, local-only display management and the standard
`/etc/X11/xdm/Xsession` dispatch to `$HOME/.xsession`.

Both xdm and the manual `xiri-desktop` launcher select `-dumbSched` for the
bundled Xorg 1.10.6. Its smart scheduler can repeatedly serve a pointer-query
client while another client's delayed button release is ready, stalling
input synchronization. The existing option selects round-robin dispatch;
it preserves XAA acceleration and the normal XTest event delays. Reassess
this workaround when upgrading the server. Existing installations retain
their administrator-owned Xservers file: adopt the new `.example` command
and restart xdm when no user session is active.

Build/install as above, then explicitly enable the services and display manager:

```sh
# As root, in runtime/:
sh install.sh --enable-xdm
passwd xiritest
```

This creates `/etc/rc.conf.d/xdm` with `xdm=YES` and
`xdm_flags="-server /etc/xiri/xdm/Xservers -resources /etc/xiri/xdm/Xresources"`
if absent. Existing rc.d policy and both display configuration files are
preserved; compare their `.example` files on upgrades.
The installer does not change an account's password,
home, `.xsession`, native xdm/PAM files or console gettys.

As `xiritest`, select the desktop (review any existing `.xsession` first):

```sh
cp /usr/local/share/xiri/xdm.xsession "$HOME/.xsession"
chmod 700 "$HOME/.xsession"
```

Other native users who leave `.xsession` unset retain NetBSD's standard
Xsession desktop (ctwm, terminal and clock). Xiri is a per-user selection;
the installer does not replace the system-wide Xsession. This does not extend
FAM beyond its one configured IRIX desktop account.

On the Indy, set **ttyE0** to `off` in `/etc/ttys` before rebooting; a getty
must not read the same graphical keyboard as xdm. Keep **ttyZ0** enabled for
serial administration. Reboot to run PTY preparation before any desktop login.
Log in at the graphical prompt as `xiritest` with the native account's password.
The session starts in `/usr/people/xiritest`, with the account's supplementary
groups and xdm's authority file. The `.xsession` entry maps local `:0` to
`127.0.0.1:0` because the current IRIX personality supports IPv4 TCP sockets;
xdm's existing authority entries authenticate this connection. It does not
create a replacement cookie or allow unauthenticated clients.
Xdm can supply a temporary `/tmp/.Xauth*` file; clients and diagnostics must
honor `XAUTHORITY` rather than assume `$HOME/.Xauthority`.
Startup diagnostics are in
`$HOME/.xsession-errors`; client logs remain in `$HOME/.xiri/sessions/`.
Xdm diagnostics are `/var/log/xdm.log`.

Both original logout menus end the client session and return to xdm. System
FAM/rpcbind remain running. A failed session also returns to authentication;
inspect `.xsession-errors` and the newest guard/client logs from serial login.
For the root manual fallback, stop xdm with `/etc/rc.d/xdm stop`, then run
`xiri-desktop`. To restore the previous graphical-console workflow permanently,
set `xdm=NO`, restore ttyE0 to `on`, and reboot. Do not run both display owners
at the same time.

## Existing prerequisites

The installer supplies integration files only. The prepared image must
already contain:

- The matching Xiri kernel/module and imported `/emul/irix` runtime, programs,
  fonts, backdrop, filetype rules, desktop resources and catalog links.
- The native `xiritest` account and owned home at `/usr/people/xiritest`.
- Native Xorg/Newport, X11 utilities and fonts under
  `/usr/local/share/xiri/fonts`, plus the qualified `xorg.conf` and
  `toolchest.chestrc` under `/usr/local/share/xiri`.
- The patched native `/usr/local/sbin/famd` and native rpcbind. FAM needs
  `/usr/lib/desktop -> /emul/irix/usr/lib/desktop` to resolve imported rules.

See the [copy ledger](../docs/IRIX-IMPORT.md),
[service integration](../docs/results/2026-11-02-desktop-services.md) and
[module image](../docs/results/2026-11-03-irix-module-image.md). Application
compatibility, saved-session restoration, preferences and physical-hardware
acceptance remain independent work.

## Qualification

`python3 scripts/probe-xiri-session.py` (from the repository root) clones the
qualified module raw seed, installs this runtime, reboots and tests service
ownership and repeated desktop sessions on accelerated Newport. It includes
same-user shell survival, inherited groups/X authority, catalog launching,
both menu logout paths, failed startup and a preexisting X server. Use
`--guard-only` for the native descendant lifecycle fixtures alone; `--services-only` checks
stop/start, restart, RPC unregistration and external-owner refusal. Host
installation-policy tests run with `python3 -m unittest discover -s tests -v`.

The [2026-11-03 qualification](../docs/results/2026-11-03-xiri-session.md) records the passed runs,
source coverage, cleanup results and screenshots.

`python3 scripts/probe-xiri-xdm.py` separately qualifies native graphical
password login, readable greeter text, full-screen geometry, both logout menus
and failed-startup recovery. It also logs in a separate native account with
no `.xsession`, checks the standard ctwm desktop and terminal, then returns
to xiritest. It builds and boots a disposable clone; the
selected CHD is unchanged. See the [xdm integration record](../docs/results/2026-11-03-xiri-xdm.md).


### Application launcher resources

The installer exposes imported `/usr/freeware` and `/usr/adobe` prefixes to
native utilities called by original IRIX scripts. It creates a symlink only
when the corresponding payload exists and the native path is unused; existing
administrator files, directories and links are preserved. The desktop session
exports `ACRO_CONFIG=mipsirix`, an option already supported by the original
Acrobat wrapper. It leaves native `uname` behavior intact. Importing application
resources is the image preparer's job; the runtime installer does not copy
vendor files or user preference profiles.
