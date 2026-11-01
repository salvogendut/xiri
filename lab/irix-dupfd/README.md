# F_DUPFD compatibility

Original inst's libc closes stdout/stderr, then uses fcntl selector0 to
allocate copies of its pipe writers at those descriptor numbers. The sproc
checkpoint creates the child and execs native sh, but selector0 still returns
EINVAL. This lab measures and implements that missing operation.

There are 21 variants for o32/n32 and direct/indirect dispatch, each run as
root and UID1234: 168 original executions. Native qualification uses LP64
CI/ordinary and o32 CI: 420 executions. Every execution emits exactly 64
big-endian words. All input flags and return triples are explicit foreign
ABI values, with no vendor implementation code or libc dependency.

## Coverage

- Minimum 0/1/2/3/4/8/31, limit 32, signed negative minima and INT_MAX.
- Lowest-free selection with an occupied descriptor beyond a hole.
- Invalid and closed source descriptors combined with invalid minima.
- Exhaustion at a 32-descriptor limit, error precedence and exact slot recovery.
- Separate descriptor flags, cleared close-on-exec, shared file position and
  append status, and duplicate lifetime after source close.
- The installer's pattern: preserve the observation channel, close stdout or
  stderr, duplicate a pipe writer into that slot, and verify data plus EOF.
- Exec of the unchanged fixture: the original close-on-exec source disappears
  while the duplicate survives, keeps its access mode and reads the file.

`setup.sh` resets a 16-byte data file before each execution. Native controls
independently check F_DUPFD allocation, both native close-on-exec/close-on-fork
flags, shared offsets/status, forked pipe output and exhaustion rollback.
The foreign API does not add a close-on-fork selector.

## Record layout

Words 0–3 are magic 0x58445550, case number, kind and minimum. Words 56–59 hold
real/effective UID/GID. Words 60/61 are fixed sentinels; unused words are zero.
A return triple is V0, V1, A3; ordinary traps seed V1 with 0xfeedface. A read record
is a return triple followed by the byte read (zero for EOF).

| Kind | Observations |
| --- | --- |
| 0: minimum | open4, SETFD7, DUPFD10; source/copy GETFD13/16; shared reads19/23/27; SETFL31 and source GETFL34; copy/source SETFD37/40 and GETFD43/46; read after source close49. Errors retain source flags/readability and verify the next ordinary dup slot at23. |
| 1: hole | open4, DUPFD7, occupied descriptor GETFD10, shared reads13/17. |
| 2: invalid | failing DUPFD4, next ordinary dup7. |
| 3: closed | open4, failing DUPFD7, next ordinary dup10. |
| 4: exhaustion | open4; allocated count7, EMFILE8, invalid minimum11, invalid source14; released slot17, recovered allocation18, source read21, final ordinary dup25. |
| 5: pipe redirection | pipe4, source SETFD7, DUPFD10, copy/source GETFD13/16, write19, data read22, EOF26. Observation output uses a saved descriptor. |
| 6: exec helper | closed source GETFD4, surviving copy GETFD7, read10, GETFL14. Setup fails the execution if source/duplicate allocation is wrong. |

The independent qualifier constructs every expected word and compares exact
descriptor values, errors, bytes and identities. It checks frozen binaries,
source hashes and the original output archive. Native runs require normal
termination, empty stderr, whole-group cleanup and before/after controls.
No timeout is accepted as a passing F_DUPFD case.

## Reproduction

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build-irix-dupfd.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-reference-dupfd.py \
  --seed-directory .work/irix-reference/sproc-records-runs/ci-65umxtm_
# Build both configs sequentially with two jobs and separate dupfd build dirs.
PYTHONDONTWRITEBYTECODE=1 python3 scripts/pin-irix-dupfd.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/pin-irix-dupfd.py --kernel-abi o32
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-dupfd.py \
  --seed-directory .work/irix-x11-fonts/runs/ci-_6m3l41w
# Repeat with --mode ordinary and --kernel-abi o32.
# qualify-irix-dupfd.py --reference RUN --export-reference freezes the reference.
# Add the three native run directories and --output FILE for qualification.
```

The separate `probe-irix-dupfd-pipe.py` repeats unchanged pipe fixtures on the
new kernels. `probe-irix-installer-dupfd.py` retries unchanged original inst.
Earlier artifacts and harnesses remain pinned. The per-process limit test
does not establish behavior under system-wide descriptor exhaustion, general
fcntl support, concurrent allocation stress or physical hardware.
