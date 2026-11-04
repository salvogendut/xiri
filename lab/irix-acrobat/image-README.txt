
GNOME and Acrobat application update
-----------------------------------
This image includes the cumulative pathname Unix sockets, GNOME PTY helper,
original-shell terminal attributes and preference-saving support. GNOME
Terminal and gedit now save their settings; GIMP saves preferences and keeps
its previous gimprc as gimprc.old. First-run user settings remain fresh.

The complete original Acrobat Reader 4 installation is under
/emul/irix/usr/adobe/Acrobat4.0, with /usr/adobe exposing that prefix to native
utilities used by its unchanged launcher. The IRIX desktop session supplies
ACRO_CONFIG=mipsirix. Open acroread from the Applications catalog tab.
The bundled sample document is /usr/adobe/Acrobat4.0/Reader/Acrobat.pdf.

The module contains the cumulative fixes, including the older Reader's ELF
layout. Review the separate application and cold-boot reports before treating
other programs or plug-ins as qualified. A first-run dialog is normal.

Known limit: Reader launches and displays PDFs, but its Icon Catalog artwork
does not change to the running shape. Broader documents, printing and browser
integration remain unqualified.
