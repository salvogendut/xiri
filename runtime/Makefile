# Build natively on NetBSD; imported libraries/fonts are separate prerequisites.
CC?=cc
CFLAGS?=-O2
WARN=-Wall -Wextra -Werror
BUILDDIR?=build
PROGRAMS=$(BUILDDIR)/session-guard $(BUILDDIR)/x11-check $(BUILDDIR)/shell-handoff
all: $(PROGRAMS)
$(BUILDDIR):
	mkdir -p $(BUILDDIR)
$(BUILDDIR)/session-guard: libexec/session-guard.c
	mkdir -p $(BUILDDIR)
	$(CC) $(CFLAGS) $(WARN) libexec/session-guard.c -o $@
$(BUILDDIR)/x11-check: libexec/x11-check.c
	mkdir -p $(BUILDDIR)
	$(CC) $(CFLAGS) $(WARN) -I/usr/X11R7/include libexec/x11-check.c -L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib -lX11 -o $@
$(BUILDDIR)/shell-handoff: libexec/shell-handoff.c
	mkdir -p $(BUILDDIR)
	$(CC) $(CFLAGS) $(WARN) libexec/shell-handoff.c -o $@
install: all
	BUILDDIR=$(BUILDDIR) sh ./install.sh
clean:
	rm -f $(PROGRAMS)
