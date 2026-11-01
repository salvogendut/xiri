# Original installer startup and persistent native homes

Original IRIX `inst` loads on the pipe-qualified NetBSD kernel, then faults
before producing output. A checked fault capture identifies the immediate
boundary: **shared/autogrow mmap support**, not Icon Catalog registration.
No package installation or hook execution has succeeded yet.

The [independent report](2026-11-01-irix-installer.json) also qualifies creation
of `/usr/people/xiritest`, repeated account setup, native/IRIX access to the
same home file and its persistence across a cold boot. Both guests halt
cleanly. Eight native execution controls and two known-fault controls pass.

## Installer fault

The unmodified n32 installer and its static dependency closure come from the
pinned installed IRIX 6.5.22m image. The first guest, `ci-e8jv2xtk`, tries its
documented hardware-report option (`-H`) and a distribution-listing dry run
using `-n -M -r /emul/irix -f /cdrom/dist -c commands`. Both receive SIGSEGV
with empty stdout/stderr; their native runner removes each owned process
group. No successful distribution read or installation is claimed.

The bounded traces show `/dev/zero` opened read/write, followed by rejected
trap1134 and close. The second guest, `mmap-ci-pq57kpty`, captures all arguments
at the pinned original libc stub:

| Argument | Captured value |
| --- | --- |
| Address hint | 0 |
| Length | `0x100000` (1 MiB) |
| Protection | READ and WRITE |
| Flags | `0x141`: SHARED, AUTOGROW, AUTORESRV |
| Descriptor / offset | 3 / 0 |
| Return | IRIX EINVAL22, A3=1 |

The current adapter supports private mappings, FIXED, bounded LOCAL and
AUTORESRV. It explicitly rejects SHARED and AUTOGROW; the flag interpretation
is bound to the historical public NetBSD IRIX header. No validation has been
relaxed and no vendor return value has been patched.

The ensuing fault is in `libinst.so`, `iStringG::vprintf`. EPC is
`0x043e18d4`; the MIPS branch-delay flag identifies the actual failing
instruction at `0x043e18d8`, `sb zero,0(a4)`. Register8 contains the failed
mapping pointer, all ones, and the fault address is `0xffffffff`. Captured
code bytes match the original library. The nearby code accepts a nonzero
mapping result and later writes through it, so this directly explains the
observed crash after mmap failure. Other installer requirements can surface
after this boundary is removed.

Next measure the original shared/autogrow contract, including `/dev/zero`,
ordinary file growth, fork visibility, invalid combinations and native
controls. Add the justified subset and retry the same installer inputs before
attempting an actual xmahjongg installation.

## Shared home layout

The native helper creates `xiritest` with UID1234, primary group users/100,
native `/bin/ksh`, `/usr/people/xiritest` and mode0700. Repeating setup accepts
the existing matching account. Native ksh writes a file there; original o32
asa reads it through the same absolute path with exact expected output.
Those direct probes use explicit UID/GID1234; the account's primary group
remains users/100. Native stat verifies the file owner.

The fault probe cold-boots a copy of the clean first guest and verifies that
the home and file contents/owner persist. This establishes native account
and shared-file persistence, not graphical logout/login or desktop-state
restoration. The earlier desktop labs retain their `/tmp` homes for faithful
reproduction. New persistent-session work should use `/usr/people`.

Original installer sessions use **HOME=/**, matching IRIX's root-home
convention. The ordinary-account helper does not move NetBSD's administrative
home. Native password/login administration and generated desktop state are
described in the [software/home design](../IRIX-SOFTWARE.md).

The selected application remains xmahjongg 3.6.1. Its own installation hooks
must register it on the **Freeware** page, install its artwork/type rules,
and remove its entry on uninstall. See the [media findings](2026-11-01-irix-freeware.md)
and [lab](../../lab/irix-installer/README.md).

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/qualify-irix-installer.py \
  .work/irix-installer/runs/ci-e8jv2xtk \
  .work/irix-installer/runs/mmap-ci-pq57kpty \
  --output docs/results/2026-11-01-irix-installer.json
```
