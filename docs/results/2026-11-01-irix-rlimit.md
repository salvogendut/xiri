# IRIX limit queries and executable data alignment

The NetBSD `xiri` branch now implements measured o32/n32 resource-limit queries
and accepts bgicons' declared 4 KiB executable data alignment when its address
and file offset satisfy the native page alignment. These clear the two startup
boundaries from the [first expanded desktop attempt](2026-11-01-irix-desktop-components.md).
The [application follow-up](2026-11-01-irix-desktop-startup-fixes.md) records the
next failure separately; this checkpoint does not implement pthreads.

The [qualification record](2026-11-01-irix-rlimit.json) binds the reference,
three NetBSD runs, sources, kernels and fixture manifests. The
[lab](../../lab/irix-rlimit/README.md) supplies build and reproduction commands.
Kernel code is pinned at `e8b037a4639d1683503d34c274fd0f1ec29746b1`, following
implementation commit `248b7c7dad063039c75cc0f5eab2003de4ac56ba`. Both kernels
were built from clean source into separate outputs; later documentation changes
do not change those pins or overwrite the previous PRDA artifacts.
The NetBSD `xiri` branch is pushed through documentation commit
`a330637c6204d175200df3b978d7eabfacc8a2c7`.

## Measured contract

| Query | o32 output | n32 output |
| --- | --- | --- |
| getrlimit, trap 1148 | Two unsigned 32-bit words | Two 64-bit words |
| getrlimit64, trap 1075 | Two 64-bit words | Two 64-bit words |

Original IRIX 6.5.22m returns narrow infinity as `0x7fffffff` and wide infinity
as `0x7fffffffffffffff`. A finite narrow limit keeps bit 31 when representable;
larger finite values saturate at `0xffffffff`. Soft and hard values are
independent. Successful queries preserve v1. Invalid selectors return EINVAL
before pointer validation, including an invalid selector paired with NULL.
Inaccessible and read-only output returns EFAULT; unaligned writable output
succeeds. Queries retain inherited limits across fork and exec.

The original-only fixtures use setrlimit64 (trap 1076) to prepare finite
large/high-bit measurements. The implementation adds query traps only. Native
wrappers set and report NetBSD limits before foreign exec so the comparison
checks real policy rather than substituting the original system's defaults.
Selectors 0–8 map to CPU, FSIZE, DATA, STACK, CORE, NOFILE, AS, RSS and NTHR.
The original PTHREAD default of 1024/1024 is not hard-coded. Native NTHR supplies
that query's value, without a claim of equivalent IRIX thread accounting.
[NetBSD's resource-limit manual](https://man.netbsd.org/getrlimit.2) describes
the native policy; [SGI's administration manual](https://techpubs.jurassic.nl/library/manuals/2000/007-2859-021/pdf/007-2859-021.pdf)
documents n32's 64-bit limit type and inheritance. The paired probes establish
the precise layouts and edge cases used here.

The executable change only lowers the declared alignment minimum for the
second, RW PT_LOAD of a runtime executable. Actual addresses and file offsets
must still satisfy PAGE_SIZE; RX text, the interpreter, protection, size,
overlap, file bounds and power-of-two checks remain enforced. Synthetic
interpreter checks cover initialized bytes, writable zero-filled BSS, poison
beyond the file extent and auxiliary-vector values.

## Verification

| Environment / run | Limit executions / records | Loader executions | Native/vendor controls |
| --- | --- | --- | --- |
| Original IRIX, `ci-h95j4nxc` | 40 / 1,168 | — | Reference identities and exit status checked |
| LP64 CI, `lp64-ci-evn9amob` | 56 / 1,904 | 140 | 8 |
| LP64 ordinary IRIS, `lp64-ordinary-i8yf8ci8` | 56 / 1,904 | 140 | 8 |
| o32 CI, `o32-ci-_jj48b55` | 28 / 952 | — | 8 |

All checks passed: 4,760 NetBSD limit records, 280 loader executions and 24
native/vendor controls. Coverage includes both foreign ABIs, direct/indirect
traps, root/UID1234, all selectors, invalid pointers/selectors, exact output
widths and canaries, independent soft/hard values, finite overflow, and actual
parent/child identities across fork/exec. Native policies include NOFILE 37/99,
NTHR 17/41, FSIZE above 4 GiB, and finite FSIZE values with bit 31 set.

The loader matrix retains the previous 60 cases and adds ten cases across
both ABIs: 4 KiB executable data succeeds; 2 KiB/zero declarations and 4 KiB
text/interpreter declarations fail on LP64. Existing half-page address/offset
negative cases remain failures. Each case runs under both identities in both
emulator modes. The o32 regression checks queries and native/vendor controls;
it does not reuse the synthetic interpreter that expects 8 KiB pages.

The enlarged native runner retains complete 128-byte records, including all
fork/exec stages. An independent decoder validates every record word against
the reference contract and preceding native observations. All guests halted
cleanly. Raw records, original binaries and disk images remain under `.work`.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/qualify-irix-rlimit.py \
  --reference .work/irix-reference/rlimit-records-runs/ci-h95j4nxc \
  .work/irix-rlimit/runs/lp64-ci-evn9amob \
  .work/irix-rlimit/runs/lp64-ordinary-i8yf8ci8 \
  .work/irix-rlimit/runs/o32-ci-_jj48b55 \
  --output docs/results/2026-11-01-irix-rlimit.json
```

## Retained development attempts

Earlier original-IRIX attempts remain private and are excluded from the
successful matrix. `ci-jypn3y3b` exposed a fixture error: waitsys reports child
status through waitinfo rather than the return-register assumption used by
the first inheritance check. `ci-_kdmd15a` exposed a reference-only setup
error using obsolete trap 1074 instead of setrlimit64 trap 1076. Both were
corrected before the final run. `ci-2vknrywt` established large finite
conversion over 32 executions; the final 40-execution run adds high-bit cases.
All three attempts halted cleanly; none is a kernel regression result.

The application follow-up retains separate pointer-focus diagnostics and
does not infer usable desktop clients from successful limit/loader checks.
Foreign setters, general threads, session restoration, signal handling,
physical Indy and Newport desktop qualification remain outside this result.

IRIS upstream was checked this cycle at
`f17b4d3bc1663efd02f93a5e0e4811eebba510c8`, already contained in fork `xiri`
`182efc8171f915be2152426819da8d05507c06c9`; no integration was needed.
NetBSD observations retain the qualified emulator `9df1df14334838a989253efefe26f0547e6da592`.
