# Offline Mozilla startup and the Netscape Messenger catalog entries

On the two November 25 Mozilla Indy images, a new browser profile opened **Welcome to Xiri** offline. Reinstalling the defaults preserved a user's chosen homepage on both releases. On the 6.5.22f Applications tab, choosing Mozilla for WebJumper links opened the original **AboutNetscapeMessenger** document and launched the **NetscapeMail** icon into Mozilla's account wizard. [6.5.22f welcome page](2026-11-25-mozilla-welcome-6.5.22f.png) · [6.5.30f welcome page](2026-11-25-mozilla-welcome-6.5.30f.png) · [About Netscape Messenger](2026-11-25-webjumper-about.png).

## Try the prepared images

From the Xiri checkout, launch the 6.5.22f Indy to try both Messenger shortcuts.

```sh
.work/images/xiri-indy-6.5.22f-catalog-20261125/run-iris.sh
```

At xdm use `xiritest` for both username and password. Select **Applications** at the bottom left of the Icon Catalog and double-click **Mozilla**, **AboutNetscapeMessenger** or **NetscapeMail**. The expected windows are **Welcome to Xiri**, SGI’s illustrated About page and Mozilla’s **Mail & Newsgroups** account wizard. Allow up to two minutes for a cold browser launch. The catalog remembers its last page. A subsequent 6.5.22f test reproduced Navigator freezing after the welcome page painted. [Menu and keyboard retest](2026-11-25-indy-interaction.md).

To try the offline homepage on the 6.5.30f Indy, use the same login and double-click **Mozilla**.

```sh
.work/images/xiri-indy-6.5.30f-catalog-20261125/run-iris.sh
```

Each bundle has a standalone `netbsd-xiri.chd` and its matching Freeware CD 4. IRIS saves manual changes in a writable overlay on subsequent runs. Both disks passed `chdman verify` and cold-booted through xdm to the Icon Catalog as `xiritest`.

| Indy release | Standalone CHD SHA-256 |
| --- | --- |
| 6.5.22f | `07a98da5c15feddb47d7f48115f6da63caf06bf85e74b53bb83383ffec49b844` |
| 6.5.30f | `975dc03808d7341cbc94b07644d487a21952e976196da8d26ddb867984a44560` |

## Install the offline homepage

Start with the Mozilla Indy image for your release, or install the matching Mozilla payload and compatibility module. The two release profiles produce different vendor archives. Each new Mozilla import also writes `install-mozilla-defaults.sh` next to its archive and records the script's SHA-256 in `manifest.json` under `guest_setup`. [Test images and launch commands](2026-11-25-mozilla-sigpoll.md#launch-the-test-images) · [Build a release-matched browser import](2026-11-24-indy-mozilla.md#build-the-matching-payload).

For a previously built import, the same script is available in the checkout under `packaging/mozilla/`. Put it on guest-readable media. If Mozilla is already installed, only the second command is needed. Run these commands as root inside NetBSD.

```sh
tar xzpf /cdrom/payload.tar.gz -C /
sh /cdrom/install-mozilla-defaults.sh
```

The installer puts the HTML file in `/emul/irix/var/netscape/mozilla/` and seeds the browser's default and US new-profile templates. The IRIX browser opens `file:///var/netscape/mozilla/xiri-welcome.html`. It reads the standard Mozilla preferences header on 6.5.22f and uses a release-specific startup milestone. A repeat installation accepts identical files and reports a conflict if a local template differs. Existing users can choose the local URL themselves in **Edit → Preferences → Navigator**. [Installer source](../../packaging/mozilla/install-mozilla-defaults.sh).

For each release we used a disposable copy of its pinned Indy image, logged in as `xiritest` through xdm and double-clicked **Mozilla** with a fresh profile. Each displayed the local document in a 610×450 window. We then set a different local homepage in the user's profile, reapplied the installer, verified that the preferences file retained its checksum, and double-clicked **mozilla**. Both browsers rendered the user-selected page. Rebuilding both imports from their original donors reproduced the previous vendor archive hashes. [Earlier catalog results with stock profiles](2026-11-25-applications-recheck.md).

## Netscape Messenger on 6.5.22f

The original 6.5.22f Applications page has two WebJumper shortcuts. The 6.5.30f donor has neither. On 6.5.22f, install the optional Communicator import as well as Mozilla to get SGI's original `launchWebJumper`, Messenger document and artwork. Build the Communicator archive into its own output directory and extract it at the guest root, using the same procedure as for the browser. [Communicator profile](../../profiles/irix-6.5.22f-communicator-v1.json) · [Original IRIX reference](2026-11-24-indy-mozilla.md#what-the-xiri-user-sees-with-the-timer-fix).

With Communicator as the stock handler, both clicks started Netscape processes that consumed CPU. **AboutNetscapeMessenger** passed the correct local file URL. After 131 seconds it had only a 1×1 helper window. **NetscapeMail**, launched with the previous browser stopped, had a 5×5 component bar and a 1×1 helper after 106 seconds. Neither click produced a usable application on this run. An earlier run also saw a Message Center with blank dialogs. The first cause of Communicator's previously observed SIGBUS remains open.

### Use SGI Mozilla for both shortcuts

The 6.5.22f Mozilla import also emits `xiri-webjumper`. It passes the About file URL to SGI's browser and sends the bare `mailbox:` shortcut to SGI's own mail launcher. With a plain `WEBBROWSER=/usr/bin/X11/mozilla` assignment both URLs go to Navigator, and the Mail icon opens a browser window. [Launcher source](../../packaging/mozilla/xiri-webjumper).

Copy `xiri-webjumper` from that release's import output to the guest-readable media. As NetBSD root, install the executable alongside Mozilla.

```sh
install -m 555 /cdrom/xiri-webjumper /emul/irix/var/netscape/mozilla/xiri-webjumper
```

As the desktop user, set this assignment in `~/.desktop-$(hostname)/desktopenv`, preserving any other settings. Log out and back in through xdm so the catalog inherits the choice.

```sh
WEBBROWSER=/var/netscape/mozilla/xiri-webjumper
export WEBBROWSER
```

Double-clicking **AboutNetscapeMessenger** with a fresh Mozilla profile displayed the original SGI heading, artwork and links. An account with older Netscape preferences may first see Mozilla's profile migration prompt. Double-clicking **NetscapeMail** from a cold start opened Mozilla's 632×450 **Mail & Newsgroups** window and its 500×380 **Account Wizard**. Clicking **Next** advanced to the **Identity** form. We repeated the Mail click with the About page still open. The same Mozilla process displayed the wizard alongside Navigator. Sending and receiving mail remain untested. [About screenshot](2026-11-25-webjumper-about.png) · [Mail screenshot](2026-11-25-webjumper-mail.png).
