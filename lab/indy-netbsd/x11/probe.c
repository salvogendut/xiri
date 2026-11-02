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

/* Exercise nonuniform, odd-width images and a shaped pixmap copy. Flat
 * swatches can hide transfer stride, prefetch, and clipping mistakes. */
static unsigned long
pattern_pixel(int x, int y)
{
    return ((x + 3 * y) & 255) | (((5 * x + y) & 255) << 8) |
        (((11 * x + 7 * y) & 255) << 16);
}

static int
check_images(int width, int sx, int sy)
{
    enum { WIDTH = 97, HEIGHT = 193, DX = 520, DY = 200 };
    XImage *source = XCreateImage(d, DefaultVisual(d, DefaultScreen(d)),
        DefaultDepth(d, DefaultScreen(d)), ZPixmap, 0, NULL, WIDTH, HEIGHT, 32, 0);
    if (!source) exit(2);
    source->data = calloc(source->bytes_per_line, HEIGHT);
    if (!source->data) exit(2);
    for (int y = 0; y < HEIGHT; y++)
        for (int x = 0; x < WIDTH; x++)
            XPutPixel(source, x, y, pattern_pixel(x, y));
    Pixmap pixmap = XCreatePixmap(d, w, WIDTH, HEIGHT, DefaultDepth(d, DefaultScreen(d)));
    GC pgc = XCreateGC(d, pixmap, 0, NULL);
    XPutImage(d, pixmap, pgc, source, 0, 0, 0, 0, WIDTH, HEIGHT);
    char bits[((WIDTH + 7) / 8) * HEIGHT];
    memset(bits, 0, sizeof(bits));
    for (int y = 0; y < HEIGHT; y++)
        for (int x = 0; x < WIDTH; x++)
            if (((x / 7) + (y / 11)) % 2)
                bits[y * ((WIDTH + 7) / 8) + x / 8] |= 1 << (x % 8);
    Pixmap mask = XCreateBitmapFromData(d, w, bits, WIDTH, HEIGHT);
    int ok = 1;
    for (int pass = 0; pass < 6 && ok; pass++) {
        XSetForeground(d, gc, 0);
        XFillRectangle(d, w, gc, DX, DY, WIDTH, HEIGHT);
        if (pass == 4 || pass == 5) {
            XSetClipMask(d, gc, mask);
            XSetClipOrigin(d, gc, DX - sx, DY - sy);
            if (pass == 5) XSetFunction(d, gc, GXor);
            XCopyArea(d, pixmap, w, gc, sx, sy, width, HEIGHT - sy, DX, DY);
            XSetFunction(d, gc, GXcopy);
            XSetClipMask(d, gc, None);
        } else if (pass == 0) {
            XPutImage(d, w, gc, source, 0, 0, DX, DY, WIDTH, HEIGHT);
        } else if (pass == 3) {
            XSetForeground(d, gc, colors[0]);
            XSetBackground(d, gc, colors[2]);
            XCopyPlane(d, mask, w, gc, 0, 0, WIDTH, HEIGHT, DX, DY, 1);
        } else {
            if (pass == 2) {
                XSetClipMask(d, gc, mask);
                XSetClipOrigin(d, gc, DX, DY);
            }
            XCopyArea(d, pixmap, w, gc, 0, 0, WIDTH, HEIGHT, DX, DY);
            XSetClipMask(d, gc, None);
        }
        XSync(d, False);
        XImage *actual = XGetImage(d, w, DX, DY, WIDTH, HEIGHT, AllPlanes, ZPixmap);
        if (!actual) exit(2);
        for (int y = 0; y < HEIGHT && ok; y++)
            for (int x = 0; x < WIDTH; x++) {
                unsigned long expected = pass == 2 && !(((x / 7) + (y / 11)) % 2)
                    ? 0 : pattern_pixel(x, y);
                if (pass == 3) expected = (((x / 7) + (y / 11)) % 2) ? colors[0] : colors[2];
                if (pass >= 4) expected = x < width && y < HEIGHT - sy &&
                    ((((x + sx) / 7) + ((y + sy) / 11)) % 2)
                    ? pattern_pixel(x + sx, y + sy) : 0;
                unsigned long got = XGetPixel(actual, x, y);
                if (got != expected) {
                    fprintf(stderr, "PIXEL_FAIL image-width=%d offset=%d,%d pass=%d x=%d y=%d expected=%lx actual=%lx\n",
                        width, sx, sy, pass, x, y, expected, got);
                    ok = 0;
                    break;
                }
            }
        XDestroyImage(actual);
        if (ok) printf("IMAGE_PASS %d width=%d offset=%d,%d pixels=%d\n", pass, width, sx, sy, WIDTH * HEIGHT);
    }
    XDestroyImage(source);
    XFreeGC(d, pgc);
    XFreePixmap(d, pixmap);
    XFreePixmap(d, mask);
    return ok;
}

static int
check_blits(void)
{
    enum { WIDTH = 97, HEIGHT = 193, DX = 520, DY = 200 };
    const int moves[][2] = {{3,5},{-3,-5},{3,-5},{-3,5},{0,5},{0,-5},{3,0},{-3,0}};
    XImage *source = XCreateImage(d, DefaultVisual(d, DefaultScreen(d)),
        DefaultDepth(d, DefaultScreen(d)), ZPixmap, 0, NULL, WIDTH, HEIGHT, 32, 0);
    if (!source || source->bits_per_pixel != 32) exit(2);
    source->data = calloc(source->bytes_per_line, HEIGHT);
    if (!source->data) exit(2);
    /* Match gifx.c: explicitly little-endian image data on the big-endian client. */
    source->byte_order = source->bitmap_bit_order = LSBFirst;
    for (int y = 0; y < HEIGHT; y++)
        for (int x = 0; x < WIDTH; x++) {
            unsigned long pixel = pattern_pixel(x,y);
            for (int b = 0; b < 4; b++)
                source->data[y * source->bytes_per_line + 4*x + b] = pixel >> (8*b);
        }
    int ok = 1;
    for (int pass = -1; pass < 8 && ok; pass++) {
        XPutImage(d, w, gc, source, 0, 0, DX, DY, WIDTH, HEIGHT);
        int mx = pass < 0 ? 0 : moves[pass][0];
        int my = pass < 0 ? 0 : moves[pass][1];
        int sx = mx < 0 ? -mx : 0, sy = my < 0 ? -my : 0;
        int tx = mx > 0 ? mx : 0, ty = my > 0 ? my : 0;
        int cw = WIDTH - abs(mx), ch = HEIGHT - abs(my);
        if (pass >= 0) XCopyArea(d, w, w, gc, DX+sx, DY+sy, cw, ch, DX+tx, DY+ty);
        XSync(d, False);
        XImage *actual = XGetImage(d, w, DX, DY, WIDTH, HEIGHT, AllPlanes, ZPixmap);
        if (!actual) exit(2);
        for (int y = 0; y < HEIGHT && ok; y++)
            for (int x = 0; x < WIDTH; x++) {
                int moved = pass >= 0 && x >= tx && x < tx+cw && y >= ty && y < ty+ch;
                unsigned long expected = pattern_pixel(x-(moved?mx:0), y-(moved?my:0));
                unsigned long got = XGetPixel(actual,x,y);
                if (got != expected) {
                    fprintf(stderr,"PIXEL_FAIL blit-pass=%d x=%d y=%d expected=%lx actual=%lx\n",
                        pass,x,y,expected,got);ok=0;break;
                }
            }
        XDestroyImage(actual);
        if (ok) printf("BLIT_PASS %d pixels=%d\n",pass,WIDTH*HEIGHT);
    }
    XDestroyImage(source);
    return ok;
}

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

    /* Each primary must also survive a physical WRMASK conversion. Clear the
     * destination on every Expose so this checks preservation, not old pixels. */
    Visual *visual = DefaultVisual(d, DefaultScreen(d));
    unsigned long masks[4] = { visual->red_mask, visual->green_mask,
        visual->blue_mask, AllPlanes };
    XSetForeground(d, gc, 0);
    XFillRectangle(d, w, gc, 20, 320, 460, 120);
    for (int i = 0; i < 4; i++) {
        XSetPlaneMask(d, gc, masks[i]);
        XSetForeground(d, gc, colors[3]);
        XFillRectangle(d, w, gc, 20 + 120 * i, 320, 100, 40);
        XCopyArea(d, w, w, gc, 380, 80, 100, 40, 20 + 120 * i, 400);
    }
    XSetPlaneMask(d, gc, AllPlanes);
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
    for (int i = 0; i < 4; i++) {
        unsigned long expected = colors[3] & masks[i];
        if (XGetPixel(image, 60 + 120 * i, 340) != expected ||
            XGetPixel(image, 60 + 120 * i, 420) != expected) {
            fprintf(stderr, "PIXEL_FAIL mask=%lx expected=%lx fill=%lx copy=%lx\n",
                masks[i], expected, XGetPixel(image, 60 + 120 * i, 340),
                XGetPixel(image, 60 + 120 * i, 420));
            XDestroyImage(image);
            return;
        }
    }
    XDestroyImage(image);
    const int widths[] = {1, 2, 3, 4, 31, 32, 33, 63, 64, 65, 84};
    for (unsigned i = 0; i < sizeof(widths)/sizeof(widths[0]); i++)
        if (!check_images(widths[i], 13, 9)) return;
    if (check_blits()) puts("PIXELS_PASS");
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
