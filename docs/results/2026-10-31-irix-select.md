# IRIX select: measured readiness and timeout behavior

Date: 2026-10-31. This follows the [Toolchest session diagnosis](2026-10-31-irix-toolchest-session.md).
The [select lab](../../lab/irix-select/README.md) supplies original probe sources,
reproduction commands and the [ABI contract](../../lab/irix-select/abi.json).

## Reference findings

The supplied IRIX 6.5.22m reference returned complete guarded records for 276
cases: 69 variants in direct/indirect o32/n32 forms. Records agree across those
forms after normalizing case IDs, except the intentional bad-stack cases: o32
fetches spilled arguments while n32 takes all five arguments from registers.
Both reference runs, including the initial 260-case discovery run, halted cleanly.

The measured timeval is two signed 32-bit fields. IRIX reads and validates it
before fd-set access; negative fields and microseconds >= 1000000 return EINVAL.
An unaligned timeval works, and the timeout is never written back. Negative
nfds behaves like zero descriptors. Nonempty fd-set accesses require four-byte
alignment. All input sets are fetched before descriptor validity is checked.

IRIX counts each ready descriptor once even when it appears in several result
sets. Two distinct ready descriptors return two; one descriptor ready for both
reading and writing returns one. Aliased output sets do not change that count.
It preserves bits outside the examined range. Result copying attempts read,
write and exception sets in order: a failed earlier copyout does not prevent a
later set from being updated before EFAULT is returned. Read-only output probes
with a nonready exception bit establish that behavior.

The independent peers handshake before delaying data or EOF by 300 ms, or keep
a connection idle for timeout/writable cases. This supplies new readiness after the handshake. The NetBSD timing run also
measures the syscall entry/return interval independently of the later read.

## Implementation and limits

The NetBSD fork branch is `xiri/irix-select`. The adapter decodes explicit 32-bit
arguments and owns six mask arrays: three inputs followed by three outputs.
A small `selcommon_kern` entry point exposes NetBSD's existing scan/wait and
notification protocol on that storage. The adapter supplies IRIX's unique count,
final-word preservation and copyout rules. Native select and poll entry points
retain their existing behavior. Timeout data is copied in once and never out.

Two differences remain explicit and are checked as differences from the original
oracle rather than silently treated as exact matches:

- nfds above 1024 returns EINVAL, bounding stack storage and size arithmetic.
- A selected invalid descriptor inside the requested range returns EBADF. IRIX
  instead ignores the tested unopened fd 31 with only low descriptors opened,
  preserving its bit. This suggests internal scan-range truncation; no complete
  IRIX descriptor-table capacity/growth model is inferred or implemented.

Each limit appears in all four ABI/dispatch forms. The guarded bytes and return
registers are otherwise compared exactly. Signal delivery/interruption,
concurrent descriptor or fd-set mutation, and general exceptional/OOB readiness
remain outside qualification. No leaked IRIX source was used; the implementation
rests on measured binaries, original probes and licensed NetBSD code.

## Validation

The bounded subset passed. [Machine-readable evidence](2026-10-31-irix-select.json)
pins the source revision, kernels, emulator, original oracle, helper sources,
private run results and trace hashes. NetBSD source revision is
`c8c61a40d34f494ef794a2b14fa252cdb1ccf1f0` on `xiri/irix-select`.

| Run | Select executions | Exact IRIX records | Explicit policy differences | Additional checks |
| --- | ---: | ---: | ---: | --- |
| LP64 CI | 552 | 536 | 16 | 12 native/vendor controls; 12 expected Toolchest configuration exits; native X before/after |
| LP64 ordinary | 552 | 536 | 16 | 12 native/vendor controls; 12 expected Toolchest configuration exits; native X before/after |
| o32 CI | 276 | 268 | 8 | 8 native/vendor controls |

Those three runs contain 1,380 select executions: 1,340 exact 512-byte reference
matches and 40 checks of the two documented policy differences. Root and uid
1234 each run every applicable fixture. Native o32 and original asa/echo controls
bracket the runs; n32 echo is omitted on the o32 kernel. Both LP64 modes use a
native X server and repeat Toolchest at normal priority with explicit HOME,
first with libraries alone and then with the supplied menu, app-defaults and
locale indexes.

All 24 Toolchest launches exit 1 at the configuration check. Their traces contain
53 successful select calls (27 CI, 26 ordinary) and 168 version-2 xstat calls
returning ENOSYS. There is no HOME fault or select-related XIO in these runs.
This advances the startup boundary without qualifying window creation or an
event loop. The earlier empty-HOME diagnosis still applies: select support does
not supply a session environment.

### Time spent inside select

The parent elapsed-time checks include process setup and the post-select drain.
A separate LP64 CI run therefore uses the kernel's timestamped foreign syscall
entry/return records to isolate select itself. The installed o32 `kdump` reads
the zero high half of the LP64 nanoseconds field, so its displayed fractional
times are unsuitable. The harness decodes the [version-2 binary header](../../lab/irix-select/trace-layout.json)
using offsets and widths verified against the pinned kernel DWARF. An initial
text-decoder attempt was excluded and halted cleanly. The corrected run repeats
28 unchanged fixtures across o32/n32 and direct/indirect dispatch, compares each full guarded record,
checks the independent peer log, and brackets execution with two native controls.

- Twelve delayed-data, EOF and null-time waits: **305.330–309.617 ms**, above the 150 ms minimum for a peer with a nominal 300 ms delay.
- Eight idle timeouts: **107.454–109.479 ms**, above the 90 ms minimum for a requested 100 ms timeout.
- Eight immediate ready/empty controls: **0.040–0.064 ms**.

These measurements exclude launch and drain time, but include dispatch,
marshalling and tracing overhead. They qualify bounded waiting behavior, not
precision timer accuracy or interruption semantics.

### Regressions and test setup

The unchanged recvmsg/transport suite passes **1,284 LP64 CI cases** and **641
o32 CI cases**, including its native controls, peer records and existing desktop
expectations. This uses `--kernel-checkpoint select`; the legacy harness's default
still selects its historical kernel. All six final NetBSD runs halt cleanly.
Both original-IRIX runs also halted cleanly.

The first NetBSD CI attempt is retained as a diagnostic, excluded from
qualification. Its 252 non-root regular-file probes exited before select because
the inherited input file had mode 000. The harness now explicitly sets mode 0644;
the complete rerun passed without changing kernel code or fixture bytes. The
public evidence records that preliminary result's hash and the correction.

Raw traces stay private, compressed for transfer through the existing serial
console and restored byte-for-byte on the host. Original helper/probe sources,
synthetic records, hashes and interpretations are public. No vendor binaries or raw vendor
traces are included in this checkpoint.

Next is the measured version-2 xstat contract and implementation, followed by the
same staged menu/app-defaults/locale checks. The full original desktop and 4Dwm's
mapping/relocation requirements remain separate work.
