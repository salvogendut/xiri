# Native service and user-session ownership

The service/session split is qualified. Four desktop sessions clean up only
their descendants while system services and an independent same-user shell
survive. Two of those sessions reuse an existing authenticated X server.
See the [desktop record](2026-11-03-xiri-session.json),
[service lifecycle record](2026-11-03-xiri-services.json),
[catalog launch PNG](images/2026-11-03-xiri-catalog-desktop.png) and
[second user-session PNG](images/2026-11-03-xiri-user-session-2.png).

The selected manual CHD is unchanged, as requested. Native xdm and a new
deployment image remain the next work cycle.
## Implementation boundary

The maintained [`runtime/`](../../runtime/README.md) packages native services,
configuration, session startup and helpers independently of historical labs.
The installer preserves local configuration and enables rc.d services only
when explicitly requested. It supplies no proprietary payload and makes no
kernel or emulator changes.

- Native rpcbind owns its standard lifecycle. `xiri_famd` owns a foreground
  native FAM v1 process, its PID file and diagnostic log. Both survive desktop
  logout. FAM retains the existing single configured `xiritest` account mapping.
- `xiri_devices` prepares PTY aliases once per boot, after mounts and before
  LOGIN. Repeated starts do not remount PTYs underneath existing sessions.
- `xiri-session` uses the current native UID, supplementary groups, HOME and
  X authority on an existing display. It starts the original desktop clients
  and owns their descendants, leaving system services and X running.
- Root's manual `xiri-desktop` wrapper starts one X server with an explicit
  MIT-MAGIC-COOKIE-1 file, uses `su -l` for the configured user, and stops its
  own X server after the session. The direct user entry rejects an inaccessible
  display or an existing window manager.

The native guard registers NetBSD `EVFILT_PROC`/`NOTE_TRACK` before fork.
Kernel fork notifications follow children across setsid/double-fork, avoiding
UID-wide process selection and `kill(-1)`. TERM is followed by KILL after one
second, with a six-second cleanup bound. Failed tracking or incomplete cleanup
returns an error rather than falling back to killing the user's other work.
This is a supervisor for the session's descendant tree, not an implementation
of IRIX saved-session restoration.

The first desktop replay exposed a start-time race in the new guard.
`kern_fork.c` queues the child notification before assigning `p_start` and
making the child runnable. `KERN_PROC2` also omits valid start-time data for
dying processes. The initial guard could mistake either transition for PID
reuse. It now waits for a fully initialized child, queries its identity,
drains intervening exit events before retaining it, and rechecks identity
before signaling. Slot generations protect against reuse during event drain.
Dying processes are retired by their exit events. A live 25-process fork burst
now complements the quick 49-process fork/exit case. All changes are userspace;
NetBSD's existing fork and kqueue interfaces are sufficient.

The development harness also needed two corrections: uncover Toolchest without
moving its menu coordinates, and redirect the background `su` fixture before
launching it. NetBSD's PAM `su` supervisor attempts a foreground-group handoff
on its stderr terminal; allowing that fixture to use the diagnostic console
left the console inaccessible after the fixture exited. The final fixture
uses its own input/output files. The runtime's manual/user invocations already
redirected their `su` output to session logs.

## Desktop and descendant qualification

The fresh run `.work/irix-session/runs/ordinary-k2283trd` passes:

- Eight native guard cases: TERM-resistant child, setsid/double-fork,
  25 live processes, 49 quick fork/exit processes, failed launcher, failed
  exec, logout request and supervisor signal. An unrelated same-user shell
  survives each case; failed launch/exec statuses remain 7 and 126.
- Reboot with the filesystem-loaded IRIX module, PTY preparation, rpcbind and
  FAM already available before login. Repeated service starts preserve PIDs.
- Both original menu logout routes through the manual wrapper, then two
  direct `xiri-session` runs on the same externally supplied X server.
- Native winterm input in all four sessions: user `xiritest`, HOME and cwd
  `/usr/people/xiritest`, groups `1234 1235`, and the correct authority path.
  Each display rejects a client without its X cookie.
- An existing-window-manager refusal, occupied-display refusal, inaccessible
  display refusal, and failed client startup returning 7 with no descendants.
- Icon Catalog's 18 pages and a fresh Freeware double-click launch of
  xmahjongg (PID 379, after terminating the demonstration game PID 151).
- The native Render probe in every desktop: **8,536 pixels, zero mismatches**.

| Session | Tracked descendants | Remaining after logout |
| --- | ---: | ---: |
| Manual, Toolchest logout | 47 | 0 |
| Manual, root-menu logout | 43 | 0 |
| Existing X server, user session 1 | 41 | 0 |
| Existing X server, user session 2 | 41 | 0 |

FAM PID 1946, rpcbind PID 476 and independent shell PID 299 survive nine
checkpoints before, during and after these operations. The shell executes a
fresh command at each checkpoint; survival is not inferred solely from a PID
existing. None of those PIDs appears in a session guard's owned tree. External
Xorg PID 4524 stays alive and accepts clients after both direct user logouts.

The harness then explicitly stops its external display, independent shell,
FAM and rpcbind. No UID 1234 clients or Xorg remain, and the manual lock is gone.
The native ABI control still exits 37. The run records 16 installed-file hashes,
reports no RPC bind warnings in its boot/test serial log, halts cleanly and
leaves the source disk unchanged. All owned test emulators are stopped.

## Service lifecycle qualification

The [service record](2026-11-03-xiri-services.json), from
`.work/irix-session/runs/ordinary-_4zot5_g`, passes two stop/start cycles,
`rc.d restart`, removal of RPC program 391002/version 1 after each owned stop,
and refusal to adopt an external daemon. The refusal test temporarily removes
the service PID file, verifies that the daemon and RPC registration survive
the rejected start, restores ownership and stops it normally. Both services
are stopped explicitly, the guest halts cleanly and the source disk is unchanged.

FAM's default SIGTERM disposition does not execute its C++ Listener destructor.
The final rc.d stop hook therefore unregisters its program/version after
`rc.subr` has stopped the matched PID. Startup never unregisters an external
service. The final script's SHA256 is
`6669ab48614713237fd740a533274fea00ea5acb3ac61ab0b7c21295a12bbcf1`.
This focused replay qualifies the final stop hook separately from the desktop
replay, which started before that hook was added. The desktop launcher,
descendant guard, service startup and configuration are the same in both runs.

The host suite passes **28 checks**, including configuration preservation,
opt-in service enablement, and rejection of a purported passed result after
unclean shutdown or a changed source disk. Each guest run retains
its frozen harness snapshot; the maintained probe now captures that source
before lengthy input verification.

## Reproduction

From the prepared host environment:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/probe-xiri-session.py \
  --seed .work/xiri-image/prepared-seed-20261103-module
python3 scripts/probe-xiri-session.py --services-only
```

The probe verifies and clones the module image's raw seed, stages hashed
sources, builds natively with `-Wall -Wextra -Werror`, installs with services
enabled, and reboots before testing. It uses the qualified module/kernel from
NetBSD `d1ce7a96615`, IRIS `819c682`, the corrected Newport Xorg driver and the
existing IRIX 6.5.22m resources. No resources are re-imported.

The [fixture guide](../../lab/irix-session/README.md) describes the native
process tests. A separate command-reading native shell is started through
`su -l xiritest` and receives fresh FIFO commands throughout the desktop tests.
This tests same-user process survival, without claiming password login through
xdm. An additional native group checks credential preservation in winterm.
These fixtures and their account/group changes remain in the disposable guest.

## Limits and next step

The selected image still contains the older manual launcher; its pointer,
CHD, NVRAM and overlays are preserved. A source checkout alone does not alter
that image. The runtime installer requires the existing imported resources,
native FAM/rpcbind, Xorg configuration, fonts and account layout recorded in
its guide and the import ledger.

FAM v1 still maps local clients to one configured account. Native xdm password
authentication, login-manager X-server resets, a replacement deployment CHD,
original IRIX clogin and authenticated multiuser FAM are separate work.
The existing winterm startup/font-metric issue remains; interaction tests
explicitly resize winterm before typing. Broader applications, launch
animation, Dumpster operations and session persistence are unchanged.

IRIS upstream was fetched at `28fa516684c54e00e35b258c65e5dcac3a36165c`, already
contained in integration `1aed0dfc842a427e32a53ad083e1be0a9d46a613`. No merge or
emulator rebuild was needed. This cycle makes no fork changes. Independent
console-artwork work advanced NetBSD `xiri` to `1c248bf932f369c3271239b8c20bc3efd55bca44`;
that work is preserved and is not part of these tested kernel artifacts.
Both forks remain on `xiri`; pinned reproduction worktrees are preserved.
