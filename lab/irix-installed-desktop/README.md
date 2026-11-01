# Installed-image applications and Icon Catalog

Import the installed image's existing application payload and registration,
then qualify execution and catalog actions on NetBSD. Installer support is
deferred, not treated as complete by copying files.

[manifest.json](manifest.json) records 166 catalog entries across 17 pages,
including 21 Freeware entries and the existing xmahjongg link. Of the 166
targets, 152 resolve to files, one is a directory, and 13 do not resolve as
files in the original image. Some link names contain command arguments;
non-resolution is not by itself proof of a broken original action.

The private inventory follows resolved ELF dependencies and script
interpreters, and has no unresolved static `DT_NEEDED`/interpreter edges.
It also extracts:

- `/usr/lib/desktop/iconcatalog`, preserving page and launcher links;
- `/usr/lib/filetype`, including installed rules, compiled tables and icons;
- `/usr/lib/X11/app-defaults` and `/usr/lib/X11/schemes`;
- selected system desktop defaults and XDM icon/device lists;
- `/usr/freeware/share/xmahjongg` and its `/usr/lib/images` icon.

The payload contains 1,951 unique paths and 238,745,814 regular-file bytes.
One double-slash alias is deduplicated after checking its hash. Original
symlink text is preserved. No host absolute symlinks are created during
extraction; tar members are checked against traversal and symlink parents
before packaging under `emul/irix`. File modes retain the executable bit,
make resources readable, and omit set-id bits.

Static closure does not establish full runtime closure: programs may need
additional data, script-invoked commands, delayed libraries or services.
Only xmahjongg's application-specific data tree is included in this first
experiment. Other catalog entries are inventory candidates, not certified
working applications. Linked defaults outside the collected trees may need
their own dependency follow-up.

The source is the previously ingested installed `irix65.chd`, exposed
read-only as `.work/irix-reference/media/irix65.raw` with `ro,norecovery`.
Vendor bytes, archives and complete inventories remain in ignored `.work`.
Public files contain paths, hashes and derived metadata. Old user layouts
are inventoried separately; the test creates fresh native state under
`/usr/people/xiritest`.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/inventory-irix-installed-desktop.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/stage-irix-installed-desktop.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-installed-desktop.py
```

The probe clones the stopped desktop-pipe guest and checks every imported
regular-file hash and catalog/resource link inside it. Original 4Dwm,
xmahjongg and Icon Catalog run against native Xvfb. It records traces and an
XWD capture, checks native execution/X before and after, and uses the
reserved-UID supervisor to remove descendants before halting. A visible
window still requires interaction, catalog launch and persistence checks.

The first attempt `ordinary-6q1wpc55` imported and verified the entire
payload, then stopped at native X font setup: its old temporary font
directory was absent after boot. It halted cleanly. The corrected probe
recreates the 22 already pinned Screen fonts and their index each boot.
To reuse that imported seed without re-extracting the archive:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-installed-desktop.py \
  --staged-seed .work/irix-installed-desktop/runs/ordinary-6q1wpc55
```

A staged seed must have halted cleanly with a verified payload, matching
kernel pin and payload manifest. The final resume path hashes the entire
stopped seed disk and its clone on the host before boot and requires exact
equality. It checks the kernel/native control and every imported link again
in the guest. The seed's prior full-file verification remains pinned; this
avoids rehashing hundreds of megabytes inside the emulated CPU.

The second attempt `ordinary-_ul719fn` reverified all imported files and
passed font setup, then the native control exposed a missing `input.txt` in
the new harness. It halted cleanly before foreign application launch. The
corrected harness creates this runner input explicitly; both setup failures
remain diagnostics, not application compatibility results.

## Prepared baseline

The final import run `ordinary-w6lzsg5x` observes original xmahjongg rendering
under 4Dwm, with native execution/X controls, full import provenance and
clean descendant removal. Icon Catalog remains Blank. The preceding
`ordinary-o5u6xm80` exposed mode-0644 libraries rejected by SGI_ELFMAP
`VEXEC`; [permissions.json](permissions.json) records the explicit ELF 0555
adjustment. Persistent native fonts and manual session helpers are installed
in the stopped seed.

Use the [reusable image guide](../../docs/XIRI-IMAGE.md) for routine tests and
manual IRIS use. Fresh inventory/staging commands above are bootstrap work.
The [copy ledger](copy-ledger.json) records 1,990 source/destination entries;
[IRIX-IMPORT.md](../../docs/IRIX-IMPORT.md) explains placement and generated
state, plus the verified SGI documentation for catalog registration.

[prismatic.cfg](prismatic.cfg) is a template to copy beside the CHD. It uses
Prismatic's own schema; its machine state/NVRAM must also select the NetBSD
loader. See the [Prismatic boot result](../../docs/results/2026-11-02-prismatic-xiri.md)
and [switching instructions](../../docs/XIRI-IMAGE.md#return-to-irix).
