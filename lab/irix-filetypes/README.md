# Original desktop filetype diagnosis

The missing icons had three independent causes: record locks rejected the
compiled database, missing seek support prevented correct executable-tag
reads, and native FAM reported imported executable targets as deleted.

`fixture.c` loads the supplied `libimdFtrDB` and asks for types by name, file
path and descriptor. `reference.sh` compiles/runs it on original IRIX. The
same n32 binary on NetBSD classifies xmahjongg as `XMahjonggExecutable`, xclock
as `XClock`, a directory as `Directory`, and passwd as `AsciiTextFile`.
These API observations are separate from executing the file's assigned action.

`trace.c` is an optional diagnostic interposer. It logs the three vendor API
results and delegates to the original library. It exposed the later change
from a correct application type to `DanglingReference`. It was used only in
a disposable guest, and is absent from the qualified desktop and image.

`XIRI_IRIX_ICONS` and `XIRI_IRIX_ICONS_O32` build the final kernel on the
NetBSD `xiri` branch. The two JSON pins record clean source revision,
configuration, kernel and emulator hashes. Build directories are
`.work/netbsd-irix-icons-build` and `.work/netbsd-irix-icons-o32-build`;
earlier lock-only builds and images are preserved.

`scripts/probe-xiri-desktop-icons.py` starts from the qualified graphical
seed, installs those kernel artifacts and the native FAM fix, verifies the
imported resource hashes, compares raw seeks to IRIX, and exercises original
Toolchest launches, catalog pages, native-home notifications and FileManager.
It captures the actual software-composed Newport framebuffer and halts.
The monitor compositor is refreshed after display changes to avoid retaining
an older framebuffer in this pinned emulator.

See [the icon result](../../docs/results/2026-11-02-desktop-icons.md),
[locking](../irix-filelocks/README.md), [seeks](../irix-lseek/README.md), and
[native FAM](../native-fam/README.md).
