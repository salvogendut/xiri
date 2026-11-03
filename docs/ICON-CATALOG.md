# Icon Catalog application checklist

Next application pass after the GIMP cold-image run, requested on 2026-11-03.
The existing [source inventory](../lab/irix-installed-desktop/manifest.json)
contains 166 launchers in 17 system tabs from the supplied IRIX installation.
The running desktop reports 18 pages; inspect the additional page and reconcile
its contents during the pass. This list describes catalog registration,
not proof that each program or all its resources are present in Xiri.

For each launcher, record the tested image/module revisions, account, direct
execution and catalog double-click, time to the expected window or terminal
output, running-icon feedback, one useful action, normal exit and descendant
cleanup. Document and directory entries should open their assigned handler.
For a process without its expected UI, capture
CPU time/activity, children and logs before classifying it as slow or stuck.
Record missing resources, unsupported calls and crashes separately. Use bounded
actions for system tools and leave settings unchanged unless the test requires
an explicit, reversible change in its disposable guest.

Rows remain pending unless a current-image result is linked. Existing bounded results for
[GIMP](results/2026-11-03-irix-gimp.md),
[winterm](results/2026-11-03-winterm-reliability.md),
[xmahjongg](results/2026-11-03-newport-xmahjongg.md) and
[xclock time](results/2026-11-01-irix-time.md) remain evidence for their stated
checks; they do not qualify every launcher alias or wider application behavior.

## Alias (2)

| Entry | Original target | Current-image result / evidence |
| --- | --- | --- |
| `Maya6.5` | `/usr/aw/maya6.5/bin/Maya6.5` | Pending |
| `Maya6.5_Extras` | `/usr/aw/maya6.5/bin/Maya6.5_Extras` | Pending; inspect source target (not a resolved regular file) |

## AliasWavefront (4)

| Entry | Original target | Current-image result / evidence |
| --- | --- | --- |
| `dispatcher` | `/usr/aw/COM2.0/bin/dispatcher` | Pending |
| `Dispatcher.doc` | `/usr/aw/COM2.0/doc/dispatcher_html/Dispatcher.doc` | Pending |
| `Licenser` | `/usr/aw/COM2.0/bin/Licenser` | Pending |
| `mayalive4.0` | `/usr/aw/maya6.5/bin/mayalive4.0` | Pending; inspect source target (not a resolved regular file) |

## Applications (31)

| Entry | Original target | Current-image result / evidence |
| --- | --- | --- |
| `AboutNetscapeMessenger` | `/var/netscape/communicator/AboutNetscapeMessenger` | Pending |
| `acadr13` | `/opt/acad13/bin/acadr13` | Pending |
| `acroread` | `/usr/adobe/Acrobat4.0/bin/acroread` | Pending |
| `dia` | `/usr/freeware/bin/dia` | Pending |
| `evolution` | `/usr/freeware/bin/evolution` | Pending |
| `galculator` | `/usr/freeware/bin/galculator` | Pending |
| `gedit` | `/usr/freeware/bin/gedit` | Pending |
| `glynx` | `/usr/freeware/bin/glynx` | Pending |
| `gnome-terminal` | `/usr/freeware/bin/gnome-terminal` | Pending |
| `gnome-terminal --login` | `/usr/freeware/bin/gnome-terminal --login` | Pending; inspect source target (not a resolved regular file) |
| `gtop` | `/usr/freeware/bin/gtop` | Pending |
| `jot` | `/usr/sbin/jot` | Pending |
| `lyx` | `/usr/freeware/bin/lyx` | Pending |
| `maker` | `/usr/frame/bin/maker` | Pending; inspect source target (not a resolved regular file) |
| `MediaMail` | `/usr/bin/X11/MediaMail` | Pending; inspect source target (not a resolved regular file) |
| `midnight-commander` | `/usr/freeware/bin/midnight-commander` | Pending |
| `Mozilla` | `/var/netscape/mozilla/mozilla` | Pending |
| `mozilla` | `/usr/bin/X11/mozilla` | Pending |
| `nedit` | `/usr/sbin/nedit` | Pending |
| `NetscapeMail` | `/var/netscape/communicator/NetscapeMail` | Pending |
| `showcase` | `/usr/sbin/showcase` | Pending |
| `Wingz` | `/usr/bin/X11/Wingz` | Pending; inspect source target (not a resolved regular file) |
| `xboard` | `/usr/freeware/bin/xboard` | Pending |
| `xbuffy` | `/usr/freeware/bin/xbuffy` | Pending |
| `xearth` | `/usr/freeware/bin/xearth` | Pending |
| `xfig` | `/usr/freeware/bin/xfig` | Pending |
| `xmms` | `/usr/freeware/bin/xmms` | Pending |
| `xosview` | `/usr/freeware/bin/xosview` | Pending |
| `xpat2` | `/usr/freeware/bin/xpat2` | Pending |
| `xscreensaver-demo` | `/usr/freeware/bin/xscreensaver-demo` | Pending |
| `zsh` | `/usr/freeware/bin/zsh` | Pending |

## Collaboration (6)

| Entry | Original target | Current-image result / evidence |
| --- | --- | --- |
| `AboutNetscapeMessenger` | `/var/netscape/communicator/AboutNetscapeMessenger` | Pending |
| `inperson` | `/usr/sbin/inperson` | Pending; inspect source target (not a resolved regular file) |
| `MediaMail` | `/usr/bin/X11/MediaMail` | Pending; inspect source target (not a resolved regular file) |
| `NetscapeMail` | `/var/netscape/communicator/NetscapeMail` | Pending |
| `outbox` | `/usr/sbin/outbox` | Pending |
| `sgimeeting` | `/usr/bin/X11/sgimeeting` | Pending |

## ControlPanels (18)

| Entry | Original target | Current-image result / evidence |
| --- | --- | --- |
| `accessibility` | `/usr/sbin/accessx` | Pending |
| `audiopanel` | `/usr/sbin/audiopanel` | Pending |
| `background` | `/usr/sbin/background` | Pending |
| `colorscheme` | `/usr/sbin/colorscheme` | Pending |
| `desktop` | `/usr/sbin/desktop` | Pending |
| `display` | `/usr/bin/X11/xsetmon` | Pending |
| `iconviews` | `/usr/sbin/fmprefs` | Pending |
| `keyboard` | `/usr/sbin/keyboard` | Pending |
| `language` | `/usr/sbin/language` | Pending |
| `monpanel` | `/usr/sbin/monpanel` | Pending |
| `mouse` | `/usr/sbin/mouse` | Pending |
| `screensaver` | `/usr/sbin/screensaver` | Pending |
| `sounds` | `/usr/sbin/dtSounds` | Pending |
| `syserrpanel` | `/usr/sbin/syserrpanel` | Pending |
| `utilities` | `/usr/sbin/dtUtilities` | Pending |
| `videopanel` | `/usr/sbin/videopanel` | Pending |
| `webcontrol` | `/root/usr/sbin/webcontrol` | Pending; inspect source target (not a resolved regular file) |
| `windows` | `/usr/sbin/windows` | Pending |

## Demos (2)

| Entry | Original target | Current-image result / evidence |
| --- | --- | --- |
| `bzflag` | `/usr/freeware/bin/bzflag` | Pending |
| `bzfs` | `/usr/freeware/bzfs` | Pending; inspect source target (not a resolved regular file) |

## DesktopTools (24)

| Entry | Original target | Current-image result / evidence |
| --- | --- | --- |
| `clock` | `/usr/sbin/clock` | Pending |
| `colorview` | `/usr/sbin/colorview` | Pending |
| `desktophelp` | `/usr/sbin/desktophelp` | Pending |
| `enterlicense` | `/usr/etc/enterlicense` | Pending |
| `gr_osview` | `/usr/sbin/gr_osview` | Pending |
| `ical` | `/usr/sbin/ical` | Pending |
| `infosearch` | `/usr/sbin/infosearch` | Pending |
| `insight` | `/usr/sbin/insight` | Pending |
| `LicenseManager` | `/usr/etc/LicenseManager` | Pending |
| `mag` | `/usr/sbin/mag` | Pending |
| `mailbox` | `/usr/sbin/mailbox` | Pending |
| `makemap` | `/usr/sbin/makemap` | Pending |
| `notepad` | `/usr/sbin/notepad` | Pending; inspect source target (not a resolved regular file) |
| `rcpDevice` | `/usr/lib/desktop/rcpDevice` | Pending |
| `showmap` | `/usr/sbin/showmap` | Pending |
| `snoop` | `/usr/bin/snoop` | Pending |
| `SoftwareManager` | `/usr/sbin/SoftwareManager` | Pending |
| `xcalc` | `/usr/bin/X11/xcalc` | Pending |
| `xclock` | `/usr/bin/X11/xclock` | Pending |
| `xfontsel` | `/usr/bin/X11/xfontsel` | Pending |
| `xpsview` | `/usr/bin/X11/xpsview` | Pending |
| `xshowcmap` | `/usr/bin/X11/xshowcmap` | Pending |
| `xwininfo` | `/usr/bin/X11/xwininfo` | Pending |
| `xwsh` | `/usr/sbin/xwsh` | Pending |

## DeveloperMagic (6)

| Entry | Original target | Current-image result / evidence |
| --- | --- | --- |
| `cvbuild` | `/usr/sbin/cvbuild` | Pending |
| `cvd` | `/usr/sbin/cvd` | Pending |
| `cvmake` | `/usr/sbin/cvmake` | Pending |
| `cvperf` | `/usr/sbin/cvperf` | Pending |
| `cvstatic` | `/usr/sbin/cvstatic` | Pending |
| `swpkg` | `/usr/sbin/swpkg` | Pending |

## Freeware (21)

| Entry | Original target | Current-image result / evidence |
| --- | --- | --- |
| `abiword` | `/usr/freeware/bin/abiword` | Pending |
| `balsa` | `/usr/freeware/bin/balsa` | Pending |
| `CUPS` | `/usr/freeware/etc/cups/CUPS` | Pending |
| `dia` | `/usr/freeware/bin/dia` | Pending |
| `emacs` | `/usr/freeware/bin/emacs` | Pending |
| `fluid` | `/usr/freeware/bin/fluid` | Pending |
| `FreewareRelnotes` | `/usr/freeware/relnotes/shared/FreewareRelnotes` | Pending |
| `gedit` | `/usr/freeware/bin/gedit` | Pending |
| `gftp` | `/usr/freeware/bin/gftp` | Pending |
| `gimp` | `/usr/freeware/bin/gimp` | [Basic setup, edit/save/reopen, catalog launch and clean exit pass](results/2026-11-03-irix-gimp.md); preference backup and wider plug-ins remain open. |
| `glade` | `/usr/freeware/bin/glade` | Pending |
| `gnumeric` | `/usr/freeware/bin/gnumeric` | Pending |
| `grok` | `/usr/freeware/bin/grok` | Pending |
| `Maelstrom` | `/usr/freeware/bin/Maelstrom` | Pending |
| `nedit` | `/usr/freeware/bin/nedit` | Pending |
| `plan` | `/usr/freeware/bin/plan` | Pending |
| `xcdroast` | `/usr/freeware/bin/xcdroast` | Pending |
| `xchat` | `/usr/freeware/bin/xchat` | Pending |
| `xmahjongg` | `//usr/freeware/bin/xmahjongg` | Pending |
| `xmcd` | `/usr/freeware/bin/xmcd` | Pending |
| `xsane` | `/usr/freeware/bin/xsane` | Pending |

## Imaging (2)

| Entry | Original target | Current-image result / evidence |
| --- | --- | --- |
| `Eclipse` | `/usr/bin/Eclipse` | Pending |
| `www.formvision.de` | `/usr/Eclipse/etc/www.formvision.de` | Pending |

## ImagingTools (4)

| Entry | Original target | Current-image result / evidence |
| --- | --- | --- |
| `EcLink` | `/usr/bin/EcLink` | Pending |
| `EcMonitorSetup` | `/usr/bin/EcMonitorSetup` | Pending |
| `EcRender` | `/usr/bin/EcRender` | Pending |
| `EcWatch` | `/usr/bin/EcWatch` | Pending |

## Interoperability (1)

| Entry | Original target | Current-image result / evidence |
| --- | --- | --- |
| `tfxConfig` | `/usr/sbin/tfxConfig` | Pending |

## MediaTools (22)

| Entry | Original target | Current-image result / evidence |
| --- | --- | --- |
| `cdman` | `/usr/sbin/cdman` | Pending |
| `cdplayer` | `/usr/sbin/cdplayer` | Pending |
| `compview` | `/usr/sbin/compview` | Pending |
| `datman` | `/usr/sbin/datman` | Pending |
| `datplayer` | `/usr/sbin/datplayer` | Pending |
| `image_editor` | `/usr/sbin/imged` | Pending |
| `imgcopy` | `/usr/sbin/imgcopy` | Pending |
| `imginfo` | `/usr/sbin/imginfo` | Pending |
| `imgview` | `/usr/sbin/imgview` | Pending |
| `imgworks` | `/usr/sbin/imgworks` | Pending |
| `macromedia` | `/usr/sbin/macromedia` | Pending; inspect source target (not a resolved regular file) |
| `mediaconvert` | `/usr/sbin/mediaconvert` | Pending |
| `mediaplayer` | `/usr/sbin/mediaplayer` | Pending |
| `mediarecorder` | `/usr/sbin/mediarecorder` | Pending |
| `moviemaker` | `/usr/sbin/moviemaker` | Pending |
| `musicplayer` | `/usr/sbin/musicplayer` | Pending |
| `soundeditor` | `/usr/sbin/soundeditor` | Pending |
| `soundplayer` | `/usr/sbin/soundplayer` | Pending |
| `soundtrack` | `/usr/sbin/soundtrack` | Pending |
| `videoin` | `/usr/sbin/videoin` | Pending |
| `videoout` | `/usr/sbin/videoout` | Pending |
| `videopanel` | `/usr/sbin/videopanel` | Pending |

## Printing (3)

| Entry | Original target | Current-image result / evidence |
| --- | --- | --- |
| `printers` | `/usr/sbin/printers` | Pending |
| `PrintPanel` | `/usr/sbin/PrintPanel` | Pending |
| `PrintStatus` | `/usr/sbin/PrintStatus` | Pending |

## SupportTools (4)

| Entry | Original target | Current-image result / evidence |
| --- | --- | --- |
| `confidence` | `/usr/sbin/confidence` | Pending |
| `Embedded_Support_Partner` | `/var/esp/ssc/ESPartnerURL` | Pending |
| `Supportfolio_Online` | `/usr/share/WebMagic/jumpsites/Supportfolio_Online` | Pending |
| `SupportInfo` | `/usr/share/WebMagic/jumpsites/SupportInfo` | Pending |

## WebTools (12)

| Entry | Original target | Current-image result / evidence |
| --- | --- | --- |
| `AboutNetscapeMessenger` | `/var/netscape/communicator/AboutNetscapeMessenger` | Pending |
| `ApacheGuide` | `/var/sgi_apache/server/share/htdocs/ApacheGuide` | Pending |
| `InfoSearch` | `/usr/lib/infosearch/C/InfoSearch` | Pending |
| `mozilla` | `/usr/bin/X11/mozilla` | Pending |
| `netscape` | `/usr/bin/X11/netscape` | Pending |
| `NetscapeMail` | `/var/netscape/communicator/NetscapeMail` | Pending |
| `outbox` | `/usr/sbin/outbox` | Pending |
| `SiliconSurf` | `/usr/share/WebMagic/jumpsites/SiliconSurf` | Pending |
| `sitemgr` | `/usr/sbin/sitemgr` | Pending |
| `webjumper` | `/usr/sbin/webjumper` | Pending |
| `WebSetup` | `/var/www/htdocs/webface/WebSetup` | Pending; inspect source target (not a resolved regular file) |
| `WelcomeToWeb` | `/var/netscape/communicator/WelcomeToWeb` | Pending |

## WhatsNew (4)

| Entry | Original target | Current-image result / evidence |
| --- | --- | --- |
| `New_IRIX_Info` | `/var/www/htdocs/WhatsNew/New_IRIX_Info` | Pending |
| `sgimeeting` | `/usr/bin/X11/sgimeeting` | Pending |
| `WebSetup` | `/var/www/htdocs/webface/WebSetup` | Pending; inspect source target (not a resolved regular file) |
| `Welcome_to_SGI` | `/var/www/htdocs/WhatsNew/Welcome_to_SGI` | Pending |
