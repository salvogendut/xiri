# Adding and retiring native helpers on Indy

Both release lines passed all three cold boots and four graphical logins
each. All six boots halted cleanly, and both original CHDs retained their
published checksums. The host regression suite passed 91 tests.

The v2-to-v3 update adds `/usr/local/bin/xiri-account-map`, switches
`xiri-sync-users` to the new filter and retires the private
`/usr/local/libexec/xiri/account-map.awk`. In the guest, mapping the native
passwd and group databases through the new command must reproduce the two
installed IRIX lookup tables byte for byte.

| Installed IRIX | Indy | Initial ownership information | Expected state at the old mapper path after upgrade |
| --- | --- | --- | --- |
| 6.5.22f | R4400 | Original clean-image receipt, updated to v2 | Absent after explicit legacy retirement |
| 6.5.30f | R5000 | v2 reinstalled over a local file with mode 0440 | Original site contents, owner, group and mode restored |

Each release uses its own clean CHD, private writable overlay and two
release-specific CDs. The v2 CD establishes the source package. The v3 CD
performs the migration in both directions. The source and candidate native
archive SHA-256 digests are `b0a4a09321a146714588dc4eebedf793cb4f8099135d3711fba00b35ab341f8a`
and `ab50f980d87d635bbf5ad2cce7c1d070f87b2599131a666da1ba504420bf2bac`.
An independent candidate build reproduced the native archive and manifest.
The rebuilt CDs reproduced every checksummed input in their respective ISOs.

Before the upgrade, the probe places a byte-identical executable at the new
name and verifies that refusal leaves its inode intact. It retries with a
dangling link, then an edit to the retiring helper. Every refusal preserves
the local entry, the previous caller and the completed receipt.

In each direction, the probe sends TERM after the caller has switched and
before retirement. It runs `xiri-sync-users` in that intermediate state,
checks the previous receipt and resumes from the same CD. A second invocation
after completion is idempotent. User preferences, native account data,
the vendor shell, a native user's file, additions to the software and font
trees, and the site's session configuration are checked by hash, ownership,
mode and inode.

Each graphical boot logs `xiritest` into 4Dwm at 1280×1024, opens the
vendor shell, verifies the saved winterm colour, then logs `netbsdtest`
into ctwm with a mapped UXTerm. The final boot checks both original helper
files against the v2 copies and verifies that the new command has gone.

| IRIX release | Upgraded desktop | Saved winterm foreground |
| --- | --- | --- |
| 6.5.22f | [R4400 screenshot](2026-11-24-indy-helper-inventory-6.5.22f.png) | `#c9ecc9` |
| 6.5.30f | [R5000 screenshot](2026-11-24-indy-helper-inventory-6.5.30f.png) | `#c9d9ec` |

The per-release ISOs and compressed guest logs are in
`.work/installers/indy-11.99.11/helper-layout/`. See the
[package, CD and per-boot records](2026-11-24-indy-helper-inventory.json),
[operator instructions](../NATIVE-PACKAGE.md#add-or-retire-helpers-with-the-v3-account-update)
and [lab procedure](../../lab/native-package/README.md#in-place-native-helper-update).
