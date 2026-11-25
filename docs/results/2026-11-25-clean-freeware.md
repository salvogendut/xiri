# Installing from the complete SGI Freeware CD 4 on a clean Mozilla Indy

SGI’s original `inst` installed xmahjongg 3.6.1 on both clean Mozilla
desktops. After a reboot, double-clicking its Freeware icon as `xiritest`
opened the 1006×614 game. Removing the game cleared its SGI history and
catalog entry. Each browser then reopened the user's chosen local homepage.
[Manual installation and removal](../../lab/irix-installer/README.md#use-the-complete-freeware-cd-4-with-a-clean-mozilla-indy).

| Indy | Game launched from Freeware | Freeware after removal | Mozilla after removal |
| --- | --- | --- | --- |
| R4400 · IRIX 6.5.22f · Mozilla 1.0.1 | [Game](2026-11-25-clean-freeware-6.5.22f-game.png) | [Catalog](2026-11-25-clean-freeware-6.5.22f-removed.png) | [Saved homepage](2026-11-25-clean-freeware-6.5.22f-browser.png) |
| R5000 · IRIX 6.5.30f · Mozilla 1.7.12 | [Game](2026-11-25-clean-freeware-6.5.30f-game.png) | [Catalog](2026-11-25-clean-freeware-6.5.30f-removed.png) | [Saved homepage](2026-11-25-clean-freeware-6.5.30f-browser.png) |

## Source and transaction

Each test booted a private overlay on its [clean Mozilla CHD](2026-11-25-mozilla-installer.md).
The user-supplied May 2004 archive contains four extracted CD trees.
We read its XFS disk read-only and made a Rock Ridge ISO of the entire
`/cds/cd-4` tree. Both guests mounted it at `/mnt/freeware` and counted
144 product inventories. The eight game and index distribution files
matched the [recorded hashes](../../lab/irix-installer/inputs.json).
The release-specific supplement at `/cdrom` supplied the installer and
eight partial base subsystems from Foundation and the matching overlays.

Both guests started with empty SGI history. The game transaction used
`/mnt/freeware/dist` as its source. SGI reported zero conflicts and selected
only `fw_xmahjongg.sw.xmahjongg` and `fw_common.sw.index`. Its package hook
registered the game under **Freeware** and compiled its artwork. SGI warned
about CPU hardware and architecture identification and setting `vhdev` in
the subshell. These warnings appeared on both guests. Installation and removal
completed and the selected binaries ran.

After reboot, both guests retained the same six product, image and subsystem
rows. After removal, only the three `fw_common` rows remained. Each guest
regained its own original `desktop.otr` byte for byte and retained the
**FreewareRelnotes** link. The browser preferences, bookmarks, user homepage,
xdm session selector, kernel, boot wrapper, module, resolver service, account
database and both Xiri receipts kept their pre-install hashes. The [release
ledger](2026-11-25-clean-freeware.json) records the observations and input hashes.

## Graphical Software Manager

On both releases we opened SGI Software Manager 4.1 with `swmgr -n -r /emul/irix -f /mnt/freeware/dist`.
In **Customize Installation**, the full-disc default selection reported
99 conflicts. The list showed the shared utilities as **Same Version** and
new products including XEmacs and WindowMaker. [R4400 inventory](2026-11-25-clean-freeware-6.5.22f-swmgr.png)
· [R5000 inventory](2026-11-25-clean-freeware-6.5.30f-swmgr.png).

Changing **Available Software** to `/mnt/freeware/dist/fw_xmahjongg`
narrowed the inventory to the game. Its optional `fw_xmahjongg.man.relnotes`
required `fw_common.man.legal`. Choosing to omit the optional release notes
cleared the conflict. **Start** completed the dry run on both Indys.
The final checks found only the shared index in SGI history and confirmed
that the game executable and catalog link were still absent.
[Dependency dialog](2026-11-25-clean-freeware-swmgr-conflict.png)
· [R4400 dry run](2026-11-25-clean-freeware-6.5.22f-dry-run.png)
· [R5000 dry run](2026-11-25-clean-freeware-6.5.30f-dry-run.png).

The [live graphical follow-up](2026-11-25-swmgr.md) installed the same game
on both releases, launched it after reboot and restored the artwork on removal.
