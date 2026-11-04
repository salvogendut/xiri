# GNOME Terminal PTY and descriptor startup

This cycle follows the GNOME startup survey. It adds the socket-pair and
legacy descriptor-transfer interfaces needed between original GNOME Terminal
and its original PTY helper. It also supplies the missing helper and replaces
the emulation namespace's layered PTY view with direct native-vnode lookup.
GNOME Terminal now starts the original IRIX shell and accepts typed commands;
that default shell still lacks interactive terminal detection and a prompt.
With the existing native-shell handoff selected explicitly, command input,
foreground resize notification and normal exit pass. The
[PNG](images/2026-11-04-irix-terminal-native.png) shows that native-shell check.
The published GIMP CHD is unchanged; these are candidate module/runtime
changes on a disposable copy.

The [baseline record](2026-11-04-irix-terminal-baseline.json) retains the
separate traces, path observations and guarded cleanup for each earlier
startup attempt.
The [cycle evidence](2026-11-04-irix-terminal.json) retains the application,
session, resource, regression and cold-boot observations, including failed
diagnostic attempts separately from passed checks.

## Failure sequence

The baseline terminal's “unable to fork: Function not implemented” dialog
comes from `socketpair(1, 2, 0, pair)` returning IRIX ENOSYS (89), before any
fork. With socketpair implemented, two pairs and the fork succeed, but the
child cannot execute `/usr/freeware/sbin/gnome-pty-helper`: it is absent from
the imported installation. The terminal then reports a generic Error 0.

After importing the unchanged helper, native `/dev/ptmx` minor 0 allocates a
slave still owned by root. The unprivileged helper cannot repair ownership
and enters its original `/usr/sbin/mkpts` fallback; that program is absent.
The terminal and helper wait for one another until the guard stops their
three-process tree. Mapping IRIX `/dev/ptmx` to native ptm minor 2 grants the
slave to its caller at allocation, just as the existing `/dev/ptc` alias does.

The next trace reaches libc's `ptsname` master check: an I_STR request with
command 0x5064 and zero timeout/length/data. An independent original-IRIX
probe confirms the exact request, success on both master entry paths and
errors for invalid descriptors, an ordinary file and a null argument. The
module accepts that request only for native PTY master descriptors. The
already supported UNLKPT 0x5002 contract remains intact.

The publicly released
[GNOME libraries 1.4.2 source](https://download.gnome.org/sources/gnome-libs/1.4/gnome-libs-1.4.2.tar.gz)
was consulted for protocol context: the helper passes master and slave in
separate one-descriptor messages. It is not evidence of an exact source
match for the supplied binaries. Actual IRIX ABI layouts and behavior are
measured with independent fixtures and traces; no leaked vendor source is used.

## Module and runtime boundaries

The adapter supports IRIX AF_UNIX/SOCK_STREAM socketpair, returning two
32-bit descriptors through the caller's pointer for both o32 and n32.
NetBSD's allocation/copyout path unwinds both descriptors on failure.
Datagram pairs and other families/types/protocols retain explicit errors.

Legacy sendmsg/recvmsg uses the measured 24-byte header and 8-byte iovecs.
For Unix streams, one complete descriptor is translated to native
SCM_RIGHTS. NetBSD owns descriptor lookup, credential checks and socket
lifetime. The receive path closes every externalized descriptor if payload,
rights output or length output fails, or if a native peer sends an unsupported
larger control message. Successful transfer retains ownership for the caller.

This is a bounded subset: one descriptor per send, positive data payload,
receive capacities 4–64 bytes, no rights peeking, no foreign control flags,
no destination address and no extended/XPG message layout. Original truncated
rights behavior can leak handles, and original rights peeking does not return
a usable externalized descriptor; these are explicit policy departures.
The existing data-only Unix and IPv4 receive paths remain separately checked.

The original helper is imported from `/usr/freeware/sbin/gnome-pty-helper`
to that same path below `/emul/irix`, SHA-256
`65bf5d62f33271292b48533e8093f511f47bc069091b6a0da58ad4fc17656612`.
Its source mode is 0755; the destination is root-owned 0555, not setuid.
The [resource ledger](../../lab/irix-terminal/resources.json) records the
read-only extraction and its existing libc dependency. No user settings or
accounting files are copied.

The maintained device setup supplies both master names and changes
`/emul/irix/dev/pts` to a symlink targeting `/../dev/pts`. NetBSD's explicit
native-root escape works through symlinks, so the original application's
post-setsid reopen reaches a native ptyfs vnode. The prior nullfs controlling
tty could panic in native revoke; winterm already uses a native handoff to
avoid that path. The handoff remains in place. Setup preserves an already
correct ptyfs mount and refuses an occupied old mount instead of forcing it.

## Evidence and reproduction

The [lab guide](../../lab/irix-terminal/README.md) describes the independent
fixtures, resource stage, module build and guest controls. Its original-IRIX
reference contains 240 records from the four ABI/trap forms under root and
UID/GID 1234. Successful reference records are compared byte-for-byte;
unsupported shapes have separately declared expectations. Native-peer
controls check descriptor counts after one-descriptor delivery, rejection
of two descriptors, and both data/rights output faults.

An earlier broad malformed-rights experiment panicked the original IRIX
reference kernel. The exact case was not captured, so no individual malformed
input is blamed. That disposable reference was stopped during its crash dump;
its serial log is retained. The later restricted reference run halted cleanly.
The source installation and published CHD were never modified.

An earlier native run completed its ABI suites but failed the 120-second
shutdown observation deadline; no final unmount/halt was captured. It is
retained as a diagnostic, not promoted or used as a seed. The ring reader
now saves the last observed kernel log and permits 300 seconds, with ten
seconds of uninterrupted guest execution between its stop/read/resume cycles.
A subsequent setup attempt refused to remount busy native ptyfs; preserving
an already correct mount fixes that startup failure. Neither failed attempt
is counted as an application pass.

The imported emulation passwd file still names `/tmp/xiri-home` for xiritest
and `/root` for root. The native account/session uses `/usr/people/xiritest`;
IRIX's root convention is `/`. Reconcile this generated emulation account
file in the next image migration without replacing native accounts or
importing the original password database.

## Application and session checks

The default GNOME Terminal launch runs the unchanged original IRIX `/bin/sh`.
Actual XTest input prints the home directory and a marker, writes a proof
file owned by xiritest, and displays the output in the terminal. HOME and cwd
are both `/usr/people/xiritest`. Typing `exit` removes the window and returns
status 0; the guard reports all four tracked processes absent. The
[default-shell PNG](images/2026-11-04-irix-terminal-default.png) shows command
output, but no shell prompt. Its trace records unsupported TCGETA/TCGETS and
foreground-group setup, including a failed open following ttyname. Complete
interactive IRIX termios/job-control support is still required.

A separate direct launch selects the already maintained native handoff:

```sh
/usr/freeware/bin/gnome-terminal --execute /usr/libexec/xiri-shell REPORT
```

`REPORT` must be a new writable report path for that run. This is a candidate
check, not a changed catalog default or an update to the current manual CHD.
The helper records UID/GID 1234, two supplementary groups, a native
`/dev/pts/2`, and equal PID/session/process-group/foreground-group IDs. Native
NetBSD `/bin/sh -i` shows a prompt and accepts commands. A real foreground job
observes 24×80, receives SIGWINCH during window resize and reports 29×102.
Typing `exit` closes the terminal with status 0 and all nine tracked processes
absent. A preceding `-e` attempt incorrectly put the command and report path
into one executable name; its ENOENT trace is retained and is not a handoff
failure. The full kdump text transfer failed framing, while the original raw
trace transferred successfully and establishes that exact attempted filename.

The `glynx` and `midnight-commander` wrappers now get through terminal startup
and exit quickly. They invoke `gnome-terminal -x lynx` and `gnome-terminal -x
mc`; both underlying programs are missing at their imported paths and native
aliases. Neither browser nor file-manager use is qualified. An initial retry
omitted the desktop PATH and failed to find GNOME Terminal itself; the recorded
valid retry uses the maintained session's PATH. Import the actual program,
dependency and resource trees before evaluating those applications.

PTY runtime regression checks log out, enter the separate netbsdtest account
and use its standard ctwm/UXTerm desktop. It remains UID 1236, HOME/cwd
`/home/netbsdtest`, a wheel member, with a 24×80 terminal on a 1280×1024 X
screen. Returning through xdm to xiritest restores the IRIX desktop and a
working 24×80 winterm in `/usr/people/xiritest`. Native FAM, rpcbind and xdm
retain their original service PIDs throughout.

The original Applications entry also passes a real double-click test. The
[screen capture](images/2026-11-04-irix-terminal-catalog.png) shows its original
shell command output and upright opened icon. FAM reports Executing/Exited;
the PID and window disappear after typed `exit`. This catalog route does not
capture an exit status. In a fixed 54×55 icon region, 927 pixels change while
running and the post-exit image matches all 2,970 original pixels exactly.
The separate direct default-shell run supplies the captured zero exit status.

## Qualified module checks

NetBSD `xiri` commit `4cf85855f1ee53cb7654b06449433cdef77da096` is byte-equivalent
to the [build inputs](../../lab/irix-terminal/build.json). The module SHA-256
is `b2ba5ba7ad5a3bae7ed6b4594daac9eddc21c653603d8500f6d16217925033e1`.
The build passes warnings-as-errors and the module import/relocation audit.
The qualified N64 kernel and boot wrapper are unchanged.

| Checks | Executions | Result |
| --- | ---: | --- |
| Socketpair, legacy rights and PTY master | 360 | 168 byte-for-byte IRIX comparisons and 192 declared subset-policy comparisons |
| Native SCM_RIGHTS peer | 32 | Single descriptor and rejection/copyout cleanup, all ABI/trap/identity combinations |
| Existing pathname Unix streams | 136 | Existing declared contracts unchanged |
| Existing IPv4 TCP and legacy recvmsg | 368 | 304 TCP and 64 receive cases, including independent native peers |

The [terminal ABI result](2026-11-04-irix-terminal-abi.json) and
[Unix regression result](2026-11-04-irix-terminal-unix.json) require the final
guest's clean halt and unchanged source CHD. Every fixture's bounded runner
records normal exit and an absent process group. The 37 maintained host tests
also pass. The main application/regression guest unmounted all filesystems
and halted cleanly; its unchanged source CHD is verified again afterward.

A second disposable clone cold-boots the installed runtime without the
harness's `--pty-setup` option. The boot service creates its readiness marker,
retains the native-root slave symlink, mounts ptyfs with gid 0/mode 0600 and
starts the full 1280×1024 desktop. Typed winterm input again confirms xiritest,
its expected HOME/cwd and 24×80 dimensions. This guest also unmounts cleanly
and halts, with the source CHD unchanged. The final host process check finds
no remaining IRIS or image-extraction QEMU instances.
