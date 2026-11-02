# Original IRIX shell and Icon Catalog launch

The unmodified IRIX 6.5.22m `/bin/sh` now executes on the LP64 NetBSD
kernel. Icon Catalog's original Freeware action launches xmahjongg on a
double-click; two launches produce distinct processes and game windows.
The ordinary winterm default remains the existing native shell handoff.

## Kernel contract

NetBSD `xiri` commit `849755450135c6734bb61c4973d687d0c8060739` admits
static n32 MIPS III executables with the measured four-header layout:
RX and RW loads, PT_MIPS_OPTIONS and PT_MIPS_REGINFO, flags `0x20000020`,
and no interpreter. This is layout validation, not a filename/hash exception.
Existing segment size, address, alignment, extent, protection and entry checks
remain in force. Metadata must point into file-backed image bytes. Native
NetBSD branding, marked static probes and dynamic vendor admission retain
their separate paths. The o32 kernel continues to reject n32 executables.

The source image's `/bin/sh` resolves to `/sbin/sh`; the import already
contains those bytes as `/emul/irix/bin/sh`. No vendor executable was patched
or replaced. Its SHA-256 is
`ab6dd5b0585aec1f0fc7147d14fb68cd81986c9a5996315d9d5f16fd4e570c57`.

The chdir adapter uses native pathname lookup, credentials and cwd ownership.
Measured syscall 1039 uses zero to query the process group and any nonzero
value for System V setpgrp. The latter creates a native session for a child
that is not already a group leader; repeated leader calls return its group.
SGI_GETSID (65) delegates to the native session query. Original libc wrapper
inspection and independent probes establish these interfaces. This is not
the multi-selector pgrpsys interface used by some other Unix systems.

## Qualification

The [machine-readable record](2026-11-02-irix-vendor-shell.json) records
**772 checks**, including 32 before/after native/vendor controls:

| Kernel and execution | Checks |
| --- | ---: |
| LP64, CI | 304 |
| LP64, ordinary execution | 304 |
| o32, CI | 164 |

The fixtures cover 38 static/native admission cases, directory errors and
preservation of cwd, process-group/session relationships, both ABIs and
direct/indirect dispatch, and dynamic-loader regressions. Root and UID 1234
both run the shell cases: quoting, arguments, environment, exit statuses,
redirection, substitution, subshells, pipes, background/wait, cd, PATH lookup,
nested shells, exec replacement and scripts. Independent original IRIX
provides 78 executions: 36 shell, 40 process and two valid static controls.
Every final guest halts cleanly. Full interactive job control and signal
semantics remain outside this bounded qualification. An attempted nested
winterm test did not prove original-shell interaction: its identity check
reported the existing native shell PID 212. A separate forced-interactive
pipe test entered the original prompt and processed its supplied input,
but does not qualify controlling-terminal behavior. Neither is included in
the 772 checks.

The first LP64 run exposed a real namespace setup omission: with O_CREAT,
`/dev/null` selected the existing `/emul/irix/dev` parent. Root could create
a regular file there, and ordinary-user redirection then failed. The native
PTY setup now supplies a character node with major/minor values obtained
from NetBSD's actual `/dev/null`, mode 0666. It validates an existing node;
it does not import IRIX device numbers or silently remove unexpected files.
The corrected shell runs match the reference, including redirected errors.

An initial o32 regression run incorrectly reused an interpreter fixture
that expects an 8 KiB auxiliary-vector page size. Final o32 qualification
uses the established 4 KiB fixtures. Initial runs and their failures remain
under `.work/irix-vendor-shell`; only the final clean builds enter the totals.

Concurrent Newport development changed the shared checkout during this
cycle. Final builds use a separate clean checkout of the committed `xiri`
revision, with empty source patches. The shared feature work is preserved.
The [lab](../../lab/irix-vendor-shell/README.md) records build/reproduction
commands and exact kernel/emulator pins.

## Desktop retry

The ordinary graphical diagnostic guest is
`.work/irix-vendor-shell/bringup-tk_33_ep`. It uses the initial LP64 build
containing the exact committed compatibility-file patch, before the clean
builds above. Its native kernel SHA-256 is
`1f95f7b74f298d3b35f0e4367c56cb324fec7d0b4988cf0577a55bf834a28825`.
The final kernel additionally includes the already integrated GR2 console
fix; its automated ordinary-execution matrix passes separately.

After stopping the automatically started game, a recognized double-click
forks the catalog child. A trace confirms successful setpgrp, chdir and exec
of the original shell, followed by execution of the catalog target. An
initial coordinate selected grok; it opens its own first-run configuration
dialog. Correcting the target to xmahjongg produces PID 1825 and a
1006×614 `XMahjongg` window. After stopping it, a second double-click
produces PID 4569. The [PNG screenshot](images/2026-11-02-catalog-shell-xmahjongg.png)
is a native Xorg XWD capture converted to PNG. Emulator monitor captures
were black in this diagnostic run and are not used as graphical evidence.

Launching is demonstrated. A sustained opened-shape change is not yet
qualified; the existing FTR already supplies distinct opened/closed artwork.
The original `/usr/lib/desktop/launcheffect` and `waitmap` are present on the
source installation. Their [inventory](../../lab/irix-vendor-shell/launch-helpers.json)
records hashes and destination paths. Neither helper was installed for these
launch tests; their role in transient feedback remains a follow-up.

The preserved `20261102-icons` manual CHD has not been repackaged. It still
has the older kernel and session setup. GIMP's signal-registration failure,
xosview's statistics interfaces, full terminal lifecycle/job control and
desktop persistence remain separate work.

The desktop diagnostic also halted cleanly after its supervisor removed the
remaining clients and services. All emulator instances owned by this cycle
were stopped; unrelated user sessions are left alone.

The subsequent [shell-image qualification](2026-11-02-irix-shell-image.md)
packages these changes in a new manual CHD and repeats the catalog launch
from that disk. The older icons CHD remains preserved.
