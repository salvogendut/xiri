# Winterm passes locale/font initialization and reaches PTY setup

Original n32 `xwsh` now checks and reads the staged C locale database and XWsh
app-defaults in eight starts: both execution modes, both identities, and
default/`fixed` font requests. Each reads 763 locale bytes and 12,699
app-default bytes. The earlier unsupported-locale warning, font warning and
null-`tuFont` SIGSEGV disappear. It exits later with status 255 and:

```
/emul/irix/usr/sbin/xwsh: Invalid argument: can't start command
```

This is startup progress, not a working terminal. No xwsh window or native
shell is qualified. The unchanged `winterm` launcher also retains its separate
`gettxt` executable-layout limitation.

The [access adapter](2026-10-31-irix-access.md) is the only functional kernel
change since the relocation checkpoint. Both default and `fixed` launches
use the existing readable original resources, synthetic test account entries,
explicit HOME/SHELL environment and native X.org Xvfb. The observer checks
native entry/fault tracing and a native terminal with the imported 15-pixel
Screen face before and after the original applications. The
[machine-readable result](2026-10-31-irix-winterm-access.json) records each
identity/mode, successful resource checks, bytes read and private trace hashes.

## New boundary

The final attempted `open` passes pathname address `0x0fb488a8`, flags `6`,
and returns IRIX `EINVAL` (22). That address resolves to `/dev/ptc` in the
pinned original libc's file-backed segment. The current open adapter rejects
flag bit `0x4` before pathname lookup. The historical BSD-licensed IRIX header
at NetBSD revision `5aca2679d78276864d2980a08314887b2058fb2c` identifies this as
`IRIX_FNDELAY`; the accepted `IRIX_FNONBLOCK` bit is separately `0x80`.

Private disassembly of original libc `_getpty` confirms that it opens this
path. Its later helper inspects descriptor device metadata and recognizes
particular major/minor values. Simply aliasing a native PTY device therefore
needs more investigation: allocation, identity reporting, ownership, slave
naming and terminal controls must be measured together. The new boundary is
PTY allocation and native shell startup, followed by input and cleanup.

`lseek` still returns `ENOSYS`, including buffered-stream adjustments. It no
longer prevents the observed locale/defaults startup path. Signal-related
calls also remain unsupported; their terminal lifecycle effects are not yet
qualified. These gaps should be revisited when the PTY path reaches them.

## Resource findings

- `C/XLC_LOCALE` and `app-defaults/XWsh` are consumed after successful access
  checks. Additional locales, delayed modules and IWsh remain unqualified.
- Base/Myers palette candidates return `ENOENT` in the guest; xwsh continues
  to PTY setup. Appearance and image-file inventory remain open.
- The error path probes `uxsyserr`, its `C/Xopen` variant and `uxsyserr.cat`
  under `/usr/lib/locale`. These are recorded in the
  [resource ledger](../../lab/irix-desktop/resource-ledger.json); the fallback
  English diagnostic works without them.
- PTY device nodes and process/session state must come from NetBSD support,
  rather than importing original device nodes or account state.

## Controls and excluded attempts

An initial candidate omitted the explicit dispatcher selection for trap
1033. Its two captures still returned `ENOSYS`; that run was stopped and
halted cleanly before qualification. A corrected-kernel attempt then failed
its native `X_OpenFont` control with `BadAlloc`, before any original xwsh
capture, and also halted cleanly.

The accepted control explicitly selects the verified normal Screen face for
both native xterm regular and bold slots (`-fn` and `-fb`). It does not claim
that every imported face or automatic bold selection works. The original
xwsh launches retain their default or explicitly requested `fixed` font.
The earlier native failure remains an open font-control finding.

Run the observer from the host, using the stopped CI font/locale seed:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-winterm-access.py \
  --seed-directory .work/irix-x11-fonts/runs/ci-_6m3l41w --mode ci --lookups
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-winterm-access.py \
  --seed-directory .work/irix-x11-fonts/runs/ci-_6m3l41w --mode ordinary --lookups
```

Each guest is disposable and halted after its observations. Raw traces,
frames, original binaries and disassembly remain in ignored `.work`.
The agreed order is usable winterm first, then evaluation of original 4Dwm
and the broader desktop session. Clock timekeeping follows those priorities.

Accepted runs: `.work/irix-winterm-access/runs/ci-ogysv6ji` and
`ordinary-zo1q35q9`. Both halted cleanly. Qualification:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/qualify-irix-winterm-access.py \
  .work/irix-winterm-access/runs/ci-ogysv6ji \
  .work/irix-winterm-access/runs/ordinary-zo1q35q9 \
  --output docs/results/2026-10-31-irix-winterm-access.json
```
