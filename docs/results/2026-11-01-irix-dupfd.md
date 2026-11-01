# Measured IRIX F_DUPFD support

IRIX fcntl selector 0 now maps to native F_DUPFD on NetBSD `xiri`, source
`572dcb832cb3a42f7c728115db241cae88fc5d8c`. It addresses the installer child's
failed stdout/stderr setup at the [previous checkpoint](2026-11-01-irix-installer-sproc.md).
This adds one descriptor operation, not general fcntl support.

## Measured contract

The original IRIX 6.5.22m installation supplies 168 independently checked
records across 21 variants, both ABIs, direct/indirect dispatch and root/UID1234.
Every record has 64 big-endian words; no descriptor or error normalization is
needed. The [retained reference](../../lab/irix-dupfd/reference.json) records
all 10,752 words and the exact fixture/source hashes.

F_DUPFD selects the lowest unused descriptor at or above the supplied minimum.
It skips occupied descriptors without replacing them. The new descriptor has
close-on-exec cleared; descriptor flags remain independent. Both descriptors
share the open-file offset and append status, and the duplicate remains usable
after the original closes. After exec, the original close-on-exec descriptor
is absent while the duplicate survives with the same access mode and file.

A valid source with a negative or out-of-limit minimum returns EINVAL 22.
An invalid/closed source returns EBADF 9 even when the minimum is invalid.
With a 32-descriptor limit, filling all slots yields EMFILE 24; an out-of-range
minimum still yields EINVAL and an invalid source still yields EBADF. Closing
one allocated slot permits the next duplicate to reuse exactly that slot.
The source and subsequent allocation remain usable after errors.

The installer's exact pattern is tested separately for stdout and stderr:
save the observation channel, close the target, duplicate a pipe writer into
that descriptor, close the original writer, transfer a byte and observe EOF
when the last writer closes. These checks cover both directions of the
observed child setup, rather than only allocation of an unused high number.

## Implementation and validation

The seven-line adapter translates only foreign selector 0 and explicitly
converts its minimum from signed 32 bits. It calls native sys_fcntl with
F_DUPFD and returns its allocated descriptor unchanged. This early return is
necessary because the existing flag-setting paths normalize success to zero.
The native allocator owns the source reference, limit checks, allocation and
publication; it clears close-on-exec/fork on the new descriptor. No core
kernel change or new hook is introduced. Deployment remains the existing
built-in personality, with the planned compat_linux-style module unchanged.

The [qualification report](2026-11-01-irix-dupfd.json) passes **420 native
records / 26,880 words and 44 native/vendor controls**. All records match the
original reference exactly. All 420 native test groups are absent afterward,
and all three matrix guests halt cleanly.

| Kernel / mode | Run under `.work/irix-dupfd/runs` | Records | Controls |
| --- | --- | ---: | ---: |
| LP64 CI | `lp64-ci-81j5e7ww` | 168 | 16 |
| LP64 ordinary | `lp64-ordinary-vgijjnvh` | 168 | 16 |
| o32 CI | `o32-ci-g_8yec0h` | 84 | 12 |

Twelve deliberately altered records are [rejected](2026-11-01-irix-dupfd-qualifier.json),
including allocation, descriptor flags, shared offsets/status, errors, recovery,
exec behavior and unused padding. The unchanged [pipe regression suite](2026-11-01-irix-dupfd-pipe.json) also
passes 220 records and 44 controls across the same three modes/kernels.
Its runs are `.work/irix-dupfd-pipe/runs/lp64-ci-ke3fjrjf`,
`lp64-ordinary-jb8g4p2x` and `o32-ci-pfirzvq4`; all halt cleanly.

The [lab](../../lab/irix-dupfd/README.md) describes the fixtures, record layout,
resource bounds and reproduction. Every native test must exit normally,
emit exactly 256 bytes, leave no test process group and preserve the before/
after native and vendor controls. Native controls independently check
allocation, native descriptor flags, shared offsets/status, forked pipe data,
EOF and exhaustion recovery. A watchdog is never accepted as success here.

The reference run is `.work/irix-reference/dupfd-records-runs/ci-qf_odwsv`.
It uses a disposable clone of the stopped sproc reference. Compressed archive
export keeps the transfer bounded. The image's previously documented XFS and
startup alerts remain outside filesystem qualification; its third-party
shutdown services take additional time, and clean shutdown is verified.

Both kernels build from clean source in separate `.work/netbsd-irix-dupfd-build`
and `.work/netbsd-irix-dupfd-o32-build` directories with sequential two-job
builds. The original and native guest emulators retain their qualified pins.
A fresh IRIS upstream check still reports `4ad1b1d435dc115697433f091b10dfa8c48aa7ed`,
already included in `xiri` at `045d69245609d186907a20e0b002e2b60be9a1ac`; no merge
or emulator build was needed. Earlier artifacts remain unchanged.

## Limits

This qualifies selector 0, the observed descriptor lifecycle and per-process
exhaustion at 32 descriptors. It does not establish system-wide exhaustion,
concurrent allocation stress, new foreign close-on-fork semantics, file locks,
other fcntl commands or physical hardware. General sharing, caught signals
and the broader desktop/installer gaps from earlier checkpoints remain.

The [installer retry](2026-11-01-irix-installer-dupfd.md) now confirms both
successful pipe-writer duplications in actual vendor libc. It still reaches
its watchdog amid gettimeofday ENOSYS calls; helper searches omit `/bin`.
The next work covers time/gettimeofday for both the installer and xclock,
then revisits helper paths. No installation or new graphical success is claimed.
