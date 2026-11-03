# Xdm desktop image

This qualified CHD is preserved as the parent of the current
[wheel-account update](2026-11-03-xiri-wheel.md). The
[direct-disk result](2026-11-03-xiri-xdm-image.json) passes full-screen xdm,
three IRIX logins, the separate native ctwm login, both original IRIX logout
menus, failed-startup recovery, catalog launch and clean shutdown. The
previous manual module image and its user state remain intact.

Run `./xiri run` from the repository. Captured PNGs show
[4Dwm and the catalog-launched game](images/2026-11-03-xiri-xdm-image.png),
[the native ctwm session](images/2026-11-03-xiri-xdm-image-native.png) and
[the greeter](images/2026-11-03-xiri-xdm-image-greeter.png).

Run `.work/irix-xdm/runs/ordinary-dmjmkzaq` booted the actual CHD without a
TFTP kernel, verified 1,788 installed files, rejected a bad password and
preserved boot services plus an independent same-user shell across all
session changes. Each IRIX session passed the 8,536-pixel Render check.
The final catalog launch created a new xmahjongg process and produced the
FAM execution event. The guest recorded clean unmount/halt markers; the
source CHD was unchanged. The separate qualifier then promoted it.

This cycle packages the [qualified native runtime](2026-11-03-xiri-xdm.md).
Native NetBSD xdm starts at boot on the full 1280×1024 accelerated Newport
display. The public development-image accounts are:

| User | Password | Desktop | HOME |
| --- | --- | --- | --- |
| `xiritest` | `xiritest` | Original IRIX 4Dwm | `/usr/people/xiritest` |
| `netbsdtest` | `netbsdtest` | Standard NetBSD ctwm | `/home/netbsdtest` |

Root serial administration remains available. The ttyE0 getty is disabled
so xdm owns graphical input. Native PAM and the global Xsession are unchanged;
only xiritest's `.xsession` selects the IRIX desktop. Services start at boot
and remain running across logout. Native ctwm is selected through the normal
system Xsession for netbsdtest, whose home has no `.xsession`.

## Replacement and initial failure

The replacement bundle is `.work/images/xiri-netbsd-desktop-20261103-xdm-v2/`.
Its CHD is 481,225,588 bytes (about 459 MiB), representing an 8 GiB disk:

- CHD SHA256: `1eb35a78f36aab9b67592fc32fa79604e4ddb244dcc7561b56b976e7b24cce83`
- Raw SHA256: `c712ef8733ae3697157c4ec3c0c6e4a73d6c481809694d582fa405345d435371`
- NetBSD `xiri`: `9390bc04900a0d04796d494aca5b00651f12954d`
- Pinned IRIS backend: `819c6825504d40ad9f9aa00554249affd2da9446`
- Build/baseline: [lab/irix-xdm](../../lab/irix-xdm/README.md)

The first candidate, `20261103-xdm`, retained the earlier kernel. Its first
valid desktop login stopped in native UVM while creating a process. It was
not promoted. The [fault investigation](2026-11-03-uvm-pglist.md) records the
missing lower-bound check in the contiguous allocator, the exact saved
registers/segment addresses and the NetBSD fix. The old source reproduces
the invalid lookup; the fixed allocator passes 195,841 synthetic cases.
The source CHD is unchanged and its failed overlay remains for reproduction.
This finding does not establish the cause of earlier intermittent faults.

The rebuilt module passed [12 lifecycle observations](2026-11-03-xiri-xdm-module-lifecycle.json),
including busy-process unload refusal and normal boot loading, then
[168 signal/process/receive observations and four native controls](2026-11-03-xiri-xdm-module-regressions.json).
Both guests halted cleanly. The kernel/module pair was rebuilt in fresh
outputs; older detached builds and qualified manual images remain intact.

## Preparation and artifact boundary

The [replacement preparation record](2026-11-03-xiri-xdm-image-prepare.json)
covers `ordinary-yygfi813`: 1,771 existing files verified, replacement
kernel/module and native runtime installed, graphical disk autoboot into
xdm at 1280×1024, services/module at securelevel 1, native control and a
verified clean halt. The source raw seed is unchanged. The initial
[older-kernel preparation](2026-11-03-xiri-xdm-image-prepare-initial.json)
is retained separately as `ordinary-zd4wxphb`.

The source is the previous qualified module raw seed. Preparation verifies
its hash and imported-file inventory before changing it. It preserves the
original IRIX resources and corrected Newport Xorg driver; no new vendor
imports are needed. `build-irix-module.py` now includes the native UVM source
hash in its manifest.

The builder's `createhd`, `verify` and `extracthd` steps passed. Extracted
raw bytes match the prepared disk exactly. The manifest records
`session_manager: xdm`, kernel/module pins and an xdm-specific manual README.
The automated probe copies the CHD and frozen graphical AutoLoad NVRAM,
boots from disk with no TFTP kernel available, and exercises the installed
runtime without reinstalling it. Test tools and hash inventories come from
a diagnostic CD. The full imported-file scan is retained in the replacement
check; it was not removed to avoid the allocator failure.

Both original PROM profiles and older manual overlays remain untouched.
`verification/graphics-boot-nvram.bin` is an immutable test profile; manual
NVRAM can evolve independently without preventing later checks. Native rc.d
adds a kernel-version prefix to `/etc/motd` at boot, so MOTD is excluded from
the immutable support-file check. Account/home/login assertions verify the
actual session policy separately.

## Reproduction

Build the pair using the [baseline instructions](../../lab/irix-xdm/README.md),
then use matching hashes for the actual build:

```sh
python3 scripts/prepare-xiri-xdm-image.py \
  --kernel-build .work/netbsd-xdm-build \
  --baseline lab/irix-xdm/image-baseline.json
./xiri image --seed-run .work/xdm-image/prepare/ordinary-yygfi813 \
  --output .work/images/xiri-netbsd-desktop-20261103-xdm-v2 \
  --baseline lab/irix-xdm/image-baseline.json \
  --kernel .work/netbsd-xdm-build/tftp/netbsd-XIRI_INDY
python3 scripts/probe-xiri-xdm.py \
  --bundle .work/images/xiri-netbsd-desktop-20261103-xdm-v2
python3 scripts/qualify-xiri-image.py PATH_TO_COLD_BOOT_RUN \
  --output docs/results/2026-11-03-xiri-xdm-image.json \
  --png docs/results/images/2026-11-03-xiri-xdm-image.png --promote
```

Use a fresh output directory and the newly returned preparation run when
repeating. `./xiri check` dispatches by manifest: xdm images use graphical
login tests; older images keep their root-launcher checks. Neither probe
promotes its own result.

## Harness checks and limits

Two earlier preparation failures are retained: `ordinary-9xmbhqa1` exceeded
the initial five-minute payload hash allowance and halted cleanly;
`ordinary-36e3lagf` reached the greeter but its teardown watched serial for
kernel halt messages sent only to ttyE0. The latter remains a failed run.
Preparation and CHD checks now use the desktop-usability probe's established
kernel-message-ring technique, factored into `xiri_lab/kernel_log.py`, and
require both clean unmount and halt markers. The matching debug kernel's
verified `msgbufp` address is recorded in the bundle. On CHD failure the
probe also captures the kernel ring and a PNG before attempting shutdown.

The cold-boot qualification requires full-screen greeter/4Dwm/ctwm, password
rejection and acceptance, three successful IRIX logins, both original IRIX
logout menus, failed-startup recovery, a native login/logout and independent
same-user shell survival. It checks module loading, payload hashes, XAA and
the 8,536-pixel Render control, a fresh catalog double-click launch, granite
resources, FAM execution events, service ownership, no new rpcbind binding
warnings, clean halt and an unchanged source CHD.

Native logout ends ctwm from its own terminal; its Quit menu is not tested.
Winterm font metrics, the greeter's `Xft.render:false` workaround, one-account
FAM, original clogin, saved sessions and broader application gaps remain.
Prismatic and physical hardware need separate manual acceptance.

IRIS upstream was fetched at `28fa516684c54e00e35b258c65e5dcac3a36165c`, already
contained in integration `1aed0df`; no merge was required. The host suite
passes 37 tests, including rejection of incomplete xdm image evidence and
preservation of mutable manual NVRAM.

After promotion, `./xiri doctor` verified 12 immutable artifacts; the manual
launcher and check dry runs selected this bundle. A reusable raw seed is
available at `.work/xiri-image/prepared-seed-20261103-xdm`. The previous
qualified CHD hash is unchanged. Repository JSON and local
documentation links passed validation. All owned IRIS/Xvfb instances stopped;
the final host process check found none remaining.
