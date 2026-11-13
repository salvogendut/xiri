
FILE MANAGER AND DUMPSTER

This image includes the filesystem statistics/removal module and the original
telldesktop helper. The hostname xiri-indy resolves locally through /etc/hosts.

Open your home directory with fm. Ctrl+N creates a folder; click an icon and
then its label to rename it; Ctrl+C makes a copy. Middle-drag between windows
to move a file, or onto Dumpster to discard it. Double-click Dumpster and drag
the file out to recover it. Toolchest -> Desktop -> Empty Dumpster permanently
removes its contents. Test with disposable files and keep originals elsewhere.

Each user has a separate home and Dumpster. The hidden .dumpster marker stays
after emptying. Cross-filesystem moves, collisions and remote filesystems need
separate checks. See docs/IRIX-FILEMANAGER.md in the Xiri repository for details.
