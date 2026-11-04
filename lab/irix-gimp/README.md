# GIMP startup and full signal masks

The [work log](../../docs/results/2026-11-03-irix-gimp.md) records the current
boundary. Original GIMP executable, libraries, resources and guest images
remain under ignored `.work`; no success is implied by resource staging.

`signal-trace.c` is a native NetBSD diagnostic. It checks the imported GIMP
entry and n32 libc sigaction instructions, records action/return bytes, and
kills/reaps its tracee. Hash the executable and libc against the report
before use. Its input is `--signals UID GID ENV_FILE EXECUTABLE [ARGUMENTS]`;
provide an `input.txt` file. stdout/stderr are captured separately. This is
not a generic tracer or a normal way to launch the application.

Build focused independent signal fixtures with:

```sh
python3 scripts/build-irix-gimp-signals.py
python3 scripts/probe-irix-gimp-signals-reference.py
```

The reference runner clones the supplied original IRIX disk, verifies all
fixture uploads, captures 80 executions and shuts down its guest. It shares
the established signal-reference protocol. Existing historical fixtures and
oracles are retained unchanged. Use the run directory printed by the runner
in `qualify-irix-gimp-signals.py`. Native execution uses the existing bounded
`lab/irix-process/runner.c`; real/effective IDs are set by that native parent.
The qualifier checks the wider IRIX mask before reusing the established
frame/return oracle for all remaining fields. `--diagnostic` permits inspecting
records before guest shutdown; final qualification requires `--native-run`.

`stage-irix-gimp.py` reads the supplied IRIX installation with `ro,norecovery`
and creates `.work/irix-gimp-resources/{payload.tgz,manifest.json}`. It imports
the original data/configuration/plugins and resolves their static libraries
against the existing installed-desktop inventory. The manifest records every
source, destination, hash and mode; original ELF files use the existing 0555
import policy. It excludes user settings and installation databases.
Installing this payload in a disposable guest is separate from staging it.

GIMP acceptance includes actual UI interaction, saved/reopened image data,
normal exit and catalog launch. Check process state, CPU time and descendants
for launches without a window. Preserve the qualified winterm image until a
replacement passes; shut down every owned IRIS instance after the cycle.

The [signal report](../../docs/results/2026-11-03-irix-gimp-signals.json) now
records 80 paired full-mask observations, 80 regression records and four
native controls with clean guest shutdown. The separate
[application report](../../docs/results/2026-11-03-irix-gimp.json) records the
first successful editing and save/reopen cycle, including matching decoded
XCF/PNG pixels, both launch routes, normal exit and the complete resource
verification. The later [preference cycle](../../docs/results/2026-11-04-irix-preferences.md)
adds measured rename support and verifies preference saving, an exact backup
and relaunch. Most plug-ins have not been exercised.

For a new image, prepare a disposable seed from the qualified winterm bundle,
then use `prepare-xiri-xdm-image.py --keep-accounts --gimp-resources
.work/irix-gimp-resources --kernel-build .work/netbsd-gimp-build --baseline
lab/irix-gimp/baseline.json --seed <prepared-seed>`. The preparer verifies
archive contents, hashes, ownership, modes and link targets. It installs the
resources before the runtime so the unused native freeware prefix can be
published. `build-xiri-image.py` includes the resource ledger in the bundle.
Use a fresh output directory and perform the separate direct-CHD checks.

The resulting [manual image](../../docs/results/2026-11-03-irix-gimp.md#fresh-chd-and-manual-testing)
has a separate [fresh GIMP observation](../../docs/results/2026-11-03-irix-gimp-cold.json)
and [xdm/desktop qualification](../../docs/results/2026-11-03-irix-gimp-image.json).
Resource-stage records retain their staging status; the application reports
establish which paths were actually exercised.

To repeat the UI check, log into xdm as xiritest and run `gimp` in winterm.
Accept the five default Continue steps on [first run](../../docs/results/2026-11-03-gimp-first-window.png). Create a 256×256 RGB
image with Ctrl+N, paint visible strokes, and save it as XCF with Ctrl+S.
Use the image's right-click File / Save As menu to save PNG; GIMP 1.2 has no
default Ctrl+Shift+S shortcut. Accept the PNG plug-in dialog, quit normally,
and launch GIMP by double-clicking its Freeware entry. Open both files with
Ctrl+O, inspect their content, then quit and verify the main process and
Script-Fu descendant are gone. Keep generated settings in the native user's
home; do not copy a reference image's user profile.
