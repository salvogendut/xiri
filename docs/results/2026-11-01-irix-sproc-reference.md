# Original IRIX sproc reference

Follow-up: the [bounded NetBSD adapter](2026-11-01-irix-sproc.md) now passes
its native matrices, and [original inst](2026-11-01-irix-installer-sproc.md)
reaches child shell exec. The report below records the preceding reference-only
cycle and its implementation requirements.

The installer’s next process requirement now has a measured reference:
**112 executions, 200 records and 12,800 independently checked words** on the
supplied IRIX 6.5.22m installation. The [evidence check](2026-11-01-irix-sproc-reference.json)
passes for o32/n32, direct/indirect dispatch and root/UID1234. This is an
original-IRIX checkpoint; NetBSD still returns ENOSYS for sproc, and original
`inst` has not progressed beyond its [previous child-launch failure](2026-11-01-irix-installer-shared.md).
No package installation or new graphical success is claimed.

## Parent release

The initial flags match the installer: `PR_SADDR|PR_BLOCK|PR_NOLIBC`,
`0x03000040`. All outcomes below repeat across both ABIs, dispatch forms and
identities.

| Child action | Observation |
| --- | --- |
| Explicit `procblk(UNBLOCK, parent)` | Parent resumes and reaps exit 37. |
| Exit without an unblock arrangement | Parent remains blocked until its watchdog. |
| Arm `PR_UNBLKONEXEC`, then successful exec | Parent resumes; helper retains child PID, reports the matching PRDA PID and no share-group membership; parent reaps exit 37. |
| Arm `PR_UNBLKONEXEC`, then exit without exec | Parent also resumes and reaps exit 37. |
| Arm `PR_UNBLKONEXEC`, then failed exec | ENOENT; `PR_ISBLOCKED(parent)` remains 1. Explicit unblock then lets the parent reap exit 37. |
| Successful exec without arming release | Helper runs, but parent remains blocked until its watchdog. |
| Omit PR_BLOCK | `PR_ISBLOCKED(parent)` is 0; parent reaps exit 37 normally. |

The armed-exit result matters: neither unconditional release on child exit nor
release only on successful exec reproduces this installation. The
[SGI prctl manual](https://www.typewritten.org/Manual/SGI/IRIX/6.5.3f/man2/prctl.html)
describes the exec arrangement; the exit and failed-exec results above are
version-specific measurements, not assumptions from that description.

## Sharing and entry

The child changes both a global word and a word on the parent's stack. The
parent observes both with SADDR; the non-SADDR control retains the original
words. The child also creates a new private zero-device mapping, writes it,
and publishes its address. After child exit, the parent reads the same word
through that address. Sharing inherited backing pages alone is insufficient:
new mappings must be visible too.

PRDA begins with copied user data but reports the child's PID. Changing its
user word does not change the parent's PRDA. A preexisting LOCAL mapping is
likewise copied privately: the child sees its initial contents, and its write
does not alter the parent's copy. These observations rule out simply sharing
the entire native vmspace, which would also share those reserved/private pages.

With the installer's flags, closing the child's inherited descriptor leaves
the parent's descriptor usable. Adding SFDS makes the parent's subsequent
read fail with EBADF. `PR_GETSHMASK(parent)` reports `0x41` for SADDR, `0x43`
with SFDS, and `1` without SADDR. `PR_GETNSHARE` is 0 before creation, 2 in the
child, and 1 in the surviving parent after a successful creation and reap;
successful exec leaves the helper outside the share group.

At raw child entry, A0 is the supplied argument, A1–A3 and V0 are zero, V1
is 1, RA is zero, and the four low-word s0–s3 sentinels survive. The supplied
16 KiB sprocsp stack enters at its top minus 64 bytes, aligned to 16. A1 remains
zero even for sprocsp: this is a raw-kernel observation, separate from the
public libc callback convention described by the
[SGI sproc manual](https://www.typewritten.org/Manual/SGI/IRIX/6.5.3f/man2/sproc.html).
Only low register words were captured; full-width and floating-point state
remain unqualified.

The null-stack sprocsp request with length 4096 returns EINVAL without creating
a share group. A zero-entry request produces no record and is bounded by the
watchdog. That negative case establishes cleanup only: it does not establish
a particular errno or child termination signal.

## Evidence and cleanup

The [lab](../../lab/irix-sproc/README.md) documents the original fixture source,
record layout and reproduction. Its [retained records](../../lab/irix-sproc/reference-records.json)
contain fixture hashes and all output bytes. The independent qualifier builds
expected records from the observed contract, checking every word, PID
relationship, mapping relationship, return/error triple and identity. It
re-reads the archive independently of the observer and checks the frozen
fixture bytes, source hashes, upload coverage and clean seed/shutdown.
Ten deliberate corruptions of records/status/cleanup were rejected, including
changed PRDA, sharing and register evidence, truncation and a residual group.

The full run is `.work/irix-reference/sproc-records-runs/ci-65umxtm_`.
There are 24 expected watchdog groups: eight plain exits, eight unarmed execs
and eight zero-entry diagnostics. The watchdog targets the whole owned
session/process group. All 112 groups are absent after cleanup. The earlier
four-case smoke run `ci-najrg9e3` also halted cleanly; it predates the fixed
register-sentinel and new-mapping extensions and is not the accepted matrix.
The pinned reference emulator is unchanged. Known XFS/startup warnings from
the supplied image remain outside filesystem qualification. Both emulator
processes have exited.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/qualify-irix-sproc.py \
  .work/irix-reference/sproc-records-runs/ci-65umxtm_ \
  --output docs/results/2026-11-01-irix-sproc-reference.json \
  --reference-output lab/irix-sproc/reference-records.json
```

## NetBSD implementation requirements

No kernel code is changed by this measurement cycle. The next implementation
must provide a share-group lifecycle with per-process PRDA and LOCAL mappings,
memory-map updates, independent descriptors unless requested otherwise, and
the measured unblock/exec/exit distinction. A fork alias or plain native
vfork would fail these tests.

Current LOCAL/ELFMAP/PR_INIT_THREADS guards only examine LWP count and vmspace
reference count. Separate vmspaces sharing backing objects would evade that
guard; explicit share-group state and LOCAL range tracking are needed before
admitting that model. Map changes and failed creation require rollback and
consistent group ownership. Exec must detach only the executing process;
failed exec must retain its membership and pending release arrangement.

The licensed historical NetBSD adapter is useful design evidence, but its old
UVM API and documented procblk locking problems are not a current implementation.
Prefer current native process/UVM interfaces and personality-owned state,
keeping the `compat_linux`-style module target. Extend tests for parent death,
signals, nested members, repeated creation, map removal/protection changes and
failure cleanup before claiming broader support. Then qualify LP64 CI/ordinary
and o32 CI with native controls and retry unchanged original `inst`.
