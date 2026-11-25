# Installing SGI Mozilla with the clean Indy desktop

Each Indy installer can add the browser from its own IRIX donor. The R4400
uses Mozilla 1.0.1 from 6.5.22f. The R5000 uses Mozilla 1.7.12 from 6.5.30f.
Choose `sh /cdrom/install.sh --mozilla` on a fresh target or an existing
v5 desktop, then reboot. Run `sh /cdrom/install.sh --remove-mozilla` and
reboot to return to the previous desktop. [Build and installation instructions](../NATIVE-PACKAGE.md#install-or-remove-mozilla-on-the-indy).

## Installer media

The local CDs are under `.work/installers/indy-11.99.11/mozilla-v5/`. They
contain SGI software imported from the user's original-media donors.

| CD | ISO SHA-256 | Mozilla component SHA-256 |
| --- | --- | --- |
| `xiri-6.5.22f.iso` | `7859a508e770a9b5d5602871679801abb9b4e107e729c7a9cac0eae5f77ffbf3` | `0e1d3b7126b5b396e674807a367a4bb1a2f1688e62b47090d87795af3d273595` |
| `xiri-6.5.30f.iso` | `042f1c05127488a24b058131f734aa8b72fb1094b50dc8157d63000967979efc` | `2da90eb7f32733666de109a18b5081c4fa79ee4719489435e844aa39265f770a` |

The browser CD retains the v5 native archive and each release's original v5
desktop archive. The additional archive contains the vendor browser and its
private libraries, the profile templates, the November 25 Indy kernel and
PROM boot file, the matching HTTP-capable module and the native hostname
service. The base receipt still identifies the desktop. A second receipt at
`/var/db/xiri-install/mozilla` identifies the component and records the
originals needed to remove it. Home directories are outside both archives.

The tests use stock NetBSD 11.0 sgimips userland and X sets with the
11.99.11 modular Indy bootstrap. The base kernel and browser kernel have
the same NetBSD version string. Checking the boot file, kernel and module
digests distinguishes them. [Bootstrap and qualification commands](../../lab/native-package/README.md#bootstrapping-a-stock-target).

## Boot the clean test images

From the Xiri checkout run the launcher for the desired release. At xdm, use
`xiritest` for the username and password. Double-click **Mozilla** in
**Icon Catalog → Applications**. The base-only v5 images and earlier
Freeware/Mozilla test images have separate directories.

```sh
.work/images/xiri-clean-indy-6.5.22f-mozilla-20261125/run-iris.sh
```

```sh
.work/images/xiri-clean-indy-6.5.30f-mozilla-20261125/run-iris.sh
```

| Release | CHD SHA-256 | Halted raw disk SHA-1 |
| --- | --- | --- |
| 6.5.22f | `9579b90a523755966f799d2847b639f40903f34f9e2842b82f5a7f5846b5e95d` | `c5740cc60a4af758fc529215fb58e86b4e419ecd` |
| 6.5.30f | `1d3dd1de7d690dd4cdc563176e2093094592191144782f206f178470d38d3e12` | `371d350485a04b42269fd025da11d0bb57ebe500` |

Both browsers also reached FrogFind by hostname. The site returned a
**CrowdSec Access Forbidden** document during this run. The earlier HTTP
qualification had reached the search page from both browsers.
[Server response on the 6.5.30f clean install](2026-11-25-mozilla-installer-frogfind.png) ·
[Earlier FrogFind results](2026-11-25-mozilla-http.md).

On the first graphical boot of each new CHD, `xiritest` logged into xdm,
double-clicked **Mozilla** in the Applications catalog and reached the
offline welcome page. Entering CERN's HTTP address loaded *The World Wide
Web project*. [6.5.22f first boot](2026-11-25-mozilla-installer-6.5.22f.png) ·
[6.5.30f first boot](2026-11-25-mozilla-installer-6.5.30f.png).

The independent desktop regression logged `xiritest` into a 1280×1024
4Dwm session and `netbsdtest` into ctwm with xterm on each packaged image.
Both logouts returned to xdm. All 99 host regression tests passed. A
second build of the optional archive with host umask 077 reproduced both
component digests above.

## In-place upgrade and rollback

On each private overlay we recorded SHA-256 for the user's actual
`prefs.js` and `bookmarks.html` after closing Mozilla. A locally added file
under the browser's `components` directory made removal stop before any files
were replaced. After deleting the test file, removal restored the exact
v5 kernel, boot wrapper, compatibility module and original regular-file
launcher. It unmounted the hostname service and retained the administrator's
edited rc.conf.d setting.

Both guests rebooted into the November 23 v5 kernel, loaded the v5 module
and showed the xdm greeter. Selecting Mozilla again on this existing desktop
preserved the two profile files, the user's xdm session file, the base
receipt and the edited service setting. After reboot, each browser launched
from Icon Catalog and rendered CERN using the same user profile. On the
restored 6.5.22f profile, the first navigation displayed a blank document.
**Ctrl+Shift+R** loaded the page. The 6.5.30f profile loaded it on the first
attempt. [Machine and file checks](2026-11-25-mozilla-installer.json).
