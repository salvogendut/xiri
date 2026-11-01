# Original installer helper paths and child completion

Follow-up: the [original signal reference](2026-11-01-irix-signal-reference.md)
now measures registration, frames, sigreturn and the predicted wait-any call.
NetBSD implementation remains pending; the capture below is unchanged.

Four native utility aliases let the original installer's target-directory
bootstrap **exit zero**, in both CI and ordinary IRIS execution. The parent
still leaves that child a zombie and reaches its 30-second watchdog. The
next runtime boundary is foreign SIGCHLD handling and child reaping.
Distribution reading and installation have not succeeded.

The [machine-readable report](2026-11-01-irix-installer-helpers.json) checks
three fresh clones of the stopped desktop-pipe seed on the unchanged
[time kernel](2026-11-01-irix-time.md), NetBSD source
`76de548ab644cb471f4c5b97ec89671c1d385c5b`. Vendor closure, xmahjongg inputs,
root environment and the original dry-run command are unchanged:

```sh
inst -n -M -r /emul/irix -f /cdrom/dist -c /cdrom/commands
```

| Run directory under `.work/irix-installer-helpers/runs` | Utility arrangement | Bootstrap exit | Parent |
| --- | --- | --- | --- |
| `ci-baseline-2u_ono9g` | Native layout | 1 | Zombie child; watchdog |
| `ci-native-6aojd6p5` | Four native aliases | 0 | Zombie child; watchdog |
| `ordinary-native-be2zjp_7` | Four native aliases | 0 | Zombie child; watchdog |

## What the helper actually does

The captured exec arguments are `/bin/sh -c <embedded script>`, followed by
another native `/bin/sh` reading its heredoc. The script has the `mkVarUsr`
marker and prepares the target's `usr`, `var`, installer-state and temporary
directories. Its environment contains `rbase=/emul/irix` and `HOME=/`.
It overrides the inherited PATH with
`/sbin:/usr/bin:/usr/bsd:/usr/sbin:/etc:/usr/etc:`, omitting native `/bin`.
Its full text stays in private traces; the report records its SHA256.

The baseline cannot find `ls` or `mkdir`. Its child exits1, and the parent
reads all 82 bytes of helper stderr through descriptor5, including the
missing-mkdir diagnostic and a misleading missing-target-directory error.
The parent does not forward those messages to its outer stderr before the
watchdog. Its outer stderr remains the same 107-byte SIGBUS/SIGSEGV handler
registration warnings; these are not captured fault deliveries.

The lab setup creates `/usr/bin/{ls,mkdir,mv,ln}` symlinks to the corresponding
native `/bin` tools. Repeated setup preserves exact existing links and
refuses to replace other files. Independent controls exercise creation,
listing with closed output descriptors, rename and relative symlink creation.
The unmodified bootstrap then executes these tools, creates target temporary
directories and `usr/tmp -> ../var/tmp`, and exits0 without helper stderr
reaching the parent.

This is deliberately narrow utility qualification. Both native `stat -qd`
calls fail because NetBSD does not recognize `-d`. The original script hides
the diagnostic and substitutes zero. The lab reaches its same-device branch,
but this is **not a qualified filesystem-device comparison**. The original
utility or a measured native adapter is still needed before installer support
can be claimed. A preliminary two-alias run also exposed missing `mv` and
`ln`; its private traces remain diagnostic evidence rather than the final
qualified setup.

## Why completion is the next interface

Four-second process snapshots show the exited shell as a zombie with the
installer as parent. The shell has its own process group/session. After the
child exits, the parent checks both pipe descriptors with fxstat and then
continues timed select calls with zero descriptors. Its gettimeofday calls
succeed. There is no foreign waitsys call and no `/cdrom/dist` name lookup.

The parent attempts `sigaction(18, ...)`, IRIX SIGCHLD, and receives ENOSYS89.
Inspection of the supplied `libinst.so` identifies its signal registration
and completion callback. Registration uses flags8 (`SA_SIGINFO`) and
`static_handler__Gi`; `signal_callback__15iIrixDispatcherGi` handles signal18
and calls `waitpid(-1, &status, 0x40)` repeatedly. The supplied libc translates
that to waitsys1170 with selector7 (`P_ALL`), id0, options0x43
(`WEXITED|WTRAPPED|WNOHANG`) and null rusage.

**That waitsys call is a static prediction, not an observed call in these
runs.** The current kernel only accepts a positive child PID, selector0 and
options drawn from 0x01/0x40/0x80; it would reject the predicted request.
It does not install foreign handlers or build their signal frames. The
historical licensed NetBSD IRIX implementation also documents the fourth
sigaction argument supplied by libc: its signal trampoline. The report pins
that source and the supplied binaries, checks the inspected instruction/GOT
sites, and retains only derived observations. Signal delivery cannot be
inferred solely from the absence of a processed-signal trace record.

The next implementation cycle should measure original IRIX sigaction,
trampoline/frame delivery and sigreturn for both supported ABIs, including
SIGCHLD, then qualify the required wait-any selector/options. Retry this same
installer fixture after those interfaces pass. Hardware queries, umask,
creat and complete software-distribution behavior remain other open work.

## Evidence and cleanup

The [lab instructions](../../lab/irix-installer-helpers/README.md) retain the
commands and qualification procedure. Full raw ktrace files supplement the
guest's text dump. A focused host decoder reads LP64 version-2 records;
the guest's o32 kdump otherwise splits native argument/return slots and does
not recognize the IRIX syscall table. Every direct foreign entry/return pair
agrees between the raw and text decoders. Truncated raw input is rejected.
The baseline contains 1,821 trace records; the CI and ordinary native-alias
runs contain 5,497 and 5,513. They respectively record 54, 43 and 46 successful
gettimeofday calls and 15, 14 and 14 zero-descriptor selects after child exit.

All **12 native execution controls** pass. Each guest also checks idempotent
account setup, UID1234 ownership/mode0700 and native-write/foreign-read access
to `/usr/people/xiritest`; foreign root retains `HOME=/`. Cleanup verifies
every traced PID is absent, including the helper's separate session, before
halting each guest. No graphical-login or new persistence claim is made.

The two initial diagnostic guests also halt cleanly. Three attempted launches
inside the toolbox failed before any guest started because `genisoimage` is
provided by the host; the accepted commands run the harness on the host.
Qualified kernels, emulator artifacts and detached worktrees are unchanged.
The final host process check finds no running IRIS instances.
The fresh IRIS upstream fetch still reports `4ad1b1d435dc115697433f091b10dfa8c48aa7ed`,
already contained in fork `xiri` at `045d692`; no merge or rebuild was needed.
