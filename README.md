# Xiri

Xiri runs original IRIX applications and desktop components on NetBSD and
X.org. The long-term target is a maintained operating system for real SGI
workstations; current development uses an R4400 Indy in the IRIS emulator.
Our reference is **IRIX 6.5.22m**. Other releases and physical hardware need
separate qualification.

The current desktop runs original 4Dwm, Toolchest, Icon Catalog, File Manager,
winterm and xclock. It has SGI fonts, the granite backdrop, desktop icons,
catalog launches and running-icon feedback. Native NetBSD Xorg drives a
1280×1024 accelerated Newport display. The latest image fixes xmahjongg's
texture corruption and passes launch, move/undo, redraw and logout checks.
See the [rendering results](docs/results/2026-11-03-newport-xmahjongg.md).

The manual launcher starts services as root and runs the desktop as
**xiritest**, UID 1234, with HOME and initial directory `/usr/people/xiritest`.
Normal xdm login is planned. The compatibility personality is currently
built into our custom NetBSD kernel.

## Run the current image

With the local image bundle and development dependencies already prepared:

```sh
./xiri status
./xiri doctor
./xiri run
```

Log in as `root` and run `xiri-desktop`. Log out through Toolchest or 4Dwm.
The [manual image guide](docs/XIRI-IMAGE.md) covers PROM settings, Prismatic,
boot troubleshooting and the exact image provenance. `./xiri run` uses the
selected bundle's tested emulator and preserves manual overlays and NVRAM.

Images, imported IRIX files, toolchains and build outputs remain local under
`.work/`; cloning this repository alone does not supply them. The
[import ledger](docs/IRIX-IMPORT.md) records what was copied from the supplied
IRIX image and where it belongs.

## Develop and check

```sh
./xiri check                 # disposable CHD boot, desktop checks and PNG
./xiri seed                  # reusable raw seed for more focused probes
./xiri build kernel --dry-run
./xiri build iris --dry-run
python3 -m unittest discover -s tests -v
```

The [development guide](docs/DEVELOPMENT.md) explains these commands, image
packaging and logs. Defaults live in [config/development.json](config/development.json);
artifact selection comes from the [current image pointer](lab/irix-installed-desktop/image.json).
New builds use separate output directories and do not replace qualified images.
Use the `xiri` integration branches for both forks, following the
[fork workflow](docs/FORKS.md). This lab repository uses `main`.

## Remaining work

Compatibility is incomplete. Winterm has intermittent startup/font-metric
quirks; broader graphics operations, Dumpster actions, preferences and session
persistence need work. GIMP signal registration and xosview statistics remain
application-specific gaps. The user's broader desktop survey is encouraging,
but it is not a per-application qualification.

The next packaging phase is a boot-loadable compatibility module modeled on
`compat_linux`, configured userspace services, and normal `xiritest` desktop
login through xdm, followed later by original IRIX clogin. The
[roadmap](docs/ROADMAP.md) defines the dependency and acceptance work.

- [Architecture](docs/ARCHITECTURE.md): kernel, imported runtime, native services and desktop boundaries.
- [IRIX resources](docs/IRIX-RESOURCES.md) and [software/home layout](docs/IRIX-SOFTWARE.md).
- [Newport graphics](docs/NEWPORT.md) and [desktop reference](docs/IRIX-DESKTOP-REFERENCE.md).
- [Emulation setup](docs/EMULATION.md) and [platform feasibility](docs/FEASIBILITY.md).
- [Historical checkpoints](docs/HISTORY.md) and [dated evidence](docs/results/).
