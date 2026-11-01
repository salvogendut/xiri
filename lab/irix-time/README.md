# IRIX time and gettimeofday

The supplied IRIX 6.5.22m installation establishes that raw trap 1013 returns
seconds without reading arguments or writing a destination. The libc-level
optional pointer must not be confused with the raw syscall. Trap 1128 takes
one destination and writes exactly eight bytes: signed 32-bit seconds followed
by signed 32-bit microseconds. It returns zero, preserves V1, accepts unaligned
buffers, ignores a second argument and reports EFAULT for null, inaccessible
or read-only destinations. A page-crossing failure preserves the already
written prefix. See the [qualification record](../../docs/results/2026-11-01-irix-time.md).

`probe.c` uses the existing libc-free trap bridge with explicit 32-bit slots
for o32 and n32. Twenty-four variants cover direct/indirect dispatch,
root/uid1234, null/invalid pointers, three unaligned offsets, read-only memory,
four-byte/one-byte accessible page tails and an invalid second argument.
There are 96 binaries and 192 original executions. The native matrix repeats
192 executions on LP64 CI and ordinary IRIS, and 96 on the o32 CI kernel.

Each 256-byte record contains 64 big-endian words:

| Words | Meaning |
| --- | --- |
| 0–5 | Magic, case, trap, pointer mode, page size, buffer offset |
| 6–14 | Before/target/after V0, V1 and A3; outer calls are time(NULL) |
| 15–22 | Two timeval samples and untouched guard words |
| 23–27 | Ten-tick sginap error, second argument, sample errors, reserved zero |
| 28–31 | Real/effective UID/GID |
| 32–63 | Each byte of the 32-byte guarded destination |

The first sample precedes the target; the second follows a ten-tick sleep.
Independent guest UTC dates bracket the matrix. The qualifier checks seconds
against those dates, ordering and elapsed time, microsecond ranges, every
return field and every destination/guard byte. It does not equate timestamps
between boots. The current signed32-bit positive-date domain is qualified;
pre-epoch dates, 2038 overflow, clock adjustment and timezone/DST remain open.

Native time/select and existing native/vendor execution controls run before
and after the matrix. Fixtures must exit normally, emit exactly 256 bytes and
leave no process group. Frozen binaries, upload checksums, source hashes,
archives and seed/result hashes preserve provenance. Twelve corrupted records
exercise rejection of missing copyout, partial-write/guard errors, wrong
returns/identities, epoch output and a frozen clock.

Reproduce with sequential two-job builds using the included kernel configs,
new build directories and the source revision in `baseline.json` and
`o32-baseline.json`. Preserve earlier qualified builds. Then:

```sh
python3 scripts/build-irix-time.py
python3 scripts/probe-irix-reference-time.py \
  --seed-directory .work/irix-reference/dupfd-records-runs/ci-qf_odwsv
python3 scripts/qualify-irix-time.py \
  --reference .work/irix-reference/time-records-runs/ci-cmkx7nzx --export-reference
python3 scripts/pin-irix-time.py
python3 scripts/pin-irix-time.py --kernel-abi o32
python3 scripts/probe-irix-time.py \
  --seed-directory .work/irix-x11-fonts/runs/ci-_6m3l41w
python3 scripts/probe-irix-time.py --mode ordinary \
  --seed-directory .work/irix-x11-fonts/runs/ci-_6m3l41w
python3 scripts/probe-irix-time.py --kernel-abi o32 \
  --seed-directory .work/irix-x11-fonts/runs/ci-_6m3l41w
```

Pass the three new native run directories to `qualify-irix-time.py`, with
`--reference` and `--output`. The retained reference requires its matching
source and fixture hashes; a changed fixture requires a new reference run.

`scripts/probe-irix-xclock-time.py` takes the stopped seed
`.work/irix-xclock/runs/ci-0xaicapn` and `--mode ci` or `--mode ordinary`.
It uses the existing original executable, libraries and app-defaults, sets
`TZ=UTC0`, supplies standard X colors, and captures analog/digital windows
under both identities before/after updates and an Expose redraw. Each launch
has an intentional 18-second watchdog and whole-group cleanup. Its qualifier
checks current second returns, advancement, pixel changes and native controls;
review the retained digital frames against the recorded UTC dates as well.

`scripts/probe-irix-installer-time.py` retries the unchanged `inst -H` and
bounded dry-run distribution commands against the same kernel. It retains the
native home controls and captures the next observed boundary. A stopped
installer process is not evidence of successful installation.

Keep at most four IRIS guests active, shut each down afterward, and retain
large images, vendor files, traces and raw frames under `.work`.
