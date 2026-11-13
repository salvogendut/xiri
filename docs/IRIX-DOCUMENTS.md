# Opening documents on the IRIX desktop

File Manager uses the original IRIX file-type rules to choose an action for a
document. Double-clicking a document, dropping it onto an application icon,
and dropping it into a running application are three separate paths. A
working launch does not establish support for all three.

## Choosing an editor or image viewer

Open **Desktop → Customize → Utilities** in Toolchest, or run:

```sh
/emul/irix/usr/sbin/dtUtilities
```

Choose **Other** in the text-editor or image-viewer menu and enter the full
command. The tested choices are `/usr/freeware/bin/gedit` for text and
`/usr/freeware/bin/gimp` for images. Native `/usr/X11R7/bin/xedit` is also a
text-editor choice. An application may present its own first-run setup.

The panel saves `WINEDITOR`, `IMGVIEWER` and its other settings in
`$HOME/.desktop-$(hostname)/desktopenv`. File Manager notices changes during
the session. Xiri also loads this file at the next login, as the original SGI
Xsession does, so newly started clients inherit the same choices. Settings
belong to the logged-in account; each user can choose differently.

The PDF rule uses the imported Acrobat package rather than `IMGVIEWER`.
The document check opens the bundled Reader guide with Acrobat 4. Text and
PNG checks use disposable filenames containing spaces. Unsupported original
viewers such as `imgview` still need their separate application work.

## Dropping onto application icons

Put a link to the application in an Icon View, then drag a document onto
its icon. The target should turn blue before release. SGI's instructions
recommend clicking an unresponsive application icon once before retrying.
A drop onto empty folder space is a file move, so check the destination icon.

The original GIMP icon accepts the PNG fixture. Xiri adds a file-type rule
for dynamically linked native NetBSD/MIPS ELF32 executables, which IRIX's
older classifier otherwise mistakes for shared libraries when they use PIC.
The new rule recognizes the native ELF interpreter, retains the original
executable artwork, and supplies Open/Drop actions. Native xedit opens the
text fixture from its icon without moving the source document.

The installed gedit icon has a separate stale rule: its Drop action adds
`-f`, but this gedit version exits with “unknown option.” Double-clicking a
text document with gedit chosen in Utilities works. The original rule is
retained for the later application-association pass.

Running-window drops depend on the receiving application's drag protocol
and accepted data types. They are tracked separately in the
[document results](results/2026-11-13-documents.md); icon launching does not
imply universal drag-and-drop support.

## Installing or refreshing native file types

The [resource ledger](../lab/documents/resource-ledger.json) adds only the
original `/usr/sbin/fftr` compiler, installed at
`/emul/irix/usr/sbin/fftr`. Its libraries, the original rule database and
artwork were already imported. No IRIX user home is copied.

Extract this addition from the configured, read-only reference image with
`scripts/stage-irix-documents.py`. The image builder accepts its output through
`prepare-xiri-xdm-image.py --documents-resources .work/irix-documents-resources`.
A live runtime installation then invokes:

```sh
/usr/local/sbin/xiri-update-filetypes
```

Run it as root after importing the compiler, or after installing new native
rules. It merges `/usr/local/share/xiri/netbsd.ftr` ahead of the current
database, keeps the first database as `desktop.otr.before-xiri`, and replaces
the active table only after successful compilation. The updater serializes
its own runs and skips a rebuild when the rules and database hashes match
its saved state. Re-run it after another installer rebuilds the master table.
Log out and back in to reload the rules.

The original compiler calls `/usr/bin/nawk` through the native shell. The
updater creates that name as a link to NetBSD `awk` only if the path is absent;
it preserves existing administrator paths. A `DESTDIR` installation stages
the helper and source rule but cannot execute the compiler.

The native rule currently covers executable big-endian MIPS ELF32 files
with `/usr/libexec/ld.elf_so` in one of up to 32 program headers. Other
architectures, static executables and arbitrary application-specific drop
arguments need separate rules or qualification. Personal IRIX file-type
customization and printing remain later work.

## Sources and checks

- SGI's [file-type rules](https://techpubs.jurassic.nl/library/manuals/2000/007-2006-130/sgi_html/ch13.html)
  describe Open/Drop actions and their variables.
- SGI's [launching applications](https://techpubs.jurassic.nl/library/manuals/1000/007-1342-170/sgi_html/ch03.html)
  describes document drops and the target-icon feedback.
- The installed IRIX 6.5.22m `fftr(1)` manual and `Xsession.dt` provide the
  compiler grammar and saved-environment behavior used here.
- The [document lab](../lab/documents/README.md) records repeatable checks;
  [results](results/2026-11-13-documents.md) distinguish passes from remaining
  application and protocol limits.
