# Applications tab startup on the November 25 Indy images

Five of eight icons opened windows on 6.5.22f, including Acrobat’s first-run dialog. All four opened windows on 6.5.30f. The two editor icons start the same editor, and the two browser icons start the same browser.

A follow-up tested both Netscape icons with the optional Communicator files installed, qualified a local Mozilla homepage for new users, and traced Showcase on the original IRIX donor. [Browser results](2026-11-25-webjumper-homepage.md) · [Showcase graphics calls](2026-11-25-showcase-graphics.md).

We logged in through xdm as `xiritest` and double-clicked every visible icon on the Applications page of each Mozilla test image. Each launch used the vendor's stock preferences. We compared the user's process list and mapped X windows before and after each click, and closed each application before testing the next launcher. The two CHDs and their bundled IRIS executables matched their recorded SHA-256 hashes. All guest writes went to disposable copies. [Image details and launch commands](2026-11-25-mozilla-sigpoll.md#launch-the-test-images).

| Catalog icon | IRIX 6.5.22f import | IRIX 6.5.30f import |
| --- | --- | --- |
| `jot` | Opened NEdit, **Untitled** | Opened NEdit, **Untitled** |
| `nedit` | Opened NEdit, **Untitled** | Opened NEdit, **Untitled** |
| `Mozilla` | Opened Navigator, then a DNS alert | Opened Navigator, then a DNS alert |
| `mozilla` | Opened Navigator, then a DNS alert | Opened Navigator, then a DNS alert |
| `acroread` | Opened the Acrobat Reader 4.0 license dialog | Absent from tab |
| `AboutNetscapeMessenger` | No window or surviving process | Absent from tab |
| `NetscapeMail` | No window or surviving process | Absent from tab |
| `showcase` | Exited during IRIS GL startup | Absent from tab |

Both Mozilla icons point to browser launchers. Each was tested with the previous browser stopped. The first sample showing the titled 610×450 Navigator window came 66–77 seconds after the click on 6.5.22f and 52–54 seconds on 6.5.30f. These host-clock observations include the sampling interval. The alert says that `www.mozilla.org` could not be found. An earlier test loaded a local HTML page through each icon on both releases. [6.5.22f screenshot](2026-11-25-applications-mozilla-stock-6.5.22f.png) · [6.5.30f screenshot](2026-11-25-applications-mozilla-stock-6.5.30f.png) · [Local page test and offline setup](2026-11-25-mozilla-sigpoll.md#open-a-local-page-on-the-manual-image).

Acrobat displayed its 699×648 license dialog after its splash screen. We stopped there on this run. The earlier document check covers PDF rendering, and the earlier editor check covers saving a file from NEdit. [License dialog screenshot](2026-11-25-applications-acrobat-startup.png) · [PDF rendering](2026-11-04-irix-acrobat.md) · [Editor save test](2026-11-24-indy-applications.md).

The two Netscape entries are WebJumper documents. For each double-click, a filesystem trace recorded lookups for `/emul/irix/usr/sbin/launchWebJumper` and `/usr/sbin/launchWebJumper`. Both paths were absent. These manual images include the optional Mozilla runtime. The separate Communicator import was tested previously on disposable copies. [Communicator import and startup results](2026-11-24-indy-mozilla.md).

Showcase started and looked for `/emul/irix/dev/graphics` and `/dev/graphics`. It left no window. Running the same executable as `xiritest` on the same display produced `ERROR #114  _GLgetfd : Cannot Open Graphics: ERR_NOGRAPHICS` and exit status 0. All three silent launches were sampled for 46–48 seconds. None left a new user process. [Per-click observations, process IDs and path lookups](2026-11-25-applications-recheck.json).
