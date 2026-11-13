# Document integration checks

These checks exercise the original IRIX File Manager and file-type rules on
the qualified NetBSD/Xorg desktop. Vendor executables, rule files and artwork
remain private under `.work/`. The maintained runtime adds a native NetBSD
application type; the fixture exercises it alongside the imported rules.

Keep three paths separate:

1. Double-clicking a document invokes its `CMD OPEN` rule.
2. Dropping a document onto an application icon invokes that icon's `CMD DROP`
   rule, when it accepts the drop.
3. Dropping into an already running application uses that application's drag
   protocol and accepted data types.

Use disposable files and application links in the test account's own home.
Check the document contents, arguments, process identity and surviving files;
a new PID or window alone does not establish that a document opened correctly.
Keep failed gestures and setup attempts separate from acceptance results.

`input.c` provides paced native XTest gestures relative to a named window or
numeric window ID. `pointer` reports the X server's coordinates independently
of an emulated hardware cursor's changing hotspot. Examples:

```sh
cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include input.c \
    -L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib -lX11 -lXtst -o doc-input
./doc-input pointer
./doc-input 'window title' drag 2 100 125 960 125
./doc-input 'window title' click 1 100 125
./doc-input 'window title' double 1 130 125
./doc-input 'window title' key Ctrl+q
./doc-input 'window title' place 20 100 550 480
```

The drag arguments are button, source x/y and destination x/y. Both points
are relative to the source window; the destination may be outside it. The
helper waits at the destination before releasing the button. It does not
implement a drag protocol, invoke a file-type action directly, or fabricate
an application response.

The original behavior is described in SGI's
[file-type rules](https://techpubs.jurassic.nl/library/manuals/2000/007-2006-130/sgi_html/ch13.html)
and [desktop variables](https://techpubs.jurassic.nl/library/manuals/2000/007-2006-100/sgi_html/apb.html).

## Repeating the qualified paths

On a packaged image containing the runtime changes and imported compiler:

```sh
python3 scripts/probe-xiri-documents.py --bundle PATH/TO/BUNDLE --local-processes
```

Use `--local-processes` only with the documented Distrobox adapter sharing the
host process namespace. The probe clones the CHD, boots a graphical Xorg/xdm
session, compiles its native input/selection helpers, and uses the original
Utilities saved-file format for different editors under both IRIX accounts.
Each desktop user writes their own fixture settings through winterm; the
original panel's GUI saving is a separate development observation. It checks
fresh-login environment values, cancelled and completed native icon drops,
original gedit's exact document content through Copy, native xedit document
Open, logout cleanup and first-user settings after the second user's session.
PNGs require visual review for the native editor's displayed content. The
probe records hashes, commands, checkpoints, identities and clean halt;
it does not promote an image by itself. Retire its private CHD/diff and ISO
after saving the evidence.

The PDF/GIMP checks are separate observed workflows: copy the imported
`/emul/irix/usr/adobe/Acrobat4.0/Reader/Acrobat.pdf` into a private test folder,
open it from File Manager, and finish Reader's first-run license dialog.
For PNG, choose GIMP in Utilities, open a disposable image, and finish GIMP's
original first-run wizard. Test a drop onto a link to `gimp` after closing
GIMP. Preserve filenames with spaces and compare file hashes before/after.
An application icon's Drop action and a drop into its running window must
have separate results.

`type-fixtures.py OUTPUT` generates inert ELF32 headers and expected native
classification. It never executes them. Run both filename and file-descriptor
classification through the original library using
[`lab/irix-filetypes/fixture.c`](../irix-filetypes/fixture.c). Cases cover
interpreter placement, mode, class/endian/machine, malformed bounds and shared
library controls. The original library is the classifier oracle; a Python
reimplementation is not used for the result.

`cancel-drag` has the same arguments as `drag` and presses Escape before
releasing the pointer button. `input.c` tolerates a child disappearing during
window-tree lookup and selects only visible windows; 4Dwm may keep a hidden
icon window with the same title. `place` moves/resizes that visible client
using x, y, width and height. Target and gesture errors still fail the operation.
