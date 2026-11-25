# Applications in the v5 Indy Icon Catalog

Each test used a private copy of the CD 4 Indy image, its matching 6.5.22f
or 6.5.30f import, and an xdm login as `xiritest`. We selected Applications
and double-clicked every visible entry. We compared the X window tree and
the user's process list before and after each launch. For silent exits we
also traced the launch or captured the program's own diagnostic on the
same authenticated display.

For Mozilla on private copies with the optional browser payload and matching kernel, see the [threaded heap checks](2026-11-25-threaded-break.md), [original IRIX worker comparison](2026-11-25-irix-event-workers.md), [Applications lock retest](2026-11-25-irix-usync.md), [stack-guard retest](2026-11-25-irix-stack-guard.md) and [signal-wait and local X socket diagnosis](2026-11-25-mozilla-event-diagnosis.md).
The [Mozilla test-image report](2026-11-25-mozilla-sigpoll.md) covers the current module, offline startup and post-load CPU use.

| Catalog entry | 6.5.22f | 6.5.30f | Observed result |
| --- | --- | --- | --- |
| `acroread` | Opens | Absent | The initial two 1×1 X windows were followed by the Reader 4.0 splash and a 699×648 first-run license dialog. Earlier testing covered opening and displaying a PDF. |
| `jot` | Opens NEdit | Opens NEdit | The IRIX launcher starts `nedit`. Its first document window is titled **Untitled** and has X class `NEdit`. |
| `nedit` | Edits and saves | Edits and saves | We typed in the editor, used Save As and verified the saved contents and `xiritest` ownership under `/usr/people/xiritest` on both images. |
| `Mozilla`, `mozilla` | Both open on the Mozilla test CHD | Both open on the Mozilla test CHD | Both icons rendered an offline document with the matching runtime, current kernel module and per-user homepage. The original v5 survey returned “Cannot find mozilla runtime directory. Exiting.” because it lacked `run-mozilla.sh` and `mozilla-bin`. [Test conditions and screenshots](2026-11-25-mozilla-sigpoll.md). |
| `AboutNetscapeMessenger`, `NetscapeMail` | Both fail to launch | Absent | These are SGI WebJumper documents. Both clicks tried to execute `/usr/sbin/launchWebJumper` and received `ENOENT`. The first targets a local HTML file, the second a `mailbox:` URL. The 6.5.22f donor contains the helper and the referenced HTML file. |
| `showcase` | Exits during graphics startup | Absent | Direct launch on the same display printed `ERROR #114  _GLgetfd : Cannot Open Graphics: ERR_NOGRAPHICS` and exited 0. This binary uses SGI's legacy IRIS GL. The Xorg GLX check for SGI Clock exercises a different interface. |

There were eight visible entries on 6.5.22f and four on 6.5.30f.
The two editors sharing a window title and the two Mozilla launchers sharing
a failure account for much of the apparent duplication. A subsequent
[browser test on private v5 copies](2026-11-24-indy-mozilla.md) restored
the release-matched imports and traced the next startup failures. Showcase
still needs a separate IRIS GL investigation.

[6.5.22f Acrobat first-run dialog](2026-11-24-applications-acrobat.png)
· [6.5.30f saved editor document](2026-11-24-applications-nedit.png)
· [Earlier PDF rendering checks](2026-11-04-irix-acrobat.md)
