# Run with native NetBSD make/cc inside the guest.
CC?= cc
CFLAGS+= -O2 -Wall -Wextra -Werror
XINC= -I/usr/X11R7/include
XLIB= -L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib
FTINC= -I/usr/X11R7/include/freetype2

all: signal-registers fp-signal core-metrics stress ft-metrics fttrace.so

signal-registers: signal-registers.c registers.S
	${CC} ${CFLAGS} signal-registers.c registers.S -o $@

fp-signal: fp-signal.c
	${CC} ${CFLAGS} fp-signal.c -o $@

core-metrics: core-metrics.c
	${CC} ${CFLAGS} ${XINC} core-metrics.c ${XLIB} -lX11 -o $@

stress: stress.c core-metrics.c
	${CC} ${CFLAGS} ${XINC} stress.c ${XLIB} -lX11 -o $@

ft-metrics: ft-metrics.c
	${CC} ${CFLAGS} ${FTINC} ft-metrics.c ${XLIB} -lfreetype -o $@

fttrace.so: fttrace.c
	${CC} ${CFLAGS} -fPIC -shared ${FTINC} fttrace.c ${XLIB} -lfreetype -o $@

clean:
	rm -f signal-registers fp-signal core-metrics stress ft-metrics fttrace.so
