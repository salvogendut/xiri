# Original IRIX winterm / xwsh

Follow-up: the startup fault is a null font object in tuFont::getWidth. Actual access calls for staged locale/defaults return ENOSYS. See the [new result](../../docs/results/2026-10-31-irix-winterm-fault.md).

Results: the 16 opening attempts are recorded; root xwsh reaches X then crashes, while the initial numerical uid lacks an account entry. Four native terminal controls pass. See the [run record](../../docs/results/2026-10-31-irix-winterm.md).

The supplied installation's `/usr/sbin/winterm` is a shell launcher, with
`#!/bin/sh`; its default terminal command is `xwsh -name winterm`.
The actual terminal executable is the original n32 `/usr/sbin/xwsh`.
The [inventory](manifest.json) pins both, the `gettxt` message helper, their
static library closure, app-defaults and supplied manual metadata. Vendor
bytes remain private under ignored `.work/irix-winterm/root`.

The static xwsh closure does not include libXmu. Its dependency selection has
not been checked against native IRIX `ldd`; startup traces establish only
the paths reached in this experiment. Delayed libraries, terminal resources
and services are not fully inventoried.

## Reproduce

Use the host libguestfs installation to inventory the original image with
`--ro` and `ro,norecovery`:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/inventory-irix-winterm.py
```

Review the generated private manifest before replacing the public metadata.
Run the bounded opening attempts on disposable copies of the qualified
SIOCNREAD seed:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-winterm.py \
  --seed-directory .work/irix-siocnread/runs/lp64-ci-d2asxkow --font fixed
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-winterm.py \
  --seed-directory .work/irix-siocnread/runs/lp64-ci-d2asxkow --mode ordinary --font fixed
```

The harness verifies the kernel/emulator and staged vendor checksums, then
tries xwsh directly and the unchanged winterm script as root and uid 1234.
With `--font fixed`, each attempt runs both with the default font and with
`-fn fixed`. Libraries/executables are installed mode 0555, resource and
environment files mode 0444, and directories mode 0755, independent of umask.
The script runs under native NetBSD `/bin/sh`, with an explicit `WINTERM`
selecting the original xwsh and `PATH` selecting the supplied `gettxt` helper.
Native `basename`, `expr` and shell behavior are therefore part of this test
environment; this is not an original-IRIX-shell qualification.

The parent bounds direct execution at 15 seconds. The winterm script starts
its terminal asynchronously, so its exit status alone cannot establish the
terminal's success. Separate window trees, frames, inherited syscall traces
and process listings retain that distinction. Any remaining xwsh process is
stopped after its observation, and each guest is shut down in `finally`.
Stay within four concurrent IRIS guests across all experiments.

A native NetBSD xterm running `/bin/sh` brackets each workload, as root before
and uid 1234 afterward. It must be viewable on the same guest Xvfb. The test
captures frames before the bounded parent exits and transfers them afterward.
It does not send terminal input or qualify an interactive original shell.

## Shell boundary

NetBSD provides its standard Bourne-style [`/bin/sh`](https://man.netbsd.org/sh.1),
the public-domain Korn shell [`/bin/ksh`](https://man.netbsd.org/ksh.1), and
`/bin/csh`. The harness records their presence and the guest root account's
configured shell. A native shell can be the eventual child of the original
IRIX terminal. That still requires working foreign process creation/exec,
pseudo-terminal allocation and terminal ioctls; a shell binary's presence
does not establish those interfaces.

## Recheck saved evidence

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/qualify-irix-winterm.py \
  .work/irix-winterm/runs/ci-x0hiy_qk \
  .work/irix-winterm/runs/ordinary-6099szjn \
  --output docs/results/2026-10-31-irix-winterm.json
```

The [font/resource follow-up](../../docs/results/2026-10-31-irix-winterm-resources.md)
adds original Screen fonts, C/ISO8859-1 data and synthetic foreign account
records. Native font controls pass; the original terminal startup fault remains.

The [fault/lookup harness](../../scripts/probe-irix-winterm-fault.py) reuses a
stopped font/locale seed, stages the imported fonts afresh, and captures the
null-font crash with checked native ptrace controls. With `--lookups`, it also
records actual access pathnames and seek arguments. See the
[diagnosis and paired qualification](../../docs/results/2026-10-31-irix-winterm-fault.md).
