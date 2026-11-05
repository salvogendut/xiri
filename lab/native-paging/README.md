# Native pageout latency and swap-control correction

The [investigation](../../docs/results/2026-11-05-native-paging.md) reproduces
long native sleep delays while the page daemon encrypts swap batches. The
candidate pauses one tick after 100 ms of scanning when free pages plus
submitted pageouts meet `freetarg`. It keeps the existing four-times-target
scan termination and does not pause below the minimum target. Page-owner
and queue locks are released before the pause.

A separate big-endian defect passes an `int` temporary to the one-byte
`vm.swap_encrypt` sysctl. The corrected temporary is `bool`. The native
false/true/false/true control in `lab/system-stability/swap-control.c` fails
two cases on the old core and passes all four after the correction. The
image continues to use encrypted swap.

`build.json` records the actual parent revision and dirty source bytes used
for the candidate build. `source.patch` is the exact kernel patch. The IRIX
module is byte-identical to the qualified job-control module. These changes
are in shared native UVM code; they add no IRIX personality hooks.
`source-equivalence.json` verifies the built source bytes against committed
NetBSD `xiri` revision `0febc6eb24ad889d12a3b2afaa12558c9781859d`.

Build independently, preserving the earlier artifacts:

```sh
XIRI_NETBSD_SOURCE_DIR="$PWD/../NetBSD-xiri" \
XIRI_NETBSD_BUILD_DIR="$PWD/.work/netbsd-paging-latency-v3-build" \
XIRI_NETBSD_TFTP_DIR="$PWD/.work/netbsd-paging-latency-v3-build/tftp" \
XIRI_NETBSD_CONFIG="$PWD/lab/irix-module/XIRI_IRIX_MODULE" \
XIRI_NETBSD_ARCH=mips64eb XIRI_BUILD_JOBS=2 \
bash scripts/build-netbsd-kernel.sh kernel
python3 scripts/build-irix-module.py --build .work/netbsd-paging-latency-v3-build --jobs 2
```

Native timing and forced encrypted-data readback:

```sh
python3 scripts/probe-native-sleep.py \
  --bundle .work/images/xiri-netbsd-desktop-20261105-cleanup \
  --kernel-build .work/netbsd-paging-latency-v3-build \
  --iterations 100 --pressure-mib 96 --check-swap-control --verify-memory
```

The full desktop gate retains two IRIX sessions, the native ctwm user,
100 input rounds per transport/phase, 20 native child-control pairs,
precise descendant checks, 96 MiB held pressure and active-session shutdown:

```sh
python3 scripts/probe-system-stability.py \
  --bundle .work/images/xiri-netbsd-desktop-20261105-cleanup \
  --kernel-build .work/netbsd-paging-latency-v3-build \
  --runs 1 --sessions 2 --input-iterations 100 --child-iterations 20 \
  --pressure-mib 96 --halt-active --require-cd9660
```

The final candidate passes the full pressure gate in `boot-wtpd08jl`,
including 800 input round trips and clean shutdown. Forced encrypted swap
readback also passes, proving 752 page faults and matching every written
test byte after releasing the extra eviction pressure. A separate packaged
image run crashes the kernel during desktop startup. Its evidence is retained
and further crash investigation is deferred at the user's request. The new
image remains unselected; preserve the existing manual image.
The independent cold desktop check passes xdm/4Dwm/ctwm, fonts, shell jobs,
catalog launch and clean shutdown; see the
[image report](../../docs/results/2026-11-05-native-paging-image.md).
