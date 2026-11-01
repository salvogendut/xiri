# IRIX process-private data area

Original 4Dwm's libc `_usinit` reads its PID from `0x00200e00`. The
[previous capture](../../docs/results/2026-11-01-irix-4dwm-mmap.json) identified
that unmapped read after GL initialization succeeded. This lab measures PRDA
initialization, ordinary fork and exec on the supplied IRIX 6.5.22m image,
then qualifies the bounded NetBSD implementation.

## Measured contract

A private writable page starts at `0x00200000`. The measured system prefix at
`+0xe00` contains PID, two zero words, initial FP flags (o32 0, n32 4), and CPU
PRId (0x440 on this R4400). Other inspected bytes are initially zero. Fork
preserves user bytes through private COW, changes only the child's PID, and
leaves the parent's bytes intact. Exec creates fresh state even if the previous
image deliberately corrupted its PID and user bytes. Setting a traditional
signal mask does not populate the inspected PRDA signal-hold bytes.

The licensed historical NetBSD PRDA definitions provide offsets; the paired
original measurements determine values. In particular, PRId is CPU identity,
not a second PID. See the [SGI sproc manual](https://techpubs.jurassic.nl/manpages_0530/cat2/standard/sproc.html)
for the fixed private area and ordinary fork behavior. This implementation
does not add sproc, threads, scheduling hints or user-managed signal holds.
The FP values describe measured initialization, not a general FP-control API.

The foreign exec package maps one zero-filled native page. Explicit uint32
initialization avoids native ABI struct layout. A child-return callback writes
only the child's PID through normal COW. Fork checks writable PID storage before
creating a child; a removed or read-only PRDA returns EFAULT. That damaged-state
behavior is explicit native policy, not a claim of original-IRIX equivalence.
A later child copyout failure terminates that child with SIGSEGV.

Native exec discards the foreign PRDA. Native mincore controls check absence
both directly and after each foreign ABI execs a native image. The separate
native page-zero controls also remain enforced; no global setting changes.
LP64 uses an 8192-byte native page and verifies its extra 4096 bytes are zero.

## Reproduce

Build the pinned LP64 and o32 kernel configurations sequentially, with at most
two jobs. Exact source, emulator and artifact pins are in `baseline.json` and
`o32-baseline.json`.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build-irix-prda.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build-irix-prda-controls.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-reference-prda.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-prda.py \
  --seed-directory .work/irix-x11-fonts/runs/ci-_6m3l41w
```

Repeat the native probe with `--mode ordinary` and with `--kernel-abi o32`.
Each clones a stopped qualified guest, checks pinned inputs, runs native/vendor
and descendant-cleanup controls, and halts its own guest. The fixture matrix
covers four operations, both ABIs, direct/indirect traps, and UID0/UID1234.
Every record is 96 big-endian words; the independent qualifier checks every
word and PID/parent relationships before normalizing identities and page size.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/qualify-irix-prda.py \
  --reference .work/irix-reference/prda-records-runs/ci-1fnljc1x \
  .work/irix-prda/runs/lp64-ci-x098xgfl \
  .work/irix-prda/runs/lp64-ordinary-e6hhdz1k \
  .work/irix-prda/runs/o32-ci-09o_4gh0 \
  --output docs/results/2026-11-01-irix-prda.json
```

The [report](../../docs/results/2026-11-01-irix-prda.md) records 80 executions,
180 records, 20 damaged-PRDA fork cases and 94 other controls. The decoded
original observations are in `reference.json`; original binaries, disks and
private traces remain under ignored `.work`.
