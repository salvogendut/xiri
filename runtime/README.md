# Native services and desktop sessions

This is the maintained NetBSD userspace integration for the imported IRIX
6.5.22m desktop. Historical `lab/` launchers remain for reproducing their
original images. Installing this runtime does not import applications or
change the kernel, selected CHD, or login manager.

## Ownership

| Entry point | Owner and lifetime |
| --- | --- |
| Native `rpcbind` rc.d service | System portmapper; survives desktop logout |
| `xiri_devices` rc.d service | Prepares native/IRIX PTY aliases once per boot, before LOGIN |
| `xiri_famd` rc.d service | Owns one native FAM v1 daemon and its PID file; survives logout |
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
`/etc/xiri/fam.conf` consistent. Native xdm and original IRIX clogin are later
integration steps.

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

Run `xiri-desktop` as root for the existing manual workflow. On a display
already owned by a login session, run `/usr/local/bin/xiri-session` as
`xiritest`. The user entry refuses an inaccessible display, a root caller,
a different configured account, missing services, or an existing window
manager. Session logs are under `$HOME/.xiri/sessions/session.*`; the manual
wrapper uses `/var/tmp/xiri-desktop/session.*` and labels the user explicitly.
An optional `XIRI_SESSION_MS` duration is in milliseconds (zero means no time
limit). Both original logout menus call the native request helper.

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
