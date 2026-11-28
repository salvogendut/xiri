# Build natively on NetBSD; imported libraries/fonts are separate prerequisites.
CC?=cc
CFLAGS?=-O2
WARN=-Wall -Wextra -Werror
X11_CPPFLAGS?=-I/usr/X11R7/include
X11_LDFLAGS?=-L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib
BUILDDIR?=build
PROGRAMS=$(BUILDDIR)/session-guard $(BUILDDIR)/x11-check $(BUILDDIR)/shell-handoff $(BUILDDIR)/save-session $(BUILDDIR)/stop-sessions $(BUILDDIR)/drop-bridge $(BUILDDIR)/desktop-sound $(BUILDDIR)/cdromd $(BUILDDIR)/recorder-audio.so
all: $(PROGRAMS)
$(BUILDDIR):
	mkdir -p $(BUILDDIR)
$(BUILDDIR)/session-guard: libexec/session-guard.c
	mkdir -p $(BUILDDIR)
	$(CC) $(CFLAGS) $(WARN) libexec/session-guard.c -o $@
$(BUILDDIR)/x11-check: libexec/x11-check.c
	mkdir -p $(BUILDDIR)
	$(CC) $(CFLAGS) $(WARN) $(X11_CPPFLAGS) libexec/x11-check.c $(X11_LDFLAGS) -lX11 -o $@
$(BUILDDIR)/shell-handoff: libexec/shell-handoff.c
	mkdir -p $(BUILDDIR)
	$(CC) $(CFLAGS) $(WARN) libexec/shell-handoff.c -o $@
$(BUILDDIR)/save-session: libexec/save-session.c
	mkdir -p $(BUILDDIR)
	$(CC) $(CFLAGS) $(WARN) $(X11_CPPFLAGS) libexec/save-session.c $(X11_LDFLAGS) -lX11 -o $@
$(BUILDDIR)/stop-sessions: libexec/stop-sessions.c
	mkdir -p $(BUILDDIR)
	$(CC) $(CFLAGS) $(WARN) libexec/stop-sessions.c -lkvm -o $@
$(BUILDDIR)/drop-bridge: libexec/drop-bridge.c libexec/drop-files.h
	mkdir -p $(BUILDDIR)
	$(CC) $(CFLAGS) $(WARN) $(X11_CPPFLAGS) libexec/drop-bridge.c $(X11_LDFLAGS) -lX11 -o $@
$(BUILDDIR)/desktop-sound: libexec/desktop-sound.c
	mkdir -p $(BUILDDIR)
	$(CC) $(CFLAGS) $(WARN) $(X11_CPPFLAGS) libexec/desktop-sound.c $(X11_LDFLAGS) -lX11 -o $@
$(BUILDDIR)/cdromd: libexec/cdromd.c
	mkdir -p $(BUILDDIR)
	$(CC) $(CFLAGS) $(WARN) libexec/cdromd.c -o $@ -lutil
$(BUILDDIR)/recorder-audio.so: libexec/recorder-audio.c libexec/recorder-audio.ld
	mkdir -p $(BUILDDIR)
	$(CC) $(CFLAGS) $(WARN) -EB -mabi=n32 -march=mips3 -mabicalls -G0 -fPIC \
	    -ffreestanding -fno-stack-protector -shared -nostdlib -Wl,-m,elf32btsmip,--oformat,elf32-ntradbigmips \
	    -Wl,--build-id=none,-T,libexec/recorder-audio.ld,-soname,recorder-audio.so libexec/recorder-audio.c -o $@
install: all
	BUILDDIR=$(BUILDDIR) sh ./install.sh
clean:
	rm -f $(PROGRAMS)
