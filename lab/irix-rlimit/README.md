# IRIX resource-limit queries and executable alignment

This checkpoint addresses the first expanded desktop startup boundaries:
`getrlimit(RLIMIT_PTHREAD)` in fm/Icon Catalog initialization, and the declared
4 KiB alignment of bgicons' otherwise page-aligned executable data segment.
Application behavior is checked separately from the ABI/loader fixtures.

## Measured query contract

Original IRIX 6.5.22m measurements establish these wire layouts:

| Call | o32 fields | n32 fields |
| --- | --- | --- |
| 1148, getrlimit | Two 32-bit unsigned words | Two 64-bit words |
| 1075, getrlimit64 | Two 64-bit words | Two 64-bit words |

Infinity is `0x7fffffff` in the narrow layout and `0x7fffffffffffffff` in the
wide layout. A finite narrow value retains its high bit when representable;
finite values larger than `UINT32_MAX` return `UINT32_MAX`, which differs from
infinity. Soft and hard values are independent. Successful calls preserve v1.
Unknown selectors return EINVAL before examining the pointer; inaccessible or
read-only output storage returns EFAULT. Unaligned writable storage succeeds.

[SGI's resource-limit description](https://techpubs.jurassic.nl/library/manuals/2000/007-2859-021/pdf/007-2859-021.pdf)
also documents the n32 64-bit limit type and inheritance. The paired probes
determine the trap-level layouts and edge cases for this installation.

Selectors 0–8 map to actual native CPU, FSIZE, DATA, STACK, CORE, NOFILE, AS,
RSS and NTHR limits. Native NTHR supplies PTHREAD's query value; it does not
establish equivalent IRIX thread accounting, thread creation or synchronization.
The [native manual](https://man.netbsd.org/getrlimit.2) describes the host policy.
Foreign setters are not implemented here. The original-only large/high-bit
fixtures call setrlimit64 to prepare measurements; the NetBSD controls instead
set native limits before foreign exec.

## Reproduce

Use the NetBSD `xiri` branch and the code revision in `baseline.json` or
`o32-baseline.json`. Preserve the previous PRDA artifacts. The kernel builds
use separate `.work/netbsd-irix-rlimit-build` and
`.work/netbsd-irix-rlimit-o32-build` outputs, run sequentially with two jobs.
An existing verified toolchain can supply each build's `tools` symlink; record
the matching `build-arch` (`mips64eb` or `mipseb`) before reuse. A newly built
toolchain is also valid. The configs are `XIRI_IRIX_RLIMIT` and
`XIRI_IRIX_RLIMIT_O32`.

```sh
XIRI_NETBSD_SOURCE_DIR="$PWD/../NetBSD-nixbench" \
XIRI_NETBSD_BUILD_DIR="$PWD/.work/netbsd-irix-rlimit-build" \
XIRI_NETBSD_TFTP_DIR="$PWD/.work/netbsd-irix-rlimit-build/tftp" \
XIRI_NETBSD_CONFIG="$PWD/lab/irix-rlimit/XIRI_IRIX_RLIMIT" \
XIRI_NETBSD_ARCH=mips64eb XIRI_BUILD_JOBS=2 scripts/build-netbsd-kernel.sh kernel
PYTHONDONTWRITEBYTECODE=1 python3 scripts/pin-irix-rlimit.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build-irix-rlimit.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build-irix-exec-align.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-reference-rlimit.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-rlimit.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-rlimit.py --mode ordinary
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-rlimit.py --kernel-abi o32
```

For the o32 build, use the `-o32-build` output/TFTP paths, `_O32` config,
`mipseb` architecture and `pin-irix-rlimit.py --kernel-abi o32`.
Pin creation requires clean recorded source. Documentation-only commits after
the code revision do not repin existing qualified kernels.

The resource fixtures cover both ABIs, direct/indirect traps, UID0/UID1234,
all nine selectors, invalid selectors and pointers, output canaries, both
field widths and fork/exec inheritance. A native wrapper reports its actual
limits immediately before foreign exec. It also tests distinct descriptor
and thread soft/hard limits, file sizes above 4 GiB and values with bit 31 set.
The enlarged native runner retains complete inheritance records.

The 70-case LP64 loader matrix preserves the previous 60 cases and adds
declared 4 KiB executable data, 2 KiB/zero alignment rejection, and unchanged
text/interpreter minimum alignment. Each case runs as root and UID1234.
The synthetic interpreter checks initialized data and writable zero-filled
BSS, including poison bytes beyond the file extent. Native and vendor asa
controls run before/after, and the original runtime files are restored after
the synthetic interpreter cases. The o32 regression exercises query behavior
and native/vendor controls; it does not reuse the 8 KiB synthetic interpreter.

`qualify-irix-rlimit.py --reference RUN RUN... --output REPORT` independently
checks the reference and all three native runs. It checks every record word,
then compares host resource values to the preceding native observations.
Original default values are evidence of layout and reference behavior, not
hard-coded replacement values for NetBSD.

## Expanded desktop follow-up

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-desktop-startup-fixes.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-desktop-startup-fixes.py --mode ordinary
```

This uses the same original files as the [component inventory](../irix-desktop-components/README.md).
The native focus diagnostic records target and actual pointer positions while
waiting for mapped-window geometry to settle; it never assigns input focus.
The existing shell-input helper retains its separate explicit-focus behavior.
Both application modes retain the 120-second descendant supervisor and clean
guest shutdown. A cleared startup call is distinct from a working desktop.

The [qualified result](../../docs/results/2026-11-01-irix-rlimit.md) records
1,168 original-IRIX records, 4,760 NetBSD records, 280 loader executions and
24 native/vendor controls. The [desktop follow-up](../../docs/results/2026-11-01-irix-desktop-startup-fixes.md)
records cleared startup blockers and the next `MAP_AUTORESRV` boundary.
