# Static o32 arguments, files, and memory — 2026-10-30

The experimental NetBSD personality now passes static argument, file, and
memory probes using synthetic IRIX o32 calls. All 44 cases pass in both CI and
ordinary IRIS execution, including the earlier execution/rejection matrix,
native regressions, partial transfers, invalid arguments, and memory faults.
Both guests shut down cleanly.

This qualifies a bounded static interface subset. The loader still accepts
only the explicitly marked, single read/execute segment described in the
[first execution record](2026-10-30-irix-o32-execution.md). No vendor IRIX
executable, runtime, dynamic loader, original desktop, or physical machine
was tested.

## Sources and build

The implementation is committed on the NetBSD fork's
[`xiri/irix-o32-basics`](https://github.com/salvogendut/NetBSD-nixbench/tree/xiri/irix-o32-basics)
branch at `c9ab9ccc062650870e17006571c93e665e2133d9`, following the initial
personality commit `6b6a7967685baff3fa1d1fb7e1e50113470fb2a6`. The trunk base
remains `a852b4a03800c32a127640b784fcc9fc94159d12`; the sibling primary checkout
stays on `trunk`. Source changes are confined to the opt-in personality and
its scope README, in `.work/netbsd-irix-src`.

The ABI definitions come from the local historical snapshot
`5aca2679d78276864d2980a08314887b2058fb2c`: `syscalls.master`, `irix_types.h`,
`irix_exec_elf32.c`, `irix_mman.{c,h}`, `irix_fcntl.c`, and the SVR4 open-flag
definitions. No removed SVR4 implementation was restored.

The kernel uses [`XIRI_IRIX_BASIC`](../../lab/irix-o32/XIRI_IRIX_BASIC), identifier
`XIRI_IRIX_BASIC_20261030`, the isolated GCC 14.4 toolchain, and
`.work/netbsd-irix-build/basics-tftp/`. Kernel SHA-256 is
`b271508f02f83f36ce8a049e6f4a93de39a9f7c6931773712697b8244645f415`.
An incremental rebuild from the clean committed source produced exactly the
tested kernel. The debug image hash and source hashes are in the retained JSON.

IRIS remains at `484452d963d2da4e2a7559e88bcc33da0f2a0c01`, binary SHA-256
`cc6561d0bdfec6ce30d656caf4a6eaee6ffbf622e5348c3b77b73810d5293f56`.
The profile is R4400, 256 MiB, Newport, NetBSD 11.99.9 kernel with NetBSD 11.0
userland. Each run cold-boots a private disk/NVRAM clone and installs its
matching `/netbsd`. The release kernel and original checkpoint retain their
recorded hashes. X11 was not requalified on this kernel.

## Implemented subset

| Interface | Supported behavior and bounds |
| --- | --- |
| Argument stack | Native o32 stack alignment, argc/argv/envp, explicit static `AT_NULL` pair, and a 16-byte-aligned first argument string |
| `read` / `write` / `close` | Direct calls 1003/1004/1006 through current native operations with foreign errno translation |
| `open` (1005) | Access modes 0/1/2; IRIX APPEND `0x8`, NONBLOCK `0x80`, CREAT `0x100`, TRUNC `0x200`, EXCL `0x400`, each translated explicitly |
| `mmap` (1134) | Positive length, exactly MAP_PRIVATE `0x2`, null address hint, basic R/W/X bits, and a nonnegative page-aligned signed 32-bit file offset |
| `munmap` / `mprotect` (1135/1136) | Page-aligned address, positive signed 32-bit length; basic R/W/X protection bits only |

The six-word o32 mmap call takes its last two words from `sp+16` and `sp+20`.
The dispatcher checks stack-address addition and copies those words from user
memory. The wrapper expands the signed 32-bit offset to native `off_t` and
initializes native argument padding. Dispatch remains an explicit selection
of implemented numbers; every other number returns IRIX `ENOSYS=89` under
the existing experiment policy.

Open uses the native guest namespace and mode/umask rules. There is no
`/emul/irix` lookup or device adaptation. `/dev/zero` supplies zero-filled
private mappings through the native device path. IRIX flag `0x1000` means
SGI_ANYADDR and is rejected instead of being passed through as NetBSD
MAP_ANON. Shared/fixed mappings, address hints, autogrow, and other flags are
also rejected. Native VM supplies protection, copy-on-write, bounds checks,
and cleanup; historical IRIX reserved address ranges are not implemented.

## Results

| Run | Cases | Duration | Shutdown |
| --- | --- | --- | --- |
| `basics-compat-ci-p1w12csb` | 44 passed | 150.240 s | Clean |
| `basics-compat-ordinary-mcomxvtf` | 44 passed | 154.512 s | Clean |

The version 2 suite has 34 fixtures plus five additional marked/native pairs.
All 23 version 1 fixture hashes, metadata, and expectations are unchanged.
The eleven new fixtures in [`basics.S`](../../lab/irix-o32/basics.S) check:

| Fixture | Observed behavior |
| --- | --- |
| `irix-args` | Four arguments including spaces and an empty string; two environment entries, vector terminators, stack/string alignment, and static `AT_NULL` |
| `irix-args-empty` | Empty argv and environment, zero argc, and explicit `AT_NULL` |
| `irix-files` | Create/exclusive collision, write, close, append, reopen/read, EOF, truncate/rewrite; native parent verifies exact `saved\n` contents and mode 0640 |
| `irix-file-errors` | Missing path, null path/buffer, bad descriptors, double close, write to read-only descriptor, and invalid open flags return the expected foreign errors |
| `irix-partial` | Five-byte short read, EOF, nonblocking empty read, partial nonblocking write, and full-pipe `EAGAIN` |
| `irix-memory` | Eight zero-filled 8192-byte mappings; first/last word checks, writes, read-only/read-write transitions, unmap, and descriptor cleanup |
| `irix-file-map` | Private writable mapping of a read-only file at offset 4096; mapping survives descriptor close; native hash check confirms backing file unchanged |
| `irix-mem-errors` | Invalid descriptor, flags, offset, length, protection, hint, or alignment produce `EBADF`, `EINVAL`, or `ENOMEM` as specified by the fixture |
| `irix-stack-args` | Inaccessible and overflowing syscall stack addresses return `EFAULT` |
| `irix-readonly` | Write after read-only protection terminates with `SIGSEGV` |
| `irix-unmapped` | Read after unmap terminates with `SIGSEGV` |

Successful new fixtures exit 37 with no stdout; failed assertions exit 99.
The two protection-fault fixtures terminate with signal 11 without a parent
kill. The native runner prepares deterministic pipes for partial transfers
and enforces the existing bounded wait and reap policy. It compiles in each
guest with `-Wall -Wextra -Werror`.

Both runs also pass the native kernel/file/swap smoke probe before the matrix,
the native identity/file checks afterward, and all earlier error, unsupported
call, delay-slot, malformed ELF, timeout, and fault cases. Both modes write
their own disk clones directly, without snapshot restore or CI rollback.

The [retained JSON](2026-10-30-irix-o32-basics.json) contains all 88 observations,
fixture/source/kernel hashes, identities, and timings. Full serial logs,
configuration, virtual media, and disposable disks remain under
`.work/irix-experiment-runs/`. See the
[lab reproduction commands](../../lab/irix-o32/README.md#static-arguments-files-and-memory).

## Remaining scope

The next bounded loader step is writable ELF data and zero-filled BSS, with
segment-boundary and permission tests. Interpreter loading and a synthetic
dynamic probe follow. General unbranded ELF recognition, runtime path policy,
dynamic auxv, vendor startup register conventions, and execution from newly
mapped memory remain unqualified. The wrapper accepts PROT_EXEC, but these
fixtures exercise data access and R/W protection transitions only.

No reference IRIX installation is available for behavioral comparison. This
subset does not establish general file/VM compatibility, fork/exec, caught
signals, synchronization, n32/n64, PRDA, process sharing, vendor applications,
or physical Indy support. Original desktop dependency work still needs the
reference installation.
