# Shared mappings and zero-device AUTOGROW

Original `inst` requests a 1 MiB READ|WRITE mapping of an O_RDWR `/dev/zero`
descriptor with flags `0x141`: SHARED|AUTOGROW|AUTORESRV. Its startup previously
received EINVAL and then stored through MAP_FAILED in `libinst.so`.

This checkpoint translates SHARED to native MAP_SHARED. AUTOGROW is accepted
only for a descriptor referencing the native zero character device, including
symlink aliases. A regular file named `zero` does not qualify. The adapter holds
the descriptor reference through native mmap, preventing reuse between the
device check and mapping. Native mmap converts the zero device to anonymous
memory and supplies sharing across fork and lifetime beyond descriptor close.
No core-kernel hook is added.

Regular-file AUTOGROW remains EINVAL. It requires different behavior: the
[original mmap manual](https://techpubs.jurassic.nl/manpages_0530/cat2/standard/mmap.html)
describes extending shared files when a process stores beyond EOF, and private
pages without extending the backing file for private mappings. Extending a
file at mmap time would not implement that contract. Plain shared regular-file
mappings use native descriptor permissions, page alignment and EOF policy.

The measured 6.5.22m reference grows the shared file on **either a read or a
store** at offset 8192: its size remains 17 immediately after mmap, then becomes
12288 after the access. Private AUTOGROW supplies zero-filled pages while the
file stays 17 bytes. Without AUTOGROW, both kinds fault with SIGBUS. These
observations take precedence over the older manual's narrower wording for
this particular reference installation.

AUTORESRV continues to use native demand allocation. IRIX logical-swap
accounting, exhaustion guarantees and mlock interactions are not established.
LOCAL still requires one LWP and an unshared vmspace. Unknown flags and ANYADDR
remain unsupported; offsets retain the signed 32-bit and native alignment
limits. See [NetBSD mmap](https://man.netbsd.org/mmap.2) for native behavior.

## Measurement

The original static fixture has 59 variants, each built for o32/n32 and
direct/indirect dispatch, then run as root and UID1234. They cover the exact
installer request; fork visibility and private isolation; descriptor close;
independent zero mappings versus shared file aliases; fixed/local combinations;
shared/private reads and stores beyond EOF; device aliases; file permissions;
protection faults; and invalid descriptors, offsets, lengths and flags.

Each case resets its file contents and produces 64 big-endian words. The
harness also copies the backing file after the child is reaped, preserving
independent byte-level evidence of sharing, growth and file privacy. Deliberate
faults run in children; the native runner owns the complete process group.
Native shared/private zero mappings, close lifetime, file alias visibility,
permissions and beyond-EOF faults are checked before and after the matrix.
Native o32 and original asa/echo controls accompany them.

The fixture's `lseek` size snapshots are useful on original IRIX. Foreign
`lseek` remains ENOSYS on this NetBSD checkpoint; those returns must be checked
explicitly, not presented as size observations. The native harness's independent
backing-file copies establish the final sizes and contents on NetBSD.

## Reproduction

Preserve existing outputs. Build both configs here from their pinned clean
NetBSD source revision into `.work/netbsd-irix-mmap-shared-build` and
`.work/netbsd-irix-mmap-shared-o32-build`, sequentially with two jobs. Use
`mips64eb` and `mipseb` respectively. A matching toolchain can be reused with
a `tools` symlink after setting `build-arch`.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build-irix-mmap-shared.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/pin-irix-mmap-shared.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/pin-irix-mmap-shared.py --kernel-abi o32
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-reference-mmap-shared.py \
  --seed-directory .work/irix-reference/pipe-records-runs/ci-3q2rck05
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-mmap-shared.py \
  --seed-directory .work/irix-x11-fonts/runs/ci-_6m3l41w
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-mmap-shared.py \
  --seed-directory .work/irix-x11-fonts/runs/ci-_6m3l41w --mode ordinary
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-mmap-shared.py \
  --seed-directory .work/irix-x11-fonts/runs/ci-_6m3l41w --kernel-abi o32
```

The reference uses the previous reference emulator, while NetBSD runs use the
pinned LP64 emulator. Both hashes are recorded. Reference media still emits the
previously documented XFS alerts; this is not a filesystem qualification.
Result archives are compressed before scratch-disk export.

`probe-irix-installer-shared.py` separately retries original `inst -H` and the
xmahjongg distribution dry run, with native home and process-cleanup controls.
Vendor payloads, guest disks and full traces stay under ignored `.work`.

The [qualified results](../../docs/results/2026-11-01-irix-mmap-shared.md)
include the complete matrix and retained harness diagnostics. The independent
`qualify-irix-mmap-shared.py` checks every record word and backing byte; it
requires LP64 CI/ordinary and o32 CI runs. Original `inst` then reaches the
[new sproc boundary](../../docs/results/2026-11-01-irix-installer-shared.md).
