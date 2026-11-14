# Desktop controls and n32 executable data

The original IRIX 6.5.22 Keyboard panel has initialized RW data at virtual
address `0x10019000`, file offset `0x9000`, size `0x2000`, and alignment
`0x1000`. Those boundaries are halfway through a native 8 KiB page.

NetBSD commit `a4a7095680588b1f0533a83153a77930b0f339ca` admits this layout
inside `compat_irix_o32`. The existing native `vmcmd_map_readvn` mapper already
copies the matching prefix. This does not add another core-loader change.
The exception is limited to dynamic n32 executable RW data with 4 KiB
alignment and matching native-page offsets. Separate RX/RW virtual pages,
extent/protection checks and the existing interpreter/o32 restrictions remain.
A pure-BSS half-page start is rejected because it lacks initialized data for
the readvn prefix.

`module-build.json` preserves the original build revision and dirty inputs.
`source-equivalence.json` proves those inputs match the committed fork, and
separately retains the native-wait core provenance. `baseline.json` pins the
module/core pair and the already qualified desktop emulator.

With the retained exec-align/elfmap-subpage fixtures and the native-wait cross
toolchain available, reproduce the executable fixtures with:

```sh
python3 scripts/build-irix-acrobat-probes.py
python3 scripts/build-irix-exec-subpage.py
```

The second builder retains 87 previous admission cases, changes the existing
n32 half-page fixture to an expected success with a matching synthetic
interpreter, and adds 12 layouts. Run the generated archive's `run.sh` in
`/tmp/xiri-exec-subpage` with its compiled `loader-runner`; it exercises root
and UID 1234, checks process-group cleanup and verifies executable contents
remain unchanged. `qualify-irix-exec-subpage.py` checks all 198 records.

The focused cold GUI suite is:

```sh
python3 scripts/probe-xiri-desktop-controls.py --bundle <qualified-bundle>
```

It uses original control panels, separate ordinary users, real input events,
native X queries, saved-file ownership, window mapping and active-desktop
reboot. See the [cycle report](../../docs/results/2026-11-14-desktop-controls.md)
for results and limitations.

`scripts/probe-xiri-iconviews.py --bundle <qualified-bundle>` separately saves
different hidden-file defaults through the original panels, logs each user
back in, and captures a fresh File Manager folder containing the same two
filenames. Review its PNGs for `.hidden.txt` plus `visible.txt` for xiritest,
and only `visible.txt` for xiritest2. It also captures the reopened preference
panels. The script asserts saved values and session cleanup; visibility is a
separate recorded visual review.

To check consumption and reboot separately from the original GUI gestures:

```sh
python3 scripts/probe-xiri-controls-restore.py --bundle <qualified-bundle> \
  --saved-profiles docs/results/2026-11-14-desktop-controls-panels.json
```

This starts from a fresh disposable CHD, stages the exact panel and desk files
captured in the referenced GUI run with their native ownership, checks each
user's restored X settings/resources and desk layout, then reboots an active
desktop through `shutdown -r now`. It does not reclassify the interrupted
original GUI run as a complete run. Encoded transfers and guest SHA256 checks
preserve literal tabs and newlines before testing the saved commands.
