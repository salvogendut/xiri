/* Xlib drawing/readback and real wscons input probe for the disposable lab. */
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static Display *d;
static Window w;
static GC gc;
static unsigned long colors[4];

static void
draw(void)
{
    const char *title = "Xiri / NetBSD Newport: fill, copy, image upload, input";
    XSetForeground(d, gc, colors[3]);
    XDrawString(d, w, gc, 20, 35, title, strlen(title));
    for (int i = 0; i < 4; i++) {
        XSetForeground(d, gc, colors[i]);
        XFillRectangle(d, w, gc, 20 + 120 * i, 80, 100, 80);
    }
    XCopyArea(d, w, w, gc, 20, 80, 460, 80, 20, 200);
    XSetFunction(d, gc, GXxor);
    XSetForeground(d, gc, colors[3]);
    XFillRectangle(d, w, gc, 20, 200, 100, 80);
    XFillRectangle(d, w, gc, 20, 200, 100, 80);
    XSetFunction(d, gc, GXcopy);

    XImage *tile = XCreateImage(d, DefaultVisual(d, DefaultScreen(d)),
        DefaultDepth(d, DefaultScreen(d)), ZPixmap, 0, NULL, 32, 32, 32, 0);
    if (!tile) exit(2);
    tile->data = calloc(tile->bytes_per_line, tile->height);
    if (!tile->data) exit(2);
    for (int y = 0; y < 32; y++)
        for (int x = 0; x < 32; x++)
            XPutPixel(tile, x, y, colors[(x >= 16) + 2 * (y >= 16)]);
    XPutImage(d, w, gc, tile, 0, 0, 520, 80, 32, 32);
    XDestroyImage(tile);
    XSync(d, False);

    XImage *image = XGetImage(d, w, 0, 0, 640, 480, AllPlanes, ZPixmap);
    if (!image) exit(2);
    for (int i = 0; i < 4; i++) {
        if (XGetPixel(image, 60 + 120 * i, 120) != colors[i] ||
            XGetPixel(image, 60 + 120 * i, 240) != colors[i] ||
            XGetPixel(image, 528 + 16 * (i % 2), 88 + 16 * (i / 2)) != colors[i]) {
            fprintf(stderr, "PIXEL_FAIL color=%d expected=%lx fill=%lx copy=%lx upload=%lx\n",
                i, colors[i], XGetPixel(image, 60 + 120 * i, 120),
                XGetPixel(image, 60 + 120 * i, 240),
                XGetPixel(image, 528 + 16 * (i % 2), 88 + 16 * (i / 2)));
            XDestroyImage(image);
            return;
        }
    }
    XDestroyImage(image);
    puts("PIXELS_PASS");
}

int
main(void)
{
    const char *names[] = { "red", "green", "blue", "white" };
    char typed[128] = "";
    size_t used = 0;
    setvbuf(stdout, NULL, _IOLBF, 0);
    d = XOpenDisplay(NULL);
    if (!d) return 1;
    int screen = DefaultScreen(d);
    for (int i = 0; i < 4; i++) {
        XColor actual, exact;
        if (!XAllocNamedColor(d, DefaultColormap(d, screen), names[i], &actual, &exact))
            return 2;
        colors[i] = actual.pixel;
    }
    w = XCreateSimpleWindow(d, RootWindow(d, screen), 40, 40, 640, 480,
        0, WhitePixel(d, screen), BlackPixel(d, screen));
    XStoreName(d, w, "Xiri Newport probe");
    XSelectInput(d, w, ExposureMask | KeyPressMask | KeyReleaseMask |
        ButtonPressMask | ButtonReleaseMask | PointerMotionMask);
    gc = XCreateGC(d, w, 0, NULL);
    XMapWindow(d, w);
    XSync(d, False);
    XSetInputFocus(d, w, RevertToParent, CurrentTime);
    printf("READY depth=%d size=%dx%d window=0x%lx\n", DefaultDepth(d, screen),
        DisplayWidth(d, screen), DisplayHeight(d, screen), w);
    for (;;) {
        XEvent e;
        XNextEvent(d, &e);
        if (e.type == Expose && e.xexpose.count == 0) draw();
        if (e.type == MotionNotify)
            printf("MOTION %d %d\n", e.xmotion.x, e.xmotion.y);
        if (e.type == ButtonPress || e.type == ButtonRelease)
            printf("BUTTON_%s %u %d %d\n", e.type == ButtonPress ? "DOWN" : "UP",
                e.xbutton.button, e.xbutton.x, e.xbutton.y);
        if (e.type == KeyPress || e.type == KeyRelease) {
            char buf[32];
            KeySym sym;
            int n = XLookupString(&e.xkey, buf, sizeof(buf), &sym, NULL);
            const char *name = XKeysymToString(sym);
            printf("KEY_%s %s\n", e.type == KeyPress ? "DOWN" : "UP", name ? name : "?");
            if (e.type == KeyPress && n > 0 && used + n < sizeof(typed)) {
                memcpy(typed + used, buf, n);
                used += n;
                typed[used] = '\0';
                if (strcmp(typed, "Xiri_123\r") == 0) puts("TEXT_PASS");
            }
        }
    }
}
