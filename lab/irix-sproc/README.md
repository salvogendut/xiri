# Original IRIX sproc lifecycle

Original `inst` reaches libc's raw `sproc` trap1129 with flags `0x03000040`
(`PR_SADDR|PR_BLOCK|PR_NOLIBC`). This lab measures that boundary on the supplied
IRIX 6.5.22m installation and tests the subsequent bounded NetBSD adapter.

The original, libc-free fixtures have 14 variants, built for o32/n32 and
direct/indirect dispatch and run as root and UID1234: 112 executions. They
cover explicit unblock, exit, exec with/without PR_UNBLKONEXEC, failed exec,
nonblocking creation, a non-SADDR control, SFDS, LOCAL, a newly created mapping,
explicit-stack sprocsp, a short stack request and zero entry. Source uses
explicit ABI constants, public manuals and the licensed historical NetBSD
headers; it contains no vendor implementation code.

`spawn.S` puts fixed low-word sentinels in s0–s3 before the trap. `entry.S`
captures the child registers before a C prologue. Each complete observation is
64 big-endian words (256 bytes). The child emits a record before its final
unblock/exec/exit action; a successful exec emits a helper record; the parent
waits for the child before emitting its final record. Record order is therefore
child, optional exec helper, parent. Error returns produce only a parent
record. A watchdog may retain only the earlier records of a blocked case.

These are low-word register observations, not a complete 64-bit register or
floating-point inheritance test. The fixture is deliberately independent of
libc's trampoline and arena setup.

## Record layout

| Word(s) | Parent (role0) | Child (role1) | Exec helper (role2) |
| --- | --- | --- | --- |
| 0–5 | magic, case, role, flags, action, trap | same | magic, zero case, role; remaining zero |
| 6–7 | own PID, zero | own PID, parent PID | own PID, zero |
| 8–10 | spawn V0, V1, A3 | initial A0, A1, A2 | zero |
| 11–19 | zero | initial A3, V0, V1, SP, RA, s0–s3 | zero |
| 20–23 | PRDA PID, user word, global word, argument word | original PRDA PID/user, global and argument words before writes | PRDA PID, remaining zero |
| 24–26 | waitsys return triple | PR_ISBLOCKED(parent) triple | zero |
| 27–29 | wait code, exit status, reaped PID | PR_GETNSHARE triple | PR_GETNSHARE triple |
| 30–32 | pre-spawn PR_GETNSHARE triple | PR_GETSHMASK(parent) triple | zero |
| 33–35 | read inherited zero-device descriptor triple | close inherited descriptor triple | zero |
| 36 | LOCAL mapping word after child | LOCAL word before child write | zero |
| 37 | explicit stack top, or zero | same | zero |
| 38–40 | LOCAL mmap triple | optional PR_UNBLKONEXEC triple | zero |
| 41–43 | post-wait PR_GETNSHARE triple | optional failed exec triple | zero |
| 44–46 | zero | PR_ISBLOCKED after failed exec | zero |
| 47 | argument pointer on parent's stack | zero | zero |
| 48–50 | child's new mapping address/content, zero | new mmap return triple | zero |
| 51–55 | zero | zero | zero |
| 56–59 | real/effective UID/GID | same | same |
| 60–63 | zero | zero | zero |

A return triple is V0, V1, A3. V1 is seeded with `0xfeedface` at ordinary
traps so unchanged secondary returns remain visible. Fixed sentinels are
`0x11220001` through `0x11220004`; PRDA user markers are at `0x200100`.

## Reproduction and ownership

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build-irix-sproc.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-reference-sproc.py \
  --seed-directory .work/irix-reference/mmap-shared-records-runs/ci-i361kb_a
```

Use `--smoke` for four root/direct cases before the full matrix. Every run
clones a clean reference disk, freezes and checks fixture bytes, verifies
guest upload checksums, compresses its exported evidence, and shuts down the
owned emulator. The original image's known startup/XFS alerts remain outside
this ABI qualification.

On original IRIX each test creates a new session before changing identity.
Its five-second guest watchdog targets that test's entire process group, not
only its parent. The archive records whether the watchdog fired and whether
the group is absent after cleanup. An exit status of 137 is an expected
observation only for a specifically qualified blocked case. Only the specifically measured blocked cases may use a watchdog in the
native matrix; it is never a successful child-launch result.

Native execution must omit the reference identity argument and use the
existing native process-group supervisor. NetBSD does not implement the
reference-only setpgrp/identity setup used here.

## Bounded NetBSD implementation

The subsequent kernel checkpoint adds a two-member, single-LWP share group.
It uses separate native vmspaces: native fork temporarily shares non-LOCAL
backing, while PRDA and tracked LOCAL intervals retain private copies. Original
inheritance is restored in both maps before user execution. New nonfixed
mappings are installed at the same address in the peer through a non-replacing
reservation and UVM extraction, with rollback on failure. Each member retains
its old vmspace until its exec/exit hook; successful exec leaves the group,
whereas failed exec leaves the unblock arrangement intact.

Automatic stacks are owned by the group and removed from the surviving map
when the child leaves. Explicit user stacks are not removed. Only the founder
can create another child, after the previous child has left. This is not a
pthread or general multi-member implementation. Stack growth, foreign signal
handlers, parent-death races, resource-exhaustion fork failures, and full-width
register/FP inheritance remain outside the accepted reference contract.

Active pairs reject ordinary fork, nested creation, LOCAL/fixed mapping changes,
munmap, mprotect, break, ELFMAP and PR_INIT_THREADS. Unsupported sharing flags,
ptraced processes and initialized pthread state are also rejected. Procblk
only releases an existing PR_BLOCK wait; it does not implement the general
counting semaphore. PRCTL targets are restricted to the caller/current peer.
Zero entry is explicitly rejected with EFAULT rather than reproducing the
unexplained original timeout. Automatic stack size is the native stack limit,
bounded to 64 MiB; sprocsp validates at least the last 8 KiB of a supplied stack.

`native-lifecycle.c` adds native-policy records (magic `0x58475350`). Word 1 is
kind, word 2 is role, and words 56–59 contain the four identities. Guard-child
records contain return triples at words 8–46 for the guarded operations,
self/missing/repeated unblock targets and nested creation, followed by an
unchanged LOCAL marker at 47. Parent records contain completed spawn count at
3, three LOCAL-region markers at 4–6, GETNSHARE at 8–10, an ordinary-fork COW
marker at 11, and the final munmap triple at 12–14. Remaining words are zero.

The replacement case removes the middle native page of a three-page LOCAL
mapping, replaces it with a normal fixed mapping, then checks that only this
middle page is shared. The repeat case alternates SADDR and non-SADDR children
12 times. `limit-exec.c` imposes a 192 MiB address-space ceiling and 16 MiB
stacks, making accumulated stack mappings exceed the limit if cleanup fails.
The native supervisor checks process-group absence for every execution.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build-irix-sproc-native.py
# Build the two configs with scripts/build-netbsd-kernel.sh, sequentially,
# using .work/netbsd-irix-sproc[-o32]-build and at most two jobs.
PYTHONDONTWRITEBYTECODE=1 python3 scripts/pin-irix-sproc.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/pin-irix-sproc.py --kernel-abi o32
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-sproc.py \
  --seed-directory .work/irix-x11-fonts/runs/ci-_6m3l41w
# Repeat with --mode ordinary, then --kernel-abi o32.
# Pass all three run directories to qualify-irix-sproc-kernel.py --output FILE.
```

Native capture and comparison are separate. The kernel qualifier checks every
record word, exact errors and termination, complete matrix coverage, frozen
fixture/source hashes and before/after native/vendor controls. Reference
fixtures and their expected records are unchanged. Only the two measured
blocked cases use the native watchdog; a watchdog on any other case fails.
