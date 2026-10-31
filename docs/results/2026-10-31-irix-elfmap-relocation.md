# Bounded ELF-map relocation and original xclock windows

Original IRIX xclock now loads its libraries, connects to native X.org, and
renders analog and digital windows on NetBSD. All eight launches—two styles,
two identities, CI and ordinary IRIS—remain alive until their intentional
ten-second timeout. Native clock/runtime controls pass before and after.

This is a loading/rendering checkpoint, not a working timekeeping claim.
Both sampled frames remain identical. The digital display reads
`Thu Jan 1 00:00:00 1970`, and the original client receives `ENOSYS` from
`time` (1013) and `gettimeofday` (1128). Missing `sgilightgray` and
`sgislateblue` color names produce two warnings. Correct time, timer behavior,
Expose redraw, session integration and longer sustained operation remain open.

The [structured report](2026-10-31-irix-elfmap-relocation.json) records
**576 mapping/limit checks**, eight original clock launches, input pins,
original-system differences, controls and clean shutdowns. The
[lab](../../lab/irix-elfmap-relocation/README.md) contains reproducible fixtures,
reference observations and kernel configurations.

## Kernel change

NetBSD fork commit `d9433df7ea0` on `xiri/irix-elfmap-relocation` extends the
SIOCNREAD checkpoint. The source and emulator hashes are pinned separately for
[LP64](../../lab/irix-elfmap-relocation/baseline.json) and
[o32](../../lab/irix-elfmap-relocation/o32-baseline.json). No emulator change is
needed.

The mapper checks each requested rounded load range under the VM-map read
lock. When one is occupied, it finds a free span for the complete two-segment
layout, starting at `0x04000000` and remaining below `0x40000000`. It preserves
one displacement modulo both ELF alignments, changes only local headers and
returns the actual first load address. The runtime performs its own ELF symbol
relocations. An occupant solely in the original inter-segment gap does not
force a move. Gaps are left unmapped, and no existing map is replaced.

The previous descriptor, permission, size, layout, single-LWP/unshared-vmspace
and resource-limit checks remain. Failed VM insertions retain their errors and
rollback ownership; they do not cause arbitrary retries at another address.
Post-insertion I/O failures were not newly fault-injected in this checkpoint.
The old collision/rollback fixtures now succeed by relocating, while preserving
the original data sentinel.

The [previous loader trace](2026-10-31-irix-xclock-elfmap.md) established the
actual libXmu/libXaw collision. New original-clock traces include successful
mapping returns at `0x04000000`, `0x0401c000` and `0x040d0000`, followed by a
socket, connection and viewable window. Original executable/library files are
unchanged. This removes that specific libXmu blocker; 4Dwm's separate 4 KiB
load-boundary problem remains.

## Qualification and deliberate differences

| Check | Executions |
| --- | ---: |
| 57 variants × o32/n32 × root/uid 1234 on LP64 CI | 228 |
| Same on LP64 ordinary IRIS | 228 |
| 57 variants × o32 × root/uid 1234 on the o32 kernel | 114 |
| Focused RLIMIT_AS checks, LP64/o32 | 6 |
| Original IRIX reference attempts | 228 |

The new assembly fixtures assert code execution, initialized data, partial and
whole BSS, pure BSS, unchanged header arrays and preserved existing sentinels.
They cover RX/RW/BSS collisions, repeated competing maps, occupied fallback
space, gap-only occupation, differing alignments, upper addresses and text/gap
faults. The existing rejection variants remain enforced. All public fixtures
and records are original test material; vendor bytes and raw traces remain
under ignored `.work`.

The original-system results are not normalized into exact matches. Address
selection differs legitimately: IRIX commonly chooses `0x5dc00000`, outside
Xiri's bounded search. One mixed-alignment case maps and executes on IRIX but
has a nonzero displacement residue (`0xc000`) for the larger alignment; Xiri
preserves both alignments. The bounded descriptor/layout/permission rejection
policy is also stricter than the observed reference returns. Rejection fixtures
with action zero record the return only; an IRIX success return there is not a
claim that all malformed mappings can subsequently be accessed safely.

The reference cannot establish the 960 MiB `/dev/zero` occupant used to fill
Xiri's search interval: four attempts exit 99 during setup, before SGI_ELFMAP.
They are explicitly excluded from ABI comparison. NetBSD establishes that
occupant and returns ENOMEM from the bounded mapper without corrupting its
sentinel.

Initial native RLIMIT_AS attempts used 8 MiB, below the kernel's reserved
stack span, and failed before SGI_ELFMAP. Those ten setup attempts are excluded.
Focused reruns allow 128 MiB on LP64 and 40 MiB on o32—8 MiB above their
120/32 MiB reserved stack spans—then request a 16 MiB ELF data mapping. All six
reach SGI_ELFMAP, return ENOMEM and preserve the existing sentinel. The
[qualifier](../../scripts/qualify-irix-elfmap-relocation.py) checks these
separately rather than counting setup failures as mapper evidence.

## Captures and cleanup

Actual ordinary-mode, uid-1234 PNG captures and provenance are saved privately:

- `.work/irix-elfmap-relocation/screenshots/xclock-analog-netbsd-xorg.png`
- `.work/irix-elfmap-relocation/screenshots/xclock-digital-netbsd-xorg.png`

Each is an unedited XWD-to-PNG conversion. Adjacent JSON files pin the source
frame, PNG and run result. The screenshots show the original IRIX client, not
the native control.

Accepted runs are `lp64-ci-frdkdvij`, `lp64-ordinary-f4fjuqew`, and
`o32-ci-0t6au_du`; focused limit runs are `lp64-ci-znu0xqyx` and
`o32-ci-gjc8ocjq`. The accepted reference is
`.work/irix-reference/elfmap-relocation-runs/ci-w5_75wqj`.
All shut down cleanly. The initial 51-variant mapper run stopped at a harness
window-inspection error; the earlier reference recorded an assumed alignment
assertion that was replaced by an explicit residue measurement. Those
exploratory runs are excluded and also stopped cleanly. Builds were sequential
with two jobs, and concurrent IRIS instances never exceeded four.

The final host audit, after the companion winterm captures also finish,
finds no `iris` or `iris-ci` process.
