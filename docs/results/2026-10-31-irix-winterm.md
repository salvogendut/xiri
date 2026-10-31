# Original IRIX winterm opening attempts

Original n32 `xwsh`, the terminal selected by this installation's `winterm`
launcher, loads its libraries and reaches the native X.org server as root.
It then receives SIGSEGV during startup. No terminal window is present in the
captured trees or frames. This gets beyond xclock's earlier libXmu mapping
boundary, but does not establish a working original terminal or shell.

The [lab](../../lab/irix-winterm/README.md) and
[inventory](../../lab/irix-winterm/manifest.json) retain the launch procedure,
static dependency metadata and input hashes. The kernel is unchanged at
`355e0ca310039839b426e66d00744edab5cd5608`; IRIS remains
`9df1df14334838a989253efefe26f0547e6da592`. No leaked IRIX source is used; the installed launcher and resources come from
the supplied image.

## Launcher, terminal and shell

The supplied `/usr/sbin/winterm` is an unchanged shell script that selects
`xwsh -name winterm` by default. The actual terminal executable is
`/usr/sbin/xwsh`. Its static closure does not contain libXmu. The inventory
also includes the launcher's `gettxt` helper and original XWsh/IWsh resources;
native IRIX `ldd` and delayed library loading remain unqualified.

The experiment runs the script under native NetBSD `/bin/sh`, with an explicit
WINTERM selecting the original xwsh. Native shell utilities remain in PATH;
the original `gettxt` is staged ahead of them. This is a mixed environment,
not an original-IRIX-shell test. The helper fails to execute in all launcher
attempts. Its ELF data segment has 4 KiB alignment, outside the currently
qualified 8 KiB loading subset; the exact exec rejection is not diagnosed here.

The guest contains `/bin/sh`, `/bin/ksh` and `/bin/csh`; root's configured shell
is `/bin/sh`. NetBSD documents [sh](https://man.netbsd.org/sh.1) as its standard
Bourne-style interpreter and [ksh](https://man.netbsd.org/ksh.1) as its
public-domain Korn shell. The original terminal can eventually host a native
shell, once its process and pseudo-terminal interfaces work. No shell selection
or host account was changed by these tests.

## Observations

The [machine-readable report](2026-10-31-irix-winterm.json) verifies 16 attempts:
direct xwsh and winterm, default font and `-fn fixed`, root and uid 1234,
in CI and ordinary IRIS execution.

| Attempt | Parent result | X connection and frame |
| --- | --- | --- |
| Direct xwsh, root, either font | SIGSEGV; not a parent timeout | One socket/connect; empty sampled window tree |
| Direct xwsh, uid 1234, either font | Exit 255, account lookup failure | No socket/connect; empty tree |
| winterm launcher, root, either font | Native shell exits 0 after asynchronous launch; gettxt exec error | Child reaches X; empty tree |
| winterm launcher, uid 1234, either font | Native shell exits 0; gettxt exec error | No child X connection; empty tree |

All 16 root XWD images have SHA-256
`7d6c819d66a7d48c67d94a281e4910478db108630bac8d8da98a88653a4a7f6b`,
the empty server frame. A script's exit zero is not counted as terminal success:
winterm backgrounds its terminal, and its captured stderr can end before all
child diagnostics are emitted. The inherited syscall trace and separate window
sample establish the observed child boundary.

Direct root launches report unsupported X locale and a font-open failure before
the crash. Selecting `fixed` changes the requested font but does not remove the
warning or crash. These messages do not prove the crash's cause. The synthetic
uid 1234 has no login database entry in this seed; xwsh rejects that identity
before opening X. That is a distinct session-data prerequisite.

Four native NetBSD xterm controls, root before and uid 1234 after each workload,
are viewable on the same Xvfb and run `/bin/sh`. Their 15-second termination is
intentional. Both accepted guests shut down cleanly. The earlier CI and ordinary
diagnostics used a newly copied environment file that uid 1234 could not read;
their final native controls failed. They are excluded and were also shut down.
The corrected harness explicitly installs readable resources/environment files
and executable libraries/programs, independent of the guest's umask.

The [font/resource follow-up](2026-10-31-irix-winterm-resources.md) now proves
native import of the selected SGI fonts and removes the uid account barrier
with explicit fixtures, but xwsh still reaches SIGSEGV. Font availability, locale
initialization, account lookup, a fault location, pseudo-terminals and child
execution remain separate questions. No interactive terminal or original
desktop-session compatibility is claimed by this opening experiment.
