# Original IRIX shell: interactive terminal support

The unchanged IRIX `/bin/sh` now recognizes its terminal inside original
GNOME Terminal on NetBSD. It shows a `$` prompt, reports interactive flag
`i`, starts commands in `/usr/people/xiritest`, survives Ctrl-C, delivers
foreground resize notifications and closes normally on typed `exit`.
The [PNG](images/2026-11-04-irix-termios-shell.png) shows the real command
session. No shell override or additional vendor payload is used.

This follows the [terminal startup cycle](2026-11-04-irix-terminal.md).
The new code belongs to `compat_irix_o32.kmod`, with no new core-kernel hook
or emulator change. The manual GIMP CHD is unchanged; this result comes from
a disposable guest using the newer module and the previously staged runtime.
GNOME preference saving, general STREAMS and broader stop/resume job control
remain open.

## Cause and implementation

The earlier shell could read commands but did not recognize stdin as a tty:
IRIX TCGETA/TCGETS returned ENOSYS. The original kernel's terminal interfaces
were measured with independent freestanding o32/n32 probes, in direct and
indirect syscall forms, as root and UID/GID 1234. The supplied IRIX 6.5.22m
headers were inspected read-only for constants/layout; their
[hash ledger](../../lab/irix-terminal/termios-headers.json) is retained without
redistributing the headers. No leaked source is used.

The module translates all four measured termio/termios families, with get,
immediate set, drain-before-set and flush-before-set selectors. Both ABIs use
four 32-bit flag words and 23 byte controls. Legacy structures occupy 40
bytes; modern structures add output/input rates and occupy 48. Termio has an
additional line byte, which the measured PTY driver ignores on input and
reports as 1 on output.

The adapter maps supported flags, echo/canonical/raw modes, signal controls,
software flow control, rates and raw VMIN/VTIME onto NetBSD's PTY discipline.
Foreign disabled controls are zero; native disabled controls use 255. Native
bits without a foreign representation are preserved. Unsupported foreign
flags or reserved nonzero controls are rejected instead of silently accepted.
Only actual native PTY master/slave vnodes enter this translation; foreign
ioctl direction/size fields are never forwarded as native commands.

Opening a PTY slave after setsid now acquires a controlling terminal when the
caller is a session leader without one and did not request O_NOCTTY. Native
TIOCSCTTY performs the ownership checks. Session-ID and foreground-group
queries/setters are translated separately. The selector `0x7416` is TIOCGSID,
as confirmed by the original-system probe and the public
[NetBSD historical SVR4 ioctl definitions](https://github.com/NetBSD/src/blob/netbsd-5/sys/compat/svr4/svr4_ttold.h).
It is not a foreground-group setter. The old GNOME trace issued this query
on inherited stdin before duplicating the PTY slave onto that descriptor.

Three comparison policies are explicit: undefined termios padding is zeroed;
modern flags omit IRIX's retained obsolete baud-code bits while explicit
rates remain compared; and an absent foreground group returns native EPERM
where IRIX reports EINVAL. Other compared flag/control/result bytes must match.
The implementation remains restricted to PTYs: other device classes, socket
ioctl error parity, serial hardware and arbitrary line disciplines are not
qualified. Drain/flush selectors are exercised without queued data; detailed
queue-drain timing still needs separate checks.

## Paired ABI evidence

The [lab guide](../../lab/irix-terminal/README.md) describes the record format,
exact case list, archives and commands. Identical ELF bytes run on both
systems. The original reference halts cleanly after 864 terminal-attribute
and 64 session observations. The old candidate reproduces ENOSYS in 16
baseline calls. An attribute-only intermediate module passes its matrix;
the final module adds session acquisition and passes both matrices.

The disposable reference account and PTY-node permissions are prepared for
the non-root fixtures; these changes stay in that clone. Early probes omitted
the required master unlock and returned EACCES. They were corrected before
collecting the accepted matrix. A separate archive command exceeded IRIX's
argument-list limit after all probes had exited successfully; archiving the
whole directory retained those results without rerunning or discarding cases.

The attribute cases include all 16 selectors, master/slave behavior, ordinary
files, null devices, invalid descriptors, null/high/unaligned pointers,
read-only pages, page-boundary faults, error precedence, flag/control changes
and unchanged settings after failed setters. The session cases include
acquisition, O_NOCTTY, a non-leader, master/file/invalid descriptors, output
faults and absent foreground groups. Their native runners require normal
exit, empty stderr and an absent process group.

The compact [attribute reference](../../lab/irix-terminal/termios-reference.json)
and [session reference](../../lab/irix-terminal/tty-session-reference.json)
retain measured values and archive hashes. Raw local archives preserve the
complete setup/result records. Final qualifier output also requires the
native guest's clean halt and an unchanged source CHD.

## Original-shell interaction

The actual GNOME window shows `FLAGS=is`, HOME and cwd
`/usr/people/xiritest`, and shell name `sh`. A native foreground control
launched by that original shell reports foreground membership and receives
SIGINT from the emulator's Ctrl-C key event. A fresh command afterward
creates the expected marker. A second native foreground control observes
24×80, receives SIGWINCH when the window changes size, and reports 29×102.
The shell then accepts another command and typed `exit`.

The application guard records exit 0, no terminating signal, all six tracked
processes absent and no forced stop. X remains ready afterward. The controls
test real kernel signal delivery to foreground children; they do not establish
full foreign stop/resume job-control parity.

Earlier interactive attempts stopped at overly strict process-name checks
before issuing Ctrl-C. A focused trace then showed the native sleep child
before the key event and its absence afterward. An echo following sleep on
the same compound input line is not a valid survival test: an interactive
shell may discard the remainder of that interrupted line. The final check
uses a foreground signal reporter and a fresh subsequent command. The earlier
attempts remain diagnostics, not normal-exit passes.

GNOME still reports an unavailable shared-memory transport and uses its
fallback, cannot open help topics, and fails to write `.gnome/Terminal` with
ENOSYS. Preference persistence remains a separate follow-up. The `glynx` and
Midnight Commander launchers still lack their actual `lynx`/`mc` payloads;
this terminal result does not qualify those applications.

## Catalog and login regressions

Double-clicking GNOME Terminal on Applications launches it as UID/GID 1234.
Real keyboard input reports `FLAGS=is`, writes a new proof owned by that
user and exits normally. This route inherits the desktop's custom
`xiritest@xiri$` prompt; the direct test uses the shell's default `$` prompt.
The [catalog PNG](images/2026-11-04-irix-termios-catalog.png) shows the opened
icon. In a fixed 54×55 region, 927 pixels change while running and all 2,970
pixels return to their initial values after exit. FAM reports Executing and
Exited; both PID and window disappear. The catalog route does not capture an
exit status; the separate guarded direct launch supplies that check.

Logout returns to xdm with every tracked session descendant absent. The
separate netbsdtest login runs standard ctwm/UXTerm as UID 1236, in
`/home/netbsdtest`, with wheel membership and a 24×80 terminal. Logging back
in as xiritest restores the original desktop and a working winterm in
`/usr/people/xiritest`. Both X sessions use 1280×1024. FAM, rpcbind and xdm
keep their service PIDs through this sequence. The
[native-session PNG](images/2026-11-04-irix-termios-native-login.png) and
[IRIX relogin PNG](images/2026-11-04-irix-termios-relogin.png) retain the result.

## Validation and artifacts

| Checks | Executions | Result |
| --- | ---: | --- |
| New terminal attributes | 864 | Paired original-IRIX comparisons with the declared padding/baud policies |
| New controlling-terminal/session queries | 64 | Paired comparisons with the declared absent-group errno policy |
| Existing socketpair, rights and PTY-master cases | 360 | Existing declared contracts unchanged |
| Native descriptor-transfer peers | 32 | Delivery, rejection and descriptor cleanup unchanged |
| Existing pathname Unix streams | 136 | Existing declared contracts unchanged |
| Existing IPv4 TCP and receive cases | 368 | Existing declared contracts and native peer data unchanged |

These are 1,824 ABI/regression executions, separate from the application and
login checks. All 37 maintained host tests also pass. The module builds with
warnings as errors and passes its symbol/relocation audit. Rebuilding the
terminal observer with the current builder reproduces all four tested ELF
files byte for byte.

The [build record](../../lab/irix-terminal/termios-build.json) identifies module
SHA-256 `e7d8a4a5e937e304ff7237add2ba2f8de7ba389e57fdb1bc6ffd5fc0db8a9910`.
The retained core kernel is
`ed97268e4c1db1c91a8973d16c1e31555816c2a29c220b29b9095eadf3b2ae04`, and
the boot wrapper is
`260b253f579ca46a50b83e367f95600b54c86756c47f5d9e0f9391251bfd7122`.
The lab remains on the manual bundle's pinned emulator, separate from the
current IRIS integration branch.

NetBSD `xiri` commit `89b8a71e1e4bf8a6e7d3ef3962b40adca08c1e2a` is
pushed and matches every recorded module source hash. IRIS upstream was
fetched again at `3bcde9f702f0b52fdb296eeda4fe10b26555f3da`, already merged
into `xiri` `bd67e65ff159748635dd484adf7fac94a591f84b`; no new emulator
changes required integration. See the [fork record](../FORKS.md).

The [combined evidence](2026-11-04-irix-termios.json),
[attribute qualification](2026-11-04-irix-termios-abi.json),
[session qualification](2026-11-04-irix-termios-sessions.json),
[terminal regression](2026-11-04-irix-termios-terminal-regression.json),
[Unix regression](2026-11-04-irix-termios-unix.json) and
[IPv4 regression](2026-11-04-irix-termios-ipv4.json) retain the exact result
and artifact identities. The final guest verifies the installed module and
core hashes again, unmounts cleanly and halts with its source CHD unchanged.
The baseline, attribute-only candidate and original-IRIX reference also halt
cleanly. The final host process check finds no IRIS or extraction QEMU
instances left running.
