# Desktop behavior qualification

This cycle uses the preserved `20261102-shell` prepared seed, its existing
8497554 NetBSD kernel and pinned 9df1df1 IRIS executable. It changes native
FAM and the session launcher, and imports one bitmap. Original client
binaries, filetype rules and artwork remain unchanged.

`resources.json` is the additional copy ledger. Extract the listed file from
the supplied IRIX 6.5.22m image into a private resource root, preserving its
`usr/include/X11/bitmaps/granite` path. No vendor bytes belong in Git.

Build into a new directory to preserve the previous qualified FAM build:

```sh
XIRI_FAM_BUILD_DIR="$PWD/.work/native-fam-exec-20261102-v3" \
  python3 scripts/build-native-fam.py
python3 scripts/probe-irix-desktop-behavior.py \
  --resource-root "$PWD/.work/desktop-behavior/assets" \
  --fam-build "$PWD/.work/native-fam-exec-20261102-v3"
```

The probe clones the seed, checks native controls and FAM's BTree/path tests,
compares execution-event phases with the original IRIX measurements, and
checks the closed/running/closed catalog pixels around a real double-click.
It also opens the filesystem and Dumpster icons, saves PNG screenshots from
the Newport framebuffer, checks logout cleanup and halts the guest. Results
and full logs stay under `.work/desktop-behavior/qualified-*`.

`lab/native-fam/exec-events.c` produced the reference observations with
`/usr/freeware/bin/gcc -std=gnu99 -mabi=n32 -mips3 ... -lfam -lCsup -lC`
on IRIX. `/sbin/sleep` is the executable; `/usr/bin/sleep` is a symlink.
The reference JSON ignores ordering between different requests within one
phase, retaining each event code and request number.

The daemon enables the new backend only with `XIRI_FAM_EXEC=1` on NetBSD.
Each polling pass reads process executable paths and compares device/inode
identities. An unavailable snapshot retains previous state. A missing native
pathname gets the existing IRIX-root resolver, following the executable's
final symlink. Native paths take precedence to avoid confusing native and
IRIX `/bin/sh`. File watches still monitor a final symlink itself, matching
the IRIX observation.

This is a polling fallback: short executions between polls can be missed,
and executable renames/unlinks/replacements are not tracked through a held
kernel vnode. It does not implement launch animation, all Dumpster actions,
desktop preferences, session restoration or xdm login. Those remain separate
qualifications. The existing manual CHD is not modified by this probe.

For image packaging, first carry a successful run into a separate candidate:

```sh
python3 scripts/prepare-xiri-desktop-behavior-seed.py PATH_TO_PASSED_RUN \
  --output NEW_CANDIDATE_DIRECTORY
python3 scripts/probe-xiri-desktop-usability.py \
  --seed NEW_CANDIDATE_DIRECTORY \
  --kernel-build .work/netbsd-irix-vendor-shell-clean-build \
  --baseline lab/irix-vendor-shell/baseline.json
```

Then use the successful, halted graphical run with the build/CHD qualification
commands in [the image guide](../../docs/XIRI-IMAGE.md#reuse-in-automated-work).
The [current image report](../../docs/results/2026-11-02-desktop-behavior-image.md)
records the concrete runs and checksums. Keep the previous qualified bundle
until its replacement has passed.
