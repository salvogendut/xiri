# Importing original IRIX fonts and locale resources

Follow-up: see the [next checkpoint](2026-10-31-irix-winterm-fault.md). This report preserves the earlier observed boundary.

Native NetBSD X.org accepts the selected original SGI Screen PCF fonts.
`mkfontdir` indexes all 22 files, and native xterm renders the exact 15-pixel
medium Screen font as root and uid 1234 in both IRIS execution modes.
Original xwsh still crashes during startup, including after the supplied
C/ISO8859-1 locale data is staged. The font warning therefore cannot be treated
as proof that the X server lacks the requested font.

The [lab](../../lab/irix-x11-fonts/README.md),
[resource manifest](../../lab/irix-x11-fonts/manifest.json) and
[machine-readable report](2026-10-31-irix-winterm-resources.json) retain the
commands, hashes, native controls, attempts and shutdown evidence. The
[central checklist](../IRIX-RESOURCES.md) records what must be retained from
the image and what still needs investigation. Kernel/emulator revisions remain
the same as the preceding [winterm baseline](2026-10-31-irix-winterm.md).

## Font import

The image contains 22 SGI Screen fonts totaling 118,634 bytes, in PCF and
compressed PCF formats. `Scr15.pcf` is an MSB-first portable bitmap font and
matches xwsh's default request through this XLFD:

```text
-sgi-screen-medium-r-normal--15-150-72-72-m-80-iso8859-1
```

The exact name is absent from the initial native server. Each guest installs
the selected original bytes into a private font directory, generates a new
index with native [mkfontdir](https://man.netbsd.org/mkfontdir.1), and prepends
the directory to Xvfb's font path using [xset](https://man.netbsd.org/xset.1).
Native `xlsfonts -ll` then returns its metrics and properties. A native xterm
explicitly selecting that font opens without stderr and runs NetBSD `/bin/sh`.
Four such controls bracket the experiments, under both identities and modes.

This proves indexing of the selected family and rendering of the requested
15-pixel face. It does not render every face, qualify every IRIX font format,
or establish an entire SGI theme. Original files remain private under `.work`;
the public manifest contains only metadata. The host's font configuration is
unchanged.

## Account and locale separation

The preceding bare uid 1234 had no account entry and xwsh exited before X.
This experiment provides synthetic root/test-user passwd and group files in
`/emul/irix/etc`, with hashes separate from vendor resources. The uid 1234
attempts now open X and reach the same later startup fault as root. These
fixtures establish the tested account lookup; they do not alter host users or
implement a complete login/name-service environment.

The `fonts` stage imports only the server fonts and those account fixtures.
The `fonts-locale` stage additionally supplies the original alias/directory
files and C/ISO8859-1 XLC_LOCALE, XI18N_OBJS and Compose data in the foreign
namespace. Both stages test default-font and `fixed` launches as root and
uid 1234 in CI and ordinary execution: 16 direct xwsh attempts.

Every attempt makes one socket/connect pair, reports X locale and font-open
failures, and receives SIGSEGV without a parent timeout. All sampled trees
are empty and all frames match the empty-server hash
`7d6c819d66a7d48c67d94a281e4910478db108630bac8d8da98a88653a4a7f6b`.
The native terminal controls pass before and after, and both guests halt
cleanly. Imported fonts and additional locale files do not resolve the
observed foreign-client failure.

## Next boundary

The traces still contain ENOSYS for `access` (1033) and `lseek` (1019), among
other unsupported calls. Their names are confirmed by the BSD-licensed
historical NetBSD IRIX table at `5aca2679d78276864d2980a08314887b2058fb2c`.
The final uid 1234 trace includes the synthetic passwd lookup but no named
lookup of C/XLC_LOCALE. This is a useful lead for following the client resource
lookup, not proof that either syscall alone causes the crash.

The next diagnostic should capture the fault location and the relevant
file-access/seek arguments, then measure any required interface on original
IRIX before implementing it. External locale/input-method modules, SGI helper
execution, pseudo-terminal ioctls, process creation and child-shell execution
remain unqualified. A working native terminal with the imported SGI font is
not counted as a successful original winterm window.
