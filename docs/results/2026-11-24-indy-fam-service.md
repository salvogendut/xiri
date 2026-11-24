# FAM service log update on Indy

The v3-to-v4 update lets the operator select a log file in
`/etc/rc.conf.d/xiri_famd`. The default is `/var/log/xiri-fam.log`.
The package replaces the native rc.d script and its example. The machine's
active rc.conf.d file, FAM policy, accounts, module configuration and the
test user's session selector and winterm preferences kept their contents,
inodes, ownership and modes across upgrade and rollback.

| Indy | IRIX | After the v4 reboot | After the v3 rollback reboot |
| --- | --- | --- | --- |
| R4400 | 6.5.22f | Site log, [4Dwm screenshot](2026-11-24-indy-fam-service-6.5.22f.png) | Default log, site setting preserved |
| R5000 | 6.5.30f | Site log, [4Dwm screenshot](2026-11-24-indy-fam-service-6.5.30f.png) | Default log, site setting preserved |

Each guest refused a locally edited startup script before changing either
package file. The probe then interrupted the forward and reverse updates
just after replacement of the rc.d script. The example and the completed
receipt still held their source versions. Retrying from the same CD
completed each transaction. A second invocation reported the package
already installed. The forward update kept the existing daemon running
until an explicit restart.

At that restart v4 appended to the default log. After a cold boot it
appended to the configured path `/var/log/xiri fam site.log`. The check
matched a startup line from the new daemon PID after a known marker. On
both graphical boots SGI File Manager subscribed to an empty directory
under the authenticated user's home. NetBSD created and deleted a file.
The kernel I/O trace of the vendor `fm` process contains both length-prefixed
FAM messages, read on the same socket and bearing its directory request
number. Both boots also exercised full-screen 4Dwm with winterm, the vendor
shell, and a separate NetBSD ctwm login through xdm.

On separate disposable disks, removal preserved an edited FAM rc.conf.d
file. A fresh v4 installation generated the single active setting
`xiri_famd=YES` at mode 0644 and installed the commented override in the
packaged example. Removing this tracked installation removed the pristine
enable file. Both fresh installers issued filetype warnings for
`gedit.open.fti` and `gedit.closed.fti`, which are absent from both
pinned vendor payloads.

The package rebuilt byte for byte. The host suite passed 94 tests. The two
release-specific upgrade ISOs and compressed qualification logs are under
`.work/installers/indy-11.99.11/fam-service/`. The three-boot runs used
private overlays and verified each published CHD's digest again after halt.
The original guest `fstat` check could not read the kernel descriptor table.
A second diagnostic selected a message FAM emits only when it receives a
watch. The recorded runs check the message emitted by `-d` at startup and
the original client's socket reads during a watch.

[Operator instructions](../NATIVE-PACKAGE.md#configure-the-fam-service-log-with-v4) ·
[Archive hashes and per-boot results](2026-11-24-indy-fam-service.json) ·
[Lab procedure](../../lab/native-package/README.md#fam-service-update)
