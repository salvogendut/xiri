# Native package assembly and qualification

Host assembly, reproducibility and the corrected 6.5.22f guest qualification
pass. This is the native package stage of the
[installation plan](../XIRI-INSTALLATION.md), with a separate clean-target
managed installer still required.

## Package

The [maintained command](../NATIVE-PACKAGE.md) accepts six explicitly named
artifacts and their pinned source provenance, a qualified cross compiler and
verified NetBSD 11.0 distribution sets. It never opens the prepared desktop
CHD. It cross-builds all six session helpers, stages the maintained runtime,
adds the kernel/boot/module, FAM, rpcbind and Newport driver, and records the
native ELF dependency closure and stock target prerequisites.

Two independent builds of the corrected package produce identical archives
and manifests:

| Check | Result |
| --- | --- |
| Native profile | `netbsd-sgimips-native-v1` |
| Archive SHA256 | `e28c1f08eb0ace50c38e87b13b9a1e70cd486b87895fe30518ec306950a1d354` |
| Manifest SHA256 | `65d8bdf461952584713eb2079ea3257f0f1b7b76fd58b67ead3d96ea4dcedbb7` |
| Payload entries | 47 |
| Native prerequisites | 80 |
| Library dependency edges | 281 |
| Host tests | 83 passed, including 5 new native packaging tests |

The package retains separate `kernel/` and `root/` sections. Configuration
defaults are marked for preservation, service/module snippets are opt-in,
and donor accounts, passwords, homes and machine-wide policy are excluded.
`preflight.sh` verifies package contents, the running kernel version, the
on-disk kernel and native prerequisites. Installed verification checks file
types, hashes, modes and links while allowing administrator configuration.

## Guest checks and scope

The initial guest run passed package/kernel/prerequisite checks, then correctly
rejected a wrong kernel and a missing prerequisite. Its first installed check
rejected the existing `/netbsd` file mode: the fixture intentionally leaves
kernel activation separate, and the established image installs kernels read-only.
The corrected checker continues to require exact kernel bytes and running
build identity, while preserving the existing kernel/boot-wrapper mode.
Payload executable/module modes remain checked. The initial failure is retained
as a failed result rather than relabeled as passing.

The final run uses a fresh native image copy, the same independently qualified
`819c6825` emulator and the 6.5.22f original-media vendor payload. Installation
and repeat installation pass while preserving accounts and administrator
configuration. Both IRIX logins pass 1280×1024 display checks and report
`xiritest`, HOME/cwd `/usr/people/xiritest`, and `IRIX_SHELL_OK` from the original
IRIX shell. File Manager, logout/relogin, native ctwm with visible UXTerm, and
clean halt pass. The selected source CHD is unchanged. Native configuration
and user homes are inherited, so this is not a clean-target installer test.

The package and compact evidence are retained under
`.work/packages/netbsd-sgimips-native-v1/`, including five PNGs and the exact
executed probe. The [machine-readable result](2026-11-14-native-package.json)
pins their hashes. The existing 6.5.22f `gettxt` helper limitation remains open;
this cycle does not claim broader application coverage.

The completed guest's process group is stopped and disk readers are absent.
Its disk, write overlay, test CD and duplicate media were removed after saving
evidence: 833 MiB of allocated file footprint. Shared reflink extents mean
that figure is not a physical-space reclamation claim. Earlier failed-run and
superseded-package cleanup removed another 0.65 GiB of file allocations.

## Fork and release policy

IRIS `xiri` incorporates six upstream commits through `5fb831ce`, merged as
`a986a0a1` and pushed. Both CLI builds, 226 Newport tests, five display tests
and the new native-window GPU presenter test pass. The latter runs on Vulkan
with the AMD Radeon 780M, and compares rendered pixels with the software
reference. The [integration record](2026-11-14-native-package-upstream.json)
retains exact commands and log hashes. Its isolated 1.47 GiB build cache was
removed after validation; the selected image's emulator remains pinned.

Always maintain both **IRIX 6.5.22 and IRIX 6.5.30** deliverables, with separate
donors, import profiles, qualification records and CHDs. Shared native packages
require checks with both vendor versions. The existing original-media O2
installation supplies the next 6.5.30f donor candidate. The saved installation
records were reviewed; the present disk is not qualified merely by those old
records. The next version will not replace the 6.5.22 reference.
