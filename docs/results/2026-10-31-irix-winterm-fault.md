# Original xwsh: null font object and blocked resource lookups

The original xwsh startup fault is in `tuFont::getWidth`: it receives a null
font object and loads a field at offset 16. The attempted call target is
`XmbTextEscapement`, but the fault occurs before that Xlib function is entered.
This follows the [font/locale/account experiment](2026-10-31-irix-winterm-resources.md).
Importing the requested SGI font into native X.org does not fix this client-side
locale/font initialization path.

The [structured report](2026-10-31-irix-winterm-fault.json) contains eight
captures: root and uid 1234, default and `fixed` font, CI and ordinary IRIS.
They use the unchanged SIOCNREAD kernel and original binaries. Native ptrace
controls and native terminal/font controls bracket each run. No terminal
window, PTY, child shell or interactive terminal behavior is qualified.

## Exact fault

| Observation | Value |
| --- | --- |
| SIGSEGV / code | 11 / SEGV_MAPERR (1) |
| Fault address / BadVAddr | `0x10` |
| Saved EPC | `0x10024394` |
| Actual fault instruction | `lw a0,16(a5)` at `0x10024398` |
| Null object register | a5, register 9, value zero |
| Call target in t9 | `0x0f60c370`, exported `XmbTextEscapement` |

The MIPS cause register has the branch-delay bit set: EPC points to the
preceding `jalr`, while the load in its delay slot faults. The supplied binary
exports the enclosing `getWidth__6tuFontGPCci` symbol. Original instruction
bytes, full registers and bounded memory captures remain private; public
reports contain locations, decoded behavior and hashes.

## Resource lookup evidence

Verified libc syscall breakpoints capture 1033 (`access`) and 1019 (`lseek`)
arguments immediately before execution, then their actual return registers.
Every observed call returns IRIX ENOSYS (89). Actual access pathnames include:

- `/usr/lib/X11/locale/C/XLC_LOCALE`
- `/usr/lib/X11/app-defaults/XWsh` and `/usr/lib/X11/C/app-defaults/XWsh`
- `/usr/lib/X11/{,C/}schemes/{Base,Myers}/BaseColorPalette`
- `$HOME/.desktop-xiri-indy/schemes/{Base,Myers}/BaseColorPalette`
- `$HOME/.Xauthority`

The C locale and app-defaults files are already staged readably under
`/emul/irix`. Their presence cannot make an unimplemented access call succeed.
This establishes a concrete compatibility gap on the failed initialization
path; it does not yet prove that implementing access alone will produce a
working font object or terminal. Scheme file presence and necessity are still
to inventory. The [resource checklist](../IRIX-RESOURCES.md) and
[ledger](../../lab/irix-desktop/resource-ledger.json) now retain these observed
paths separately from confirmed requirements.

The captured seeks have negative offsets and SEEK_CUR. Their return address is
`0x0fa57690`, inside libc `fflush` at offset `0x274`; these are buffered-stream
position adjustments. They remain unsupported, but this evidence does not
establish them as the cause of the null font. The next adapter work should
measure original access behavior and namespace/credential rules, then qualify
seek semantics separately where required. Locale modules and later terminal
process behavior remain open.

## Controls and harness corrections

The native o32 tracer uses the pinned LP64 kernel's 38 × 64-bit register
layout with a guard. A labelled native null load validates SIGSEGV, fault PC
and address; native entry/exit checks run under both identities. Native xterm
opens the imported SGI Screen font before and after the vendor captures.
Software breakpoints use NetBSD MIPS BREAK code 514, verify original stub
instructions and restore each instruction before it executes. Neither vendor
files nor kernel code are modified.

The tracer must request PT_TRACE_ME **before** changing the child's uid:
NetBSD rejects that request after the credential change. Earlier root captures
were useful diagnostics, but those runs stopped at uid-1234 tracing setup and
are excluded from the final paired qualification. Other excluded setup runs
caught boot-time `/tmp` cleanup of staged fonts and a missing explicit native
window title. One ordinary-seed attempt stopped at a native X_OpenFont
BadAlloc control failure, before vendor captures; it is excluded as well.
All excluded guests shut down cleanly. The final harness stages
fonts afresh and verifies their hashes on every boot.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-winterm-fault.py --lookups \
  --seed-directory .work/irix-x11-fonts/runs/ci-_6m3l41w
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-winterm-fault.py --lookups \
  --mode ordinary --seed-directory .work/irix-x11-fonts/runs/ordinary-2fz6bgec
```

The standalone capture without `--lookups` also records the fault; the final
comparison uses the checked lookup trace. Raw observations, original resource
bytes and guest images stay in ignored `.work`. No leaked IRIX source is used.

Accepted captures are `.work/irix-winterm-fault/runs/ci-hn9jf6ae` and
`.work/irix-winterm-fault/runs/ordinary-q66ktby1`. Both use the same stopped CI
font/locale seed. The final ordinary run additionally verifies all staged font
hashes and loads the requested font with `xlsfonts -ll` before tracing. Both
runs finish with passing native controls and clean shutdown. The final host
process audit finds no `iris` or `iris-ci` process.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/qualify-irix-winterm-fault.py \
  .work/irix-winterm-fault/runs/ci-hn9jf6ae \
  .work/irix-winterm-fault/runs/ordinary-q66ktby1 \
  --output docs/results/2026-10-31-irix-winterm-fault.json
```
