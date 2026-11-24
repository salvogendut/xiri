# In-place native helper upgrade on Indy

Both IRIX releases passed upgrade, interruption recovery and rollback. All
six test boots ended in clean shutdown. The eight graphical logins covered
both accounts after upgrade and again after rollback. The original CHDs
retained their published hashes. The host suite passed all 88 tests.

The update changes one file in the installed native package,
`/usr/local/sbin/xiri-sync-users`. It leaves an IRIX passwd or group file
in place when the generated contents, ownership and permissions match.
Both packages were built for the same NetBSD 11.99.11 kernel and module
with the stock 11.0 o32 userland. Two independent candidate builds produced
identical archives and manifests.

| Native archive | SHA-256 |
| --- | --- |
| November 23 installation | `8fe4ab367981937353616eb82e6cc0fdd073458103151d101001f7e039379859` |
| Updated account helper | `b0a4a09321a146714588dc4eebedf793cb4f8099135d3711fba00b35ab341f8a` |

Each release uses its own upgrade CD and private overlay of its
[clean Indy image](2026-11-23-clean-indy-desktops.md). The probe edits the
session configuration and the user's winterm colour, and adds a private file
in the native user's home, a file under the IRIX software tree and a local
font-tree entry. It compares their contents, inode numbers, ownership and
modes across the update and rollback. It also checks the installed vendor
shell and the pre-install rpcbind backup.

| Boot | Observable check |
| --- | --- |
| Install the update | An edit to the helper causes a refusal before the transaction starts. After restoring the packaged version, the probe sends TERM after the replacement reaches disk and before the completed receipt changes. Repeating the command from the same CD resumes the transaction. A further repeat reports the package already installed. |
| Boot the updated desktop | All four receipts match the new native archive. Two refreshes preserve both account table inodes. Regenerating an edited group table repairs it while preserving the passwd inode. The probe exercises both xdm logins, then rolls back the helper and checks its bytes against the saved original. |
| Boot after rollback | The four receipts match the original installation. The original helper again replaces account tables on refresh. The same two users log in and out. |

The graphical checks log `xiritest` into the full-screen 4Dwm desktop,
inspect Toolchest, Icon Catalog, winterm and xclock, execute the vendor shell
and read the saved winterm foreground from the running X server.
The `netbsdtest` login starts ctwm and a mapped UXTerm.

| IRIX release | Indy CPU | Saved winterm foreground | Upgraded desktop |
| --- | --- | --- | --- |
| 6.5.22f | R4400 | `#c9ecc9` | [PNG](2026-11-24-indy-native-upgrade-6.5.22f.png) |
| 6.5.30f | R5000 | `#c9d9ec` | [PNG](2026-11-24-indy-native-upgrade-6.5.30f.png) |

The two local CDs and compressed qualification logs are under
`.work/installers/indy-11.99.11/upgrade/`. For exact archive and CD hashes,
see the [per-boot results](2026-11-24-indy-native-upgrade.json).
The [operator guide](../NATIVE-PACKAGE.md#upgrade-native-helpers-on-an-installed-indy)
gives the mount, upgrade and rollback commands. The [lab procedure](../../lab/native-package/README.md#in-place-native-helper-update)
repeats the tests on disposable disks.
