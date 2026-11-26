# Freeware wget preserves HTTP modification times on both Indys

The original SGI Freeware wget 1.8.2 now saves the server's modification
time when run by `xiritest` on the 6.5.22f R4400 and 6.5.30f R5000 Xiri
Indys. Both downloaded the same ten bytes as original IRIX and recorded
**2009-02-13 23:31:30 UTC**. The change is in the loadable NetBSD module
at `4ed77b1dfd0`. The previously published clean Mozilla CHDs still carry
the earlier module. [NetBSD commit](https://github.com/salvogendut/NetBSD-xiri/commit/4ed77b1dfd0) · [Measurements and artifact hashes](2026-11-26-irix-utime.json).

| Test on each release | Original IRIX | Xiri before | Xiri with the updated module |
| --- | --- | --- | --- |
| Unprivileged wget, server mtime 1234567890 | `par` reports `utime("fetched", …) OK`. The file has the server time. | Trap 1030 returns IRIX error 89 (`ENOSYS`). The file has the download time. | Trap 1030 returns zero. The file has the server time and is owned by `xiritest`. |
| Explicit timestamps on another user's file, mode 0444 or 0666 | `EPERM`, timestamps preserved | `ENOSYS` | `EPERM`, timestamps preserved |
| Current time on another user's file | Mode 0444 gives `EACCES`. Mode 0666 succeeds. | `ENOSYS` | Both match original IRIX. |

The HTTP server and client used loopback on each guest. On original IRIX,
`guest` ran the same wget executable used in the earlier GIMP maintenance
check. On Xiri, NetBSD `ktrace` recorded the trap number, arguments and
return. Each run independently compared the downloaded bytes with the
served contents and read the on-disk time. [Earlier GIMP maintenance check](2026-11-26-gimp-removal.md).

## ABI and filesystem checks

Legacy `utime` takes a pathname and a pointer to two signed 32-bit seconds,
access time first. A null pointer requests the current time.
It shares the emulation-root pathname lookup, symlink following and native
VFS permission checks with trap 1235, the nanosecond `utimets` interface
used by File Manager. A separate regression check exercised trap 1235 with
distinct access and modification times and nanoseconds on both updated Indys.

Each original release and its corresponding Xiri Indy ran 60 records as
an ordinary user. They cover o32 and n32, direct and indirect calls,
symlinks, a trailing slash, missing files, an invalid time pointer,
pre-epoch seconds and the ownership cases above. The IRIX 6.5.22f control
was an Indy R4400. The 6.5.30f control was an O2 R5000.

All six Xiri guest runs and the original IRIX Indy shut down from the guest.
The O2 harness stopped its private emulator after capturing the live results.
An additional O2 boot reached login, but the probe under `/tmp` was absent,
so that run could not repeat the readback across a reboot.

One value differs. Original IRIX on XFS accepts **−1 second**
(1969-12-31 23:59:59 UTC). NetBSD VFS reserves that value for an omitted
attribute, so Xiri returns `EINVAL` before changing either timestamp.
Both systems store −2 seconds exactly.

| Release | Original IRIX records | Updated Xiri records |
| --- | --- | --- |
| 6.5.22f | [Indy R4400](2026-11-26-irix-utime-6.5.22f-reference.txt) | [Indy R4400](2026-11-26-irix-utime-6.5.22f-xiri.txt) |
| 6.5.30f | [O2 R5000](2026-11-26-irix-utime-6.5.30f-reference.txt) | [Indy R5000](2026-11-26-irix-utime-6.5.30f-xiri.txt) |

[Build and run the timestamp probes](../../lab/irix-pathops/README.md#legacy-utime).

## Try the module on a private Indy disk

The workstation copy of the qualified, module-only ISO is
`.work/modules/irix-utime-20261126/utime.iso`. Use a private test copy of
either clean Mozilla Indy running NetBSD 11.99.11. Attach the ISO as the
only CD at SCSI ID 4. From the NetBSD root console, run the following
commands. The checksum guard identifies the module shipped with those
images, and `cp -p` saves it for rollback.

```sh
set -e
mkdir -p /mnt/utime
mount -rt cd9660 /dev/cd0a /mnt/utime
module=/stand/sgimips/11.99.11/modules/compat_irix_o32/compat_irix_o32.kmod
test "$(sha256 -q "$module")" = 8be760a6e36bb163c83d5038654841b86572bc49645ebdcfbd997f9377dcb7fc
test "$(sha256 -q /mnt/utime/compat_irix_o32.kmod)" = 259386c1487ec501f3345e7e677e4ec1b8a1e13b763741e5ec98af70cae77e44
test ! -e "$module.before-utime"
cp -p "$module" "$module.before-utime"
install -m 444 /mnt/utime/compat_irix_o32.kmod "$module.new"
mv "$module.new" "$module"
shutdown -r now
```

To restore the prior module, set `module` to the same pathname in the
new root shell, copy `"$module.before-utime"` to `"$module.new"`, move
it over `"$module"` and reboot. The clean installer and its Mozilla component
still validate the release-pinned module.

To rebuild from the NetBSD fork, run
`sh lab/ip28-kernel/build-module.sh ../NetBSD-xiri .work/netbsd-octane-build/tools /path/to/build`
from the Xiri checkout. Place the resulting `module/compat_irix_o32.kmod`
at the ISO root.
