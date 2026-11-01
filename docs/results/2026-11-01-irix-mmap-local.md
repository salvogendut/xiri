# Original GL's fixed/local mapping on NetBSD

Original 4Dwm now completes the `/dev/zero` mapping used by its GL dispatch
initialization. The previous `gl: warning, mmap failed` message and fault at
0x1050 are gone. It encounters a later startup SIGSEGV before managing windows;
this checkpoint does not claim a working 4Dwm desktop.

The implementation is pinned at NetBSD `c1a9f98d05d` on
`xiri/irix-mmap-local`. IRIS is unchanged. The
[lab](../../lab/irix-mmap-local/README.md) contains both kernel configurations,
exact build pins, original synthetic inputs and reproducible commands.

## Measured request and implementation

Native ptrace captured all six n32 arguments under root and UID1234:
`mmap(0, 0x1000, 3, 0x92, 3, 0)`. The descriptor was `/dev/zero`; the return was
EINVAL. The following SIGSEGV addressed 0x1050 in original `libGL.so`.
The existing tracer's labeled native fault control checks its register layout
and reported PC. The mapping request is PRIVATE | FIXED | LOCAL; see the
[original SGI mmap manual](https://techpubs.jurassic.nl/manpages_0530/cat2/standard/mmap.html).
Original IRIX accepts the request at address zero and exercises its payload.

The adapter explicitly translates PRIVATE and FIXED and accepts LOCAL only
for one LWP with an unshared vmspace. Native mmap retains ownership of file
checks, protections, COW, rounding and replacement. It never receives arbitrary
foreign flag bits. Shared mappings, AUTOGROW, AUTORESRV, ANYADDR and unknown
flags remain unsupported. The 0x1000 ANYADDR flag is not MAP_ANON.

Flag translation alone was insufficient: native exec normally excludes page
zero. The corrected IRIX probe permits VM_MIN_ADDRESS after validating the
foreign ELF. GL's 4096-byte request then covers an 8192-byte native page,
including its dispatch data at 0x1050. Native programs retain the default
page-zero guard. Tests check native mmap rejection directly and after both
IRIX ABIs exec a native program; `vm.user_va0_disable` stays 1 throughout.

## Verification

All **660 mapping cases, 30 native/vendor/cleanup controls and 32 native
page-zero controls pass**. Every accepted guest shuts down cleanly.
The original IRIX 6.5.22m reference contributes 264 executions.

| Run | Mapping cases | Oracle-equivalent | Explicit native policy | Other controls | Native zero-page controls |
| --- | ---: | ---: | ---: | ---: | ---: |
| LP64 CI `lp64-ci-9w7qfw1q` | 264 | 176 | 88 | 10 | 12 |
| LP64 ordinary `lp64-ordinary-5loxjf4j` | 264 | 176 | 88 | 10 | 12 |
| o32 CI `o32-ci-5rdcre9m` | 132 | 96 | 36 | 10 | 8 |

The 33 variants run through direct and indirect traps, as root and UID1234.
Their records include request fields, results and identities. Successful
cases inspect the entire rounded page and exercise read/write access. Fixed
replacement preserves the adjacent mapping; an invalid descriptor preserves
the original mapping. Private regular-file writes leave its backing hash
unchanged. A deliberate read-only store terminates with SIGSEGV after emitting
the successful mapping record.

The [qualification JSON](2026-11-01-irix-mmap-local.json) binds all accepted
runs, sources and pins. [Decoded original records](../../lab/irix-mmap-local/reference.json)
retain each reference result. Only non-fixed placement and native page size
are normalized; payload checks use the actual page size. Every other difference
is checked against an explicit native-policy expectation.

Those differences include LP64's 8 KiB alignment, EINVAL for unsupported flags,
bad protection and empty mappings, and ENOMEM for the wrapping fixed range.
Native `/dev/zero` also accepts a write-only descriptor, while IRIX returns
EACCES. NetBSD's vnode mmap implementation recognizes that device as an
anonymous-memory source before its regular-file FREAD check; this existing
native behavior is retained. Only signed 32-bit file offsets and unshared
address spaces are covered.

## Original application and remaining work

The live 4Dwm run `local-ci-_i17e84p` records mmap returning address zero, then
successful close, heap growth and descriptor queries. The old GL warning is
absent. A separate native ptrace capture identifies the later fault in libc
`_usinit`, at PC `0x0fb0d92c`, reading `0x00200e00`. This is the PID field
of IRIX’s process-private data area (PRDA), currently absent. Both root and
UID1234 reproduce it after mmap succeeds. The diagnostic environment supplies
HOME and an explicit unavailable display; the live X run reaches the same
temporary-name initialization path. The
[application evidence](2026-11-01-irix-4dwm-mmap.json) binds both captures. Native X remains usable, the two native test windows remain unmanaged,
and the descendant supervisor confirms complete cleanup. The guest halts
cleanly. A screenshot of those unmanaged native windows would not demonstrate
4Dwm success, so no success PNG is published.

The earlier flag-only kernel (`21ce00a5355`) and its two fixture runs are
excluded from the accepted matrix: they established that the native minimum
address still rejected GL's page. Its live 4Dwm run reproduced the old fault.
The redundant ordinary-mode attempt was interrupted during boot and is also
excluded. The original mapper and winterm checkpoints remain separately
pinned. The [shell regression](2026-11-01-irix-mmap-shell.json) on this kernel
passes all three applications (native xterm, original xwsh, and the unchanged
winterm launcher), with typed shell commands, UID1234-owned output markers,
eight native controlling-terminal controls, ten other controls and clean
shutdown. Existing gettxt, signal-handler, resize and normal-exit limitations
remain explicit.

The later [PRDA checkpoint](2026-11-01-irix-prda.md) clears the libc fault;
its [4Dwm follow-up](2026-11-01-irix-4dwm.md) reaches window interaction and
a combined winterm shell with session saving disabled. The negative captures
above remain the evidence for this earlier mapping checkpoint.
