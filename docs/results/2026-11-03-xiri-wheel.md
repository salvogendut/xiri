# netbsdtest wheel membership

The account update is qualified and selected for `./xiri run`. The
[fresh-CHD result](2026-11-03-xiri-wheel.json) verifies graphical login as
`netbsdtest`, wheel membership, interactive `su -`, return to xdm and clean
halt. The [terminal PNG](images/2026-11-03-xiri-wheel.png) records the root
shell result and the original user's supplementary groups.

The change is `usermod -G wheel netbsdtest` inside NetBSD. NetBSD's
`usermod -G` adds secondary group membership; the primary group remains
`netbsdtest` (GID 1236). Password files and all other group entries are checked
for preservation. The image creation recipe now gives new netbsdtest accounts
`-G wheel` as well.

The focused check boots through graphical PROM AutoLoad, logs in through xdm
as netbsdtest, verifies its supplementary groups, and types `su -` in the
native terminal. The resulting shell must report root, UID 0, HOME `/root`
and working directory `/root`. Root retains the existing empty development
password. The native session then returns to xdm, preserving service PIDs,
and the guest must halt cleanly.

The original image's kernel/module, rendering, IRIX session and catalog
qualification is inherited from the [xdm cycle](2026-11-03-xiri-xdm-image.md).
This account-only cycle does not repeat that full compatibility suite.
CHD creation, verification and exact raw round-trip checks are repeated,
followed by the actual fresh-CHD account/login/su test.

The replacement bundle is
`.work/images/xiri-netbsd-desktop-20261103-xdm-wheel-v2/`:

- CHD bytes: `481227717`
- CHD SHA256: `95eeecc4195dc63e80352b28a522b93da06495ebe95bcb4ce79f0b48b7572693`
- Raw SHA256: `66d2b205bb2a676d95bd1c9f92fcb543183aab5f1b08f6f41eb460e214e90d8e`
- Preparation: `.work/xdm-wheel/prepare-djuo9s9w`
- Fresh CHD check: `.work/xdm-wheel/check-va4madqv`

Preparation and the fresh CHD both verified `netbsdtest wheel` as the login's
groups and
`root`, `0`, `/root`, `/root` from `id -un`, `id -u`, `$HOME` and `pwd` after
`su -`. The guest returned to xdm, preserved service PIDs and halted cleanly.
The source disk hashes were unchanged, and the test emulator instances were
stopped. The previous manual image and overlays remain intact.
`./xiri doctor` verified all 12 immutable artifacts and host dependencies;
launcher dry runs, Python compilation, documentation links and JSON checks passed.

Reproduce with the retained base seed:

```sh
python3 lab/irix-xdm/wheel-update.py \
  --seed .work/xiri-image/prepared-seed-20261103-xdm
./xiri image --seed-run PATH_TO_PREPARATION_RUN \
  --output .work/images/xiri-netbsd-desktop-20261103-xdm-wheel-v2
python3 lab/irix-xdm/wheel-update.py \
  --bundle .work/images/xiri-netbsd-desktop-20261103-xdm-wheel-v2
python3 lab/irix-xdm/qualify-wheel.py PATH_TO_CHD_CHECK \
  --output docs/results/2026-11-03-xiri-wheel.json \
  --png docs/results/images/2026-11-03-xiri-wheel.png --promote
```

Use fresh bundle, JSON and PNG output paths on repeats. The helper records both the exact
account observations and the explicitly inherited image preparation data.
The previous image and its manual overlays remain preserved.
Promotion requires the same parent still selected; omit `--promote` when
reproducing this cycle after a newer image has been selected.

The first preparation attempt, `prepare-cwvnjqxb`, passed the group/password
checks but its test used `pgrep -x ctwm`. NetBSD compares argv[0], including
the pathname, so this missed the window manager. That run is retained as a
failure with a clean halt and unchanged source disk. The helper now uses
the full-path matcher from the existing native-session probe.

The next preparation, `prepare-zi50xdx1`, passed login and `su -`, but inherited
the manual image's `overlay = true`. Its first package reproduced the old
base disk instead of incorporating the account change. It was not promoted.
Its fresh-CHD run, `check-lt_my_2j`, rejected the missing wheel membership and
halted cleanly with its source disk unchanged.
Preparation now disables overlays on its disposable raw clone and rejects an
unchanged raw disk; qualification also rejects a CHD with the parent's raw
hash. Fresh-CHD testing verifies that membership survives packaging.

IRIS upstream was checked at
`28fa516684c54e00e35b258c65e5dcac3a36165c`, already in `xiri`; no integration
or fork builds were needed.
