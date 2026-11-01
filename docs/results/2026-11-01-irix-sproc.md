# Bounded IRIX share-process lifecycle on NetBSD

The measured `sproc`/`sprocsp` lifecycle now has a bounded implementation in
NetBSD `xiri`, source `f32cbf59a52b951f9792b2af74125ad2bbedae44`. It supports a
founder and one child, each with one LWP. This is process compatibility, not
pthread creation or a general share-group implementation. The
[original reference](2026-11-01-irix-sproc-reference.md) remains unchanged.

## Implementation

The new `sys/compat/irix_o32/irix_sproc.c` owns group membership, pending unblock
targets, automatic stacks and retained vmspace references. Both ABIs dispatch
traps 1129, 1131 and 1132 explicitly; prctl also accepts the measured ISBLOCKED,
UNBLKONEXEC, GETSHMASK and GETNSHARE queries.

Separate native vmspaces preserve process-private PRDA and preexisting LOCAL
mappings. For SADDR creation, native fork temporarily shares the other backing
mappings; the original inheritance is restored in both maps before either
returns to userland. Existing data and parent-stack writes remain shared.
New nonfixed mappings use an exact, non-replacing peer reservation followed
by UVM extraction. Failed reservation/extraction removes only owned new
mappings. SFDS selects native descriptor sharing; otherwise descriptors are
independent.

PR_BLOCK waits on a personality-owned condition variable. Explicit unblock
releases it. An armed PR_UNBLKONEXEC releases the target on successful exec
or exit; failed exec retains the group and pending arrangement. Unarmed
exit/exec does not release it. Exec/exit removes the departing member and
clears incoming target pointers. Retained vmspace references prevent a peer
from operating on a freed old map or a replacement exec image.

Automatic child stacks are removed from the surviving map when the child
leaves, including non-SADDR children. Explicit user stacks and the founder's
stack are not removed. After reap, the founder may create another child.
An ordinary fork after the pair has ended retains native COW behavior.

LOCAL ownership is tracked as a bounded, coalesced interval set. Fixed
replacement and partial unmap prepare the metadata change before mutating
the map, and commit it only on success. Guards recognize explicit group
membership as well as LWP/vmspace references. They reject active-pair fork,
nested creation, LOCAL/fixed mmap, munmap, mprotect, break, ELFMAP and
PR_INIT_THREADS. This avoids pretending that unimplemented updates propagate.

No core fork/UVM hook was added: the changes are compatibility source,
existing emulation callbacks and build registration. The eventual deployment
target remains a `compat_linux`-style module; these kernels still build the
personality in.

## Validation

The [independent qualifier](2026-11-01-irix-sproc.json) passes **340 executions,
600 records / 38,400 words and 44 native/vendor controls** across LP64 CI,
LP64 ordinary mode and o32 CI. All 340 process groups are absent after cleanup.
The 40 watchdog cases are exactly the measured unarmed exit/exec blocks;
all other cases finish normally. All three guests halt cleanly.

| Kernel / mode | Run | Executions | Records | Controls |
| --- | --- | ---: | ---: | ---: |
| LP64 CI | `lp64-ci-63o41wkh` | 136 | 240 | 16 |
| LP64 ordinary | `lp64-ordinary-95q4kaac` | 136 | 240 | 16 |
| o32 CI | `o32-ci-uq11sdec` | 68 | 120 | 12 |

Runs are under `.work/irix-sproc/runs`. Both clean-source kernel builds pass;
the LP64 and o32 baselines record the exact boot/native/debug artifacts.

The unchanged shared-mapping fixtures also [pass on this kernel](2026-11-01-irix-sproc-mmap.json):
**1,180 mapping records, 1,180 complete backing files and 44 controls** across
LP64 CI/ordinary and o32 CI. This checks existing mapping, ordinary fork,
permissions, EOF and native-policy behavior after the VM guard/LOCAL changes.
The regression runs are `.work/irix-sproc-mmap/runs/lp64-ci-g03dfi3p`,
`lp64-ordinary-vzh7ql_v` and `o32-ci-x3x5izvd`; all halt cleanly.

The installer run and all diagnostic guests also halt cleanly. A final host
process check finds no running IRIS instances.

The record checks cover low-word child registers, explicit stack entry,
private PRDA PID/user data, private LOCAL data, shared globals/parent-stack
words and new mappings, descriptor ownership, exact return triples,
exec/exit/unblock distinctions and both identities. Zero entry uses the
explicit native EFAULT policy; the original reference only established a
watchdog outcome for that case.

Native-only fixtures add guarded operations, missing/self/repeated unblock
targets, nested-creation rejection, split LOCAL ownership, ordinary-fork COW
restoration and final munmap. Twelve alternating SADDR/non-SADDR creations
run under a 192 MiB address-space ceiling with 16 MiB child stacks, so retaining
all those stacks cannot pass. Twelve deliberately corrupted native-policy
records were independently [rejected by the qualifier](2026-11-01-irix-sproc-qualifier.json).

The [lab](../../lab/irix-sproc/README.md) describes the record layout and
reproduction. Kernel pins are in its LP64/o32 baseline files. Builds are
sequential, with two jobs, and use the existing qualified emulator at
`9df1df14334838a989253efefe26f0547e6da592`. A fresh IRIS upstream fetch still
reported `4ad1b1d435dc115697433f091b10dfa8c48aa7ed`, already integrated in
`xiri` at `045d69245609d186907a20e0b002e2b60be9a1ac`; no emulator change was
needed. Previous builds, guest disks and detached checkouts remain pinned.

## Diagnostics retained

The first LP64 build caught missing kernel declarations and syscall dispatch
wiring; the corrected revision builds both kernels. The initial native smoke
run `lp64-ci-e2uxin5l` completed cleanly and matched its reference cases.

The first full native-policy tests used a 128 MiB address-space ceiling.
That works on o32, but LP64 reserves a 120 MiB main-stack region even when its
soft stack limit is smaller. The first 16 MiB child allocation therefore
correctly returned ENOMEM. Runs `lp64-ci-9sa6l7wp`,
`lp64-ordinary-50iswkjx` and `o32-ci-547fw768` are retained as diagnostics;
the first two pass their original reference cases but fail the extra fixture
precondition. Final matrices use 192 MiB. No kernel behavior was relaxed to
make this resource test pass.

## Limits and next work

This is limited to the measured flags NOLIBC, BLOCK, SADDR and optional SFDS,
with at most two members and one LWP each. Automatic stacks are bounded by
the native soft stack limit and a 64 MiB ceiling; automatic growth is not
implemented. Procblk only releases an existing PR_BLOCK wait, not its general
counting-semaphore behavior. PRCTL targets are the caller/current peer.
Initialized pthread state and ptraced processes are rejected.

Parent-death races, caught signals and restart behavior, resource-exhaustion
fork failure injection, general multi-member groups, active-group protection/
unmapping changes, full-width register/FP state and physical hardware remain
unqualified. Existing regular-file AUTOGROW and signal-registration limits
remain. Original package installation, history, catalog hooks and a usable
Freeware action are separate acceptance steps; passing these fixtures does
not establish them.


The [original-inst retry](2026-11-01-irix-installer-sproc.md) now confirms
actual vendor libc child creation, UNBLKONEXEC and native shell handoff.
F_DUPFD EINVAL during pipe setup is the next concrete compatibility failure;
gettimeofday and helper-path issues remain additional observations. The next
cycle should measure and implement that descriptor operation before repeating
the installer. No new desktop image or application-installation success is
claimed by this kernel checkpoint.
