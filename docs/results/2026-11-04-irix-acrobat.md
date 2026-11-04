# Original Acrobat Reader 4 on NetBSD/Xiri

The unchanged IRIX Acrobat Reader 4 now opens and renders a PDF, changes page
and zoom, reopens the document through its file chooser and exits normally as
xiritest. Its [sample screenshot](images/2026-11-04-acrobat-pdf.png) shows
original text and images on the NetBSD/Xorg desktop. These are bounded checks,
not general PDF, printing, browser-integration or plug-in qualification.

## Executable and library layouts

The complete package exposed a second boundary after the survey's missing
`acroread.dist`: native exec rejected the actual Reader with ENOEXEC. The
measured executable has exact flags `0x4` (o32 MIPS-I CPIC), 4 KiB load
alignment and a PT_PHDR whose memory size is zero while its file size covers
all program headers. Some bundled libraries also place initialized RW data
at a 4 KiB file offset that is incongruent with an 8 KiB virtual boundary.

NetBSD `xiri` commit `2ca3d76a4384cd73dbef1bd09b9cace12afadf41` supports
these bounded layouts in `compat_irix_o32.kmod`. The main-image validator
retains metadata containment, ABI, virtual native-page alignment, extent,
entry-point, protection and nonoverlap checks. Other unknown flags and
malformed layouts remain rejected. The native ELF mapper already has a
read-copy path for smaller declared alignment; no core-loader change is needed.

For library mapping, an incongruent RW segment uses owned anonymous pages
plus a file read, with zero BSS and the existing rollback journal. Native
vnode permissions, occupied mappings and private backing-file semantics are
preserved. Existing congruent subpage mapping and bounded relocation remain.
This is not unrestricted ELF-format support.

The module hash is
`37c8a5114483ad834d0dbef551175e506a1874599aa8caf70366481be7559b2f`.
The [build ledger](../../lab/irix-acrobat/build.json) records its exact source
inputs and equivalent commit. The [baseline](../../lab/irix-acrobat/baseline.json)
retains the qualified core, boot kernel and emulator. The module includes the
preceding Unix sockets, original-shell terminal support and
[preference rename](2026-11-04-irix-preferences.md).

## Resource and launcher integration

The [resource ledger](../../lab/irix-acrobat/resources.json) records 86 paths:
62 files, 17 directories and seven links. The original `/usr/adobe/Acrobat4.0`
tree and missing `/usr/lib/libMrm.so.1` dependency are staged beneath
`/emul/irix`. Original bytes and link targets are retained; ELF files use the
existing 0555 policy. Fonts, libraries, app-defaults, plug-ins and documentation
remain in their original relative layout. No user profile is copied.

The original wrapper calls native utilities with `/usr/adobe` pathnames.
The runtime installer therefore exposes `/usr/adobe -> /emul/irix/usr/adobe`
only when that native prefix is unused. Existing native directories or links
are preserved. The desktop exports the wrapper's existing
`ACRO_CONFIG=mipsirix` option, leaving native uname unchanged.

## Validation

The final module passes **174 executable and 340 library-mapping executions**
under root and UID/GID 1234. These retain all 70 earlier executable and 74
library cases and add legacy positive and negative cases. They check actual
output/exit, executable text, initialized data, writable zero BSS, protection
faults, repeat mappings, collisions, input-file preservation and process-group
cleanup. A private chroot isolates each loader test's synthetic interpreter
from the real guest libc. The module build's symbol/relocation audit passes.

The [final ELF qualification](2026-11-04-irix-acrobat-elf.json) preserves every
execution record. The [44 new original-IRIX observations](../../lab/irix-acrobat/reference.json)
use identical fixture bytes for the eleven new library layouts, both ABIs
and both identities. Non-address record fields agree; relocation addresses
follow the previously declared bounded native placement policy. The original
reference, earlier 508-case candidate and final 514-case guest halt cleanly.
Fixture hashes still match after the native runs, and the source CHD remains
unchanged. Image acceptance is recorded separately. The [lab guide](../../lab/irix-acrobat/README.md)
contains reproduction commands and fixture scope.

The original bundled `Reader/Acrobat.pdf` has nine pages, is 226,035 bytes and
hashes to `f1bc498f742ca8f72f22cf650a43584494b41e1b2eb24b7e2d8d626eab758c9a`.
A byte-identical copy in xiritest's home is used for the file-chooser check.
The first page renders text and images at 127%; Next displays page 2, and
Actual Size changes the display to 100%. Close/Open through the original
file chooser returns to page 1. File/Exit reports status 0, no signal or
forced stop, and all eleven tracked processes absent. Native X remains ready.

Earlier filename-typing attempts appended to the existing path in the Motif
chooser and produced ENOENT. The final check selects the real file from its
list. An initial exploration also reaches its explicit 900-second guard
limit; that forced stop is retained as a diagnostic, not a normal-exit pass.
A frame-stability wait times out during one capture; subsequent PNGs force
fresh compositor readback. No graphical equivalence to original IRIX is claimed.

## Catalog and remaining behavior

After a fresh xdm login with the maintained session launcher, double-clicking
Applications / acroread starts Reader as UID/GID 1234. Its file chooser opens
the same [PDF in the catalog-launched window](images/2026-11-04-acrobat-catalog-document.png).
Ctrl+Q removes the process and document window; native X remains ready. The
[application evidence](2026-11-04-irix-acrobat.json) retains process identities,
window observations, normal direct-launch exit, screenshots and clean halt.
FAM, rpcbind and xdm survive the logout/relogin with unchanged service PIDs.

The catalog's opened-icon feedback **does not pass** for Acrobat. The 54×55
icon crop is byte-identical before launch and while Reader is visibly running.
FAM logs Exists/EndExist for the wrapper but no Executing event. The wrapper
executes `acroread.dist`; a script-to-executable tracking gap is a plausible
explanation, not an established cause. Keep this separate from the working
catalog launch and PDF operations. Hidden 1×1 windows also use the name
Acrobat, so window-name lookup alone is not a valid readiness check.

Broader PDFs, printing, browser integration and individual plug-ins remain
unqualified. The original package includes those resources; presence alone
does not establish working behavior.
