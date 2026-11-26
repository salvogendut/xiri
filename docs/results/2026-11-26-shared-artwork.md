# Freeware packages sharing the IRIX desktop filetype table

SGI File Manager reads icon artwork and double-click actions from
`/usr/lib/filetype/desktop.otr` in the IRIX runtime. Both xmahjongg and
UnZip 5.50 contribute rules to this file. The older installers each
saved the table that existed at the time of installation. Removing the
first-installed product after another changed the table could therefore
stop at the checksum check.

The helpers now save each desktop's original table once. While holding
both installer locks, they compile the installed rules with SGI's `fftr`
in a fixed order, then rename the finished table into place. Removing a
product rebuilds the table with the remaining rule. Removing the last
product restores the saved file byte for byte. An unrelated edit to the
live table stops package maintenance for review.

## Desktop checks on the two Indys

| First installed and removed | Action after the first removal | 6.5.22f R4400 | 6.5.30f R5000 |
| --- | --- | --- | --- |
| UnZip | Double-click xmahjongg in Icon Catalog’s Freeware tab. | [Game](2026-11-26-shared-artwork-6.5.22f-game.png) | [Game](2026-11-26-shared-artwork-6.5.30f-game.png) |
| xmahjongg | Double-click a ZIP in a writable File Manager folder. | [ZIP icon](2026-11-26-shared-artwork-6.5.22f-archive.png) · [After opening](2026-11-26-shared-artwork-6.5.22f-opened.png) | [ZIP icon](2026-11-26-shared-artwork-6.5.30f-archive.png) · [After opening](2026-11-26-shared-artwork-6.5.30f-opened.png) |

The game-first test uses an installation made by the previously shipped
supplement. The new UnZip helper adopts its existing artwork receipt.
The ZIP-first test installs UnZip 5.40, upgrades to 5.50 with Software
Manager, then installs xmahjongg. With both installed, the shared table
contains `XMahjonggExecutable`, `UnZipExecutable` and `ZipArchive`. Each
release produces the same combined checksum in either installation order.

File Manager opened the original SGI ZIP action on a copy of `sample.zip`
in the ordinary user's home. The action created a sibling directory named
`sample_extracted`. The check compares `sample.txt` in that directory
with the CD reference and checks its owner using NetBSD's `/usr/bin/stat`.

After removal of either product, the surviving table matches that release's
earlier single-product checksum. After both removals only the deliberately
retained Freeware shared index remains in SGI's inventory.
[Per-release checks and screenshot hashes](2026-11-26-shared-artwork.json)
· [How to install and remove both packages](../../lab/irix-installer/README.md#install-xmahjongg-and-unzip-together).
