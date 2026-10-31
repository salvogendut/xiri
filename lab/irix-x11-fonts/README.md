# Original IRIX fonts and locale data

Follow-up: the null-font fault and unsupported resource-access calls are now captured. Imported font availability alone does not resolve this client initialization path. See the [new result](../../docs/results/2026-10-31-irix-winterm-fault.md).

Results: 22 original Screen fonts are indexed; the requested 15-pixel face renders in four native terminal controls. All 16 original xwsh attempts still receive SIGSEGV, even after locale data and synthetic account records are staged. See the [run record](../../docs/results/2026-10-31-irix-winterm-resources.md).

This lab evaluates importing the original fonts requested by xwsh into the
native X.org server. It follows the [winterm opening attempts](../irix-winterm/README.md),
where even `-fn fixed` reports a font failure after an X locale warning.
Server font availability and foreign Xlib locale initialization are tested
as separate conditions.

## Selected resources

The [manifest](manifest.json) pins 22 original SGI Screen bitmap fonts,
118,634 bytes in total, plus the supplied C/ISO8859-1 locale files. The exact
15-pixel medium font requested by the default xwsh pattern is present as
`Scr15.pcf`. The files use PCF, including MSB-first data and `.pcf.Z` compression.
Original font/resource bytes remain under ignored `.work/irix-x11-fonts/root`;
only names, paths, sizes and hashes are published.

The broader private inventory includes font indexes and selected Fixed fonts,
but the guest experiment stages only the 22 Screen fonts. It does not replace
the native server's default fonts or import an entire IRIX filesystem.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/inventory-irix-x11-fonts.py
```

This mounts the supplied disk read-only with `ro,norecovery` and closes its
guestfish daemon afterward. Review the generated metadata before updating
the public manifest.

## Experiment

The stopped, observed winterm seeds contain the pinned kernel, original
xwsh/library closure and explicit native session environment:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-winterm-resources.py \
  --seed-directory .work/irix-winterm/runs/ci-x0hiy_qk
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-winterm-resources.py \
  --seed-directory .work/irix-winterm/runs/ordinary-6099szjn --mode ordinary
```

Each disposable guest first records the server's response to the exact SGI
font name. It copies the original Screen fonts to `/tmp/irix-screen-fonts`,
uses native [mkfontdir](https://man.netbsd.org/mkfontdir.1) to build the index,
and adds that directory to the private Xvfb font path with
[xset](https://man.netbsd.org/xset.1). Native `xlsfonts -ll` records the imported
font's metrics/properties. A native xterm explicitly requests the same font
and runs `/bin/sh`; controls bracket the vendor workload under both identities.

The `fonts` stage changes only server fonts and explicit test-account data.
The `fonts-locale` stage additionally installs the supplied C/ISO8859-1 locale
resources below `/emul/irix`. Both stages repeat direct original xwsh startup
with the default font and `fixed`, as root and uid 1234. Window trees, frames,
parent observations and raw syscall traces remain private.

The earlier bare uid 1234 had no account record. This experiment supplies
synthetic `/emul/irix/etc/passwd` and `group` entries for root and the test uid;
these are foreign namespace fixtures, not host account changes. Their hashes
are recorded separately from vendor resources. Whether foreign account lookup
accepts them is an observed outcome, not an assumption.

Font import alone does not establish a working terminal, input method, locale,
pseudo-terminal, shell execution, multilingual support or complete SGI theme.
The kernel and emulator are unchanged. Keep at most four IRIS guests running
across all workloads and stop each after use.

## Recheck saved evidence

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/qualify-irix-winterm-resources.py \
  .work/irix-x11-fonts/runs/ci-_6m3l41w \
  .work/irix-x11-fonts/runs/ordinary-2fz6bgec \
  --output docs/results/2026-10-31-irix-winterm-resources.json
```

Keep new discoveries in the [central resource checklist](../../docs/IRIX-RESOURCES.md)
and [ledger](../irix-desktop/resource-ledger.json).
