/* Seed a TrueColor window, copy within it, and check the server's readback. */
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef __NetBSD__
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <dev/wscons/wsconsio.h>
#include <fcntl.h>
#include <stdint.h>
#include <unistd.h>
#endif

enum { W = 192, H = 128, LEFT = 192, TOP = 128 };

struct copy { int sx, sy, dx, dy, w, h; };
static const struct copy cases[] = {
	{ 8, 11, 37, 11, 144, 95 }, { 37, 11, 8, 11, 144, 95 },
	{ 17, 4, 17, 23, 151, 99 }, { 17, 23, 17, 4, 151, 99 },
	{ 8, 9, 31, 28, 150, 91 }, { 31, 28, 8, 9, 150, 91 },
	{ 0, 0, -7, 3, 85, 65 }, { 1, 2, 130, 89, 82, 61 },
	{ 2, 3, 191, 127, 1, 1 }, { 3, 2, 3, 2, 159, 109 }
};

static unsigned long
component(int x, int y, int channel)
{
	static const int ax[] = { 17, 5, 23 }, ay[] = { 3, 19, 7 };
	return (x * ax[channel] + y * ay[channel]) & 255;
}

static unsigned long
pack(unsigned long value, unsigned long mask)
{
	return value * (mask & -mask);
}

static unsigned long
pixel(int x, int y, unsigned long r, unsigned long g, unsigned long b)
{
	return pack(component(x, y, 0), r) | pack(component(x, y, 1), g) |
	    pack(component(x, y, 2), b);
}

static void
source(int *x, int *y, const struct copy *c)
{
	if (c && *x >= c->dx && *x < c->dx + c->w &&
	    *y >= c->dy && *y < c->dy + c->h) {
		*x += c->sx - c->dx;
		*y += c->sy - c->dy;
	}
}

#ifdef __NetBSD__
static int
check_ram(const struct copy *c)
{
	struct wsdisplayio_fbinfo fb = { 0 };
	int fd = open("/dev/ttyE0", O_RDONLY);
	if (fd < 0)
		return -1;
	if (ioctl(fd, WSDISPLAYIO_GET_FBINFO, &fb) < 0 ||
	    fb.fbi_bitsperpixel != 32 || fb.fbi_pixeltype != WSFB_RGB ||
	    fb.fbi_width < LEFT + W || fb.fbi_height < TOP + H ||
	    fb.fbi_stride < fb.fbi_width * 4 ||
	    fb.fbi_fboffset + (TOP + H) * (uint64_t)fb.fbi_stride > fb.fbi_fbsize)
		goto failed;
	struct _fbi_rgbmasks m = fb.fbi_subtype.fbi_rgbmasks;
	if (m.red_size != 8 || m.green_size != 8 || m.blue_size != 8 ||
	    m.red_offset > 24 || m.green_offset > 24 || m.blue_offset > 24)
		goto failed;
	const uint8_t *base = mmap(NULL, fb.fbi_fbsize, PROT_READ, MAP_SHARED, fd, 0);
	if (base == MAP_FAILED)
		goto failed;
	unsigned long r = 255UL << m.red_offset, g = 255UL << m.green_offset,
	    b = 255UL << m.blue_offset;
	int errors = 0;
	for (int y = 0; y < H; y++) {
		const uint32_t *row = (const uint32_t *)(base + fb.fbi_fboffset +
		    (TOP + y) * fb.fbi_stride);
		for (int x = 0; x < W; x++) {
			int sx = x, sy = y;
			source(&sx, &sy, c);
			errors += (row[LEFT + x] & (r | g | b)) != pixel(sx, sy, r, g, b);
		}
	}
	munmap((void *)base, fb.fbi_fbsize);
	close(fd);
	return errors;
failed:
	close(fd);
	return -1;
}
#endif

int
main(void)
{
	Display *d = XOpenDisplay(NULL);
	XVisualInfo vi;
	if (!d || !XMatchVisualInfo(d, DefaultScreen(d), 24, TrueColor, &vi))
		return 1;
	unsigned long r = vi.red_mask, g = vi.green_mask, b = vi.blue_mask;
	if (r / (r & -r) != 255 || g / (g & -g) != 255 || b / (b & -b) != 255)
		return 1;
	Window root = RootWindow(d, vi.screen);
	XSetWindowAttributes a = { .override_redirect = True, .border_pixel = 0,
	    .colormap = XCreateColormap(d, root, vi.visual, AllocNone) };
	Window win = XCreateWindow(d, root, LEFT, TOP, W, H, 0, vi.depth, InputOutput,
	    vi.visual, CWOverrideRedirect | CWColormap | CWBorderPixel, &a);
	GC gc = XCreateGC(d, win, 0, NULL);
	XSetGraphicsExposures(d, gc, False);
	XMapRaised(d, win);
	XWarpPointer(d, None, root, 0, 0, 0, 0, LEFT + W + 50, TOP + H + 50);
	XImage *seed = XCreateImage(d, vi.visual, vi.depth, ZPixmap, 0, NULL, W, H, 32, 0);
	if (!seed || !(seed->data = calloc(H, seed->bytes_per_line)))
		return 1;
	for (int y = 0; y < H; y++)
		for (int x = 0; x < W; x++)
			XPutPixel(seed, x, y, pixel(x, y, r, g, b));
	XSync(d, False);
	setvbuf(stdout, NULL, _IOLBF, 0);
	printf("READY %zu\n", sizeof(cases) / sizeof(*cases));
	char line[64];
	const struct copy *c = NULL;
	while (fgets(line, sizeof(line), stdin)) {
		unsigned int n;
		if (!strcmp(line, "seed\n")) {
			c = NULL;
			XPutImage(d, win, gc, seed, 0, 0, 0, 0, W, H);
		} else if (sscanf(line, "copy %u", &n) == 1 && n < sizeof(cases) / sizeof(*cases)) {
			c = &cases[n];
			XCopyArea(d, win, win, gc, c->sx, c->sy, c->w, c->h, c->dx, c->dy);
			XSync(d, False);
			printf("COPY %d %d %d %d %d %d\n", c->sx, c->sy, c->dx, c->dy, c->w, c->h);
			continue;
		} else if (!strcmp(line, "check\n")) {
			XImage *img = XGetImage(d, win, 0, 0, W, H, AllPlanes, ZPixmap);
			if (!img)
				return 1;
			int errors = 0;
			for (int y = 0; y < H; y++)
				for (int x = 0; x < W; x++) {
					int sx = x, sy = y;
					source(&sx, &sy, c);
					errors += XGetPixel(img, x, y) != pixel(sx, sy, r, g, b);
				}
			XDestroyImage(img);
			printf("XIMAGE %d\n", errors);
			continue;
#ifdef __NetBSD__
		} else if (!strcmp(line, "ram\n")) {
			printf("RAM %d\n", check_ram(c));
			continue;
#endif
		} else if (!strcmp(line, "quit\n")) {
			break;
		} else {
			return 2;
		}
		XSync(d, False);
		puts("SEEDED");
	}
	XDestroyImage(seed);
	XCloseDisplay(d);
	return 0;
}
