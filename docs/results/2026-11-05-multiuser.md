# Multi-user IRIX desktop sessions

Multi-user desktop support is qualified, and its CHD is selected for manual
testing. Two ordinary IRIX desktop accounts share one native FAM service,
alongside the existing native NetBSD ctwm login. No kernel or emulator change
is needed. The cycle began November 5 and completed November 6 local time.

| Account | UID | Desktop | Native HOME |
| --- | --- | --- | --- |
| xiritest | 1234 | Original IRIX 4Dwm | /usr/people/xiritest |
| xiritest2 | 1237 | Original IRIX 4Dwm | /usr/people/xiritest2 |
| netbsdtest | 1236 | Native NetBSD ctwm; wheel member | /home/netbsdtest |

The disposable image passwords match the usernames. Root remains the native
administrator, with its existing empty lab password and `/root` home. The
IRIX lookup entry for root retains the original `/` convention.

FAM previously mapped every legacy TCP client to xiritest. The
[native credential patch](../../lab/native-fam/patches/native-credentials.patch)
uses NetBSD's existing `TCPCTL_IDENT` interface to identify the connecting
socket, then loads that account's native primary and supplementary groups.
It ignores claimed protocol UID/GID fields and rejects unresolved owners.
The localhost-only service remains alive across desktop logouts.

`xiri-session` now accepts the authenticated ordinary account. Each user gets
private session logs, Desktop links, Dumpster and application settings beneath
HOME. `xiri_user` selects only the root convenience launcher's default account.
Native xdm/PAM, X authority and native ctwm selection are retained.

The new `xiri-sync-users` administrator helper generates password-free
`/emul/irix/etc/passwd` and `/emul/irix/etc/group` lookup tables from native NSS.
Boot refreshes them; administrators can refresh after account/group changes.
It preserves the original tables once and leaves native login databases alone.
No new IRIX resources are imported. See the [runtime instructions](../../runtime/README.md).

The image uses the selected native-wait kernel/module and qualified `819c682`
emulator, plus the maintained session guard. It does not adopt the held paging
kernel or resume its intermittent-crash investigation. Earlier images and
manual overlays remain intact. The native FAM build is isolated at
`.work/native-fam-multiuser`; its predecessor remains at `.work/native-fam`.

Preparation verifies the imported payload, account projection, full-screen
graphical boot, native execution and clean halt. The CHD's full 8 GiB
decompression matches its source disk byte for byte. Its verified extraction
cache was removed afterward, reclaiming 8 GiB while retaining the CHD and
source disk. Host checks pass all 55 tests.

The [build record](2026-11-05-multiuser-build.json) preserves the FAM artifact,
preparation harness, CHD and test-log hashes, plus the cache-cleanup ledger.

The cold test adds two concurrent FAM v1 clients: own-home and supplementary
group watches, Created/Deleted events, and requests claiming the other UID or
root groups. Both client programs pass. The first harness attempt read their
logs too early because its transfer pipeline ran `wait` in a child shell;
waiting in the owning shell confirms both zero exit statuses. That incomplete
attempt is retained at `.work/irix-xdm/runs/ordinary-i8ah5k_3` and is excluded
from desktop qualification. The corrected harness waits before transferring logs.

The next attempt reaches the second desktop, but its readiness check assumes
xiritest's 18 pages. The fresh xiritest2 account correctly has 17 system pages,
without xiritest's personal Blank page. Its screenshot shows the catalog and
user-specific home icon; the harness now checks the appropriate page count.
That incomplete attempt is retained at `.work/irix-xdm/runs/ordinary-wj92nya8`
and is also excluded from full desktop qualification. Its bounded diagnostic
checks confirm xiritest2's typed shell identity, HOME/cwd, supplementary group,
private state ownership and complete 17-page system catalog. Both incomplete
guests halt cleanly. Their redundant base CHD copies were removed afterward
(another 947 MiB reclaimed); logs and small write overlays remain, and the
cleanup ledger identifies the retained base CHD needed to replay them.

The corrected cold run passes both IRIX accounts, private state, native ctwm,
login rejection, both logout menus, relogin, failed-startup recovery, service
and unrelated-login survival, catalog launching, full-screen rendering and
345 text comparisons. Winterm startup/resize checks pass across the three
xiritest sessions; the extra terminal closes normally. The second account's
typed shell verifies identity, HOME/cwd and supplementary groups. Its private
home ownership and complete 17-page catalog pass. The guest halts cleanly and
the source CHD is unchanged.

The successful run is `.work/irix-xdm/runs/ordinary-ul7xpkl5`. Its duplicate
base copy was also removed after verification, reclaiming another 473 MiB;
the write overlay and canonical CHD remain. Restore a run's `disk.chd` from
the ledger's `restore_from` path before replaying its retained overlay.

The [qualification record](2026-11-05-multiuser.json) retains the cold-run
sources, installed hashes, logs and image evidence. Screenshots show
[the second IRIX user](images/2026-11-05-multiuser-second-user.png),
[the primary desktop and catalog launch](images/2026-11-05-multiuser.png),
[native ctwm](images/2026-11-05-multiuser-native.png),
[the greeter](images/2026-11-05-multiuser-greeter.png) and
[untouched winterm](images/2026-11-05-multiuser-winterm.png).

Visual review confirms the second user's prompt and home icon, the granite
backdrop and desktop icons. The final primary-user capture shows xmahjongg
running above the populated Freeware catalog.

Reproduction from the retained selected seed:

```sh
XIRI_FAM_BUILD_DIR="$PWD/.work/native-fam-multiuser" python3 scripts/build-native-fam.py
python3 scripts/prepare-xiri-xdm-image.py \
  --seed .work/xiri-image/prepared-seed-20261105-wait \
  --kernel-build .work/netbsd-wait-accounting-build --keep-accounts \
  --fam-build .work/native-fam-multiuser --multiuser
```

The prepared run is `.work/xdm-image/prepare/ordinary-vnu_c06q`. Packaging uses
`lab/native-wait/baseline.json`, its matching boot kernel and the predecessor's
bundled emulator. The resulting bundle is
`.work/images/xiri-netbsd-desktop-20261105-multiuser/`.
Its CHD SHA256 is
`a800307d5b8a7ad7e47327115406a06814fd932bf26df1b5131e524e97cb0c12`.
Use `./xiri run` for manual testing, with the credentials in the table above.

```sh
python3 scripts/probe-xiri-xdm.py \
  --bundle .work/images/xiri-netbsd-desktop-20261105-multiuser \
  --multiuser --winterm --fonts
```

The maintained `./xiri check` selects the multi-user gate from the image's
account inventory. Later `--keep-accounts` image refreshes retain that account
inventory as well as the actual accounts. Simultaneous graphical seats,
original IRIX clogin, saved sessions and individual application repairs remain
separate work.
