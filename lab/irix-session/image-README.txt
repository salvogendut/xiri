
Saved desktop sessions:
Open Toolchest -> Desktop -> Customize -> Windows.
Save Windows & Desks -> Continuously saves the running apps at logout.
Explicitly -> Set Home Session keeps a chosen startup collection instead.
The first login starts winterm, xclock and Icon Catalog. Subsequent logins
restore the saved list and layout; closed apps stay closed in continuous mode.
Toolchest and desktop icons always start. Restored winterms open fresh native
shells in the user's HOME; shell jobs and unsaved documents are not resumed.

Log out before rebooting or shutting down. Rebooting with an active desktop
can close X before its save completes, losing the latest layout changes.
Each user keeps separate files under ~/.desktop-127.0.0.1/0.0/ on this image:
4Dwmsession, 4Dwmdesks and 4Dwmdeskname. Back them up while logged out.
See docs/IRIX-SOFTWARE.md#saved-desktop-sessions for reset instructions.
