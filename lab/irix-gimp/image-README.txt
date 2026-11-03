
GIMP 1.2.5 application check
--------------------------
This image includes the full-mask signal fix and original GIMP data, defaults,
plug-ins and canonical /sbin/sh. gimp-resources.json records the copied files.
No source-image user profile or package database is imported.

As xiritest, run gimp in winterm or double-click gimp on the Freeware page.
On first run, accept the five default Continue steps. Startup can take tens
of seconds while it reads brushes and queries plug-ins. Wait for The GIMP
toolbox; a PID or splash screen alone does not establish readiness.

Create an RGB image with Ctrl+N, paint strokes and save as XCF with Ctrl+S.
Use right-click on the image, File / Save As, and a .png filename to exercise
the PNG plug-in. GIMP 1.2 has no default Ctrl+Shift+S shortcut. Quit with
Ctrl+Q, relaunch, and use Ctrl+O to reopen both files. Save your work under
/usr/people/xiritest; generated GIMP settings live in ~/.gimp-1.2.

Known limits: the preference backup rename syscall is missing; first-run
output can report failure to rename gimprc to gimprc.old. Preference
persistence is unqualified. Shared-memory tile transport is disabled and
the tested path uses its fallback. Other plug-ins, large images, swapping,
overwrite/recovery and printing require separate checks.
