/* Alternate solid fills and patterned pixmap copies under host scanout control. */
#include <X11/Xlib.h>
#include <stdio.h>

enum { WIDTH = 640, HEIGHT = 480, SQUARE = 8 };

int
main(void)
{
	Display *d = XOpenDisplay(NULL);
	if (d == NULL)
		return 1;
	int screen = DefaultScreen(d);
	XSetWindowAttributes attr = { .override_redirect = True, .background_pixel = 0 };
	Window win = XCreateWindow(d, RootWindow(d, screen), 0, 0, WIDTH, HEIGHT,
	    0, CopyFromParent, InputOutput, CopyFromParent,
	    CWOverrideRedirect | CWBackPixel, &attr);
	GC gc = XCreateGC(d, win, 0, NULL);
	const unsigned long colors[2] = { 0xca4632, 0x249ace };
	Pixmap pattern[2];
	for (int phase = 0; phase < 2; phase++) {
		pattern[phase] = XCreatePixmap(d, win, WIDTH, HEIGHT, DefaultDepth(d, screen));
		for (int y = 0; y < HEIGHT; y += SQUARE) {
			for (int x = 0; x < WIDTH; x += SQUARE) {
				int shade = (phase + x / SQUARE + y / SQUARE) % 2;
				XSetForeground(d, gc, colors[shade]);
				XFillRectangle(d, pattern[phase], gc, x, y, SQUARE, SQUARE);
			}
		}
	}
	XMapRaised(d, win);
	/* Keep the server cursor out of the scanout comparison. */
	XWarpPointer(d, None, RootWindow(d, screen), 0, 0, 0, 0, WIDTH + 40, HEIGHT + 40);
	XSync(d, False);
	puts("READY");
	fflush(stdout);
	char line[8];
	while (fgets(line, sizeof(line), stdin) != NULL) {
		if (line[0] == 'q')
			break;
		int phase = line[1] == '1';
		if (line[0] == 'f') {
			XSetForeground(d, gc, colors[phase]);
			XFillRectangle(d, win, gc, 0, 0, WIDTH, HEIGHT);
		} else if (line[0] == 'p') {
			XCopyArea(d, pattern[phase], win, gc, 0, 0, WIDTH, HEIGHT, 0, 0);
		} else {
			return 2;
		}
		XSync(d, False);
	}
	XCloseDisplay(d);
	return 0;
}
