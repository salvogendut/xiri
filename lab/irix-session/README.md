# Session ownership qualification

The implementation lives in [`runtime/`](../../runtime/README.md). These
fixtures run natively inside the disposable NetBSD guest; they are not host
process tests.

`descendants.c` creates a TERM-resistant child, a setsid/double-fork escape,
a 25-process live burst, a 49-process fork/exit burst, and an escaped child whose launcher exits with
status 7. `guard-tests.sh` checks timeout, clean exit, exec failure, logout-file
and signal shutdown, while an unrelated same-user shell stays alive. All
recorded fixture processes must be gone (or already-dead zombies), and the
guard must report successful tracking with no live descendants.

The saved-session extension also checks that a save hook sees live clients,
that a stalled hook reaches bounded cleanup, and that a nested supervisor
does not inherit the desktop's save hook. The unrelated shell must survive
all three cases. `resources.json` records the original `tellwm` import used
by the real desktop; it is not needed for the synthetic guard fixtures.

`shutdown-tests.sh` runs as root on a disposable NetBSD xdm image with
`xiritest` and `xiritest2`, while no graphical user is logged in. After
installing the current runtime, run `sh shutdown-tests.sh`. It checks an
empty desktop set, refusal of an unprivileged caller, simultaneous saves
under both users' own credentials, preservation of a generic application
guard, and bounded cleanup of a stalled save. Its temporary evidence
directory is printed at the end; fixture processes are stopped on exit.

For the real desktop check, change the open applications and their positions,
then run `shutdown -r now` from an administrative terminal without logging
out first. After boot, check that the previous guard log contains both
`SESSION_SAVE acknowledged by 4Dwm` and `SESSION_SAVE completed=1 exit=0`,
and that a new login restores the changed windows. Repeat with the second
user in explicit-save mode: save a home session, close one of its windows,
halt with `shutdown -h now`, cold-boot, and verify that the saved window
returns. Compare the first user's session files before and after to check
isolation. The reverse `rcorder -k shutdown /etc/rc.d/*` order must place
`xiri_sessions` ahead of `xdm` and `xiri_famd`.

Run from the repository root:

```sh
python3 scripts/probe-xiri-session.py --guard-only
python3 scripts/probe-xiri-session.py --services-only
python3 scripts/probe-xiri-session.py
```

The full run builds/installs the runtime on a clone of the module image's raw
seed, enables its rc.d settings and reboots. It checks two manual sessions
with original logout menus, then two direct user sessions on a separately
started authenticated Xorg server. A separate `su -l xiritest` command shell
reads a FIFO and executes fresh commands before, during and after logout.
This proves same-user process survival; password authentication through xdm
is not part of this probe. An extra native group checks that login groups
survive the session and terminal handoff. The test group and FIFO belong only
to the disposable guest.

FAM/rpcbind PIDs must remain unchanged throughout all client sessions. The
last two sessions must leave the existing X server alive and reusable.
After those checks, the harness explicitly stops its external display,
independent shell and system services, then halts the guest. Each run keeps
its source hashes, harness snapshot, serial output, result JSON and PNGs in
`.work/irix-session/runs/ordinary-*`. The seed and selected manual CHD are
never modified or promoted by this probe.

The [2026-11-03 qualification](../../docs/results/2026-11-03-xiri-session.md) records the passed runs,
source coverage, cleanup results and screenshots.
