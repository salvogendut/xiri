/* Native X observer and independent static Expose control on the test Xvfb. */
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <inttypes.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

static Display *display;
static Window root;
static unsigned visible;

static void
walk(Window window, unsigned depth, int clear)
{
    Window parent, actual_root, *children = NULL;
    unsigned count = 0;
    XWindowAttributes a;
    char *name = NULL;
    if (depth > 32 || !XGetWindowAttributes(display, window, &a)) return;
    if (depth && a.map_state == IsViewable && a.class == InputOutput) {
        visible++;
        if (clear) XClearArea(display, window, 0, 0, 0, 0, True);
    }
    if (!clear) {
        XFetchName(display, window, &name);
        printf("WINDOW id=%#lx depth=%u map=%d class=%d override=%d x=%d y=%d width=%d height=%d name=%s\n",
            window, depth, a.map_state, a.class, a.override_redirect,
            a.x, a.y, a.width, a.height, name ? name : "");
        if (name) XFree(name);
        XWMHints *hints = XGetWMHints(display, window);
        if (hints) {
            printf("WM_HINTS id=%#lx flags=%#lx initial_state=%d\n",
                window, hints->flags, hints->initial_state);
            XFree(hints);
        }
    }
    if (XQueryTree(display, window, &actual_root, &parent, &children, &count)) {
        for (unsigned i = 0; i < count; i++) walk(children[i], depth + 1, clear);
        if (children) XFree(children);
    }
}

static uint32_t
pixels(void)
{
    XWindowAttributes a;
    if (!XGetWindowAttributes(display, root, &a)) _exit(2);
    XImage *image = XGetImage(display, root, 0, 0, (unsigned)a.width,
        (unsigned)a.height, AllPlanes, ZPixmap);
    if (!image) _exit(2);
    uint32_t hash = UINT32_C(2166136261);
    for (int y = 0; y < a.height; y++)
        for (int x = 0; x < a.width; x++) {
            unsigned long pixel = XGetPixel(image, x, y);
            hash ^= (uint32_t)pixel;
            hash *= UINT32_C(16777619);
        }
    XDestroyImage(image);
    return hash;
}

int
main(int argc, char **argv)
{
    alarm(60);
    display = XOpenDisplay("127.0.0.1:98");
    if (!display) return 2;
    root = DefaultRootWindow(display);
    if (argc == 2 && !strcmp(argv[1], "control")) {
        int screen = DefaultScreen(display);
        Window w = XCreateSimpleWindow(display, root, 20, 20, 240, 80, 0,
            BlackPixel(display, screen), WhitePixel(display, screen));
        XStoreName(display, w, "Xiri_native_expose_control");
        XSelectInput(display, w, ExposureMask);
        GC gc = XCreateGC(display, w, 0, NULL);
        XSetForeground(display, gc, BlackPixel(display, screen));
        XMapWindow(display, w);
        for (;;) {
            XEvent event;
            XNextEvent(display, &event);
            if (event.type == Expose) {
                XDrawString(display, w, gc, 10, 30, "Xiri native Expose control", 26);
                XFillRectangle(display, w, gc, 10, 45, 100, 12);
                XFlush(display);
            }
        }
    }
    visible = 0;
    walk(root, 0, 0);
    printf("VISIBLE %u\n", visible);
    if (argc == 2 && !strcmp(argv[1], "redraw")) {
        XGrabServer(display);
        uint32_t before = pixels();
        visible = 0;
        walk(root, 0, 1);
        XSync(display, False);
        uint32_t cleared = pixels();
        XUngrabServer(display);
        XFlush(display);
        sleep(1);
        uint32_t after = pixels();
        printf("REDRAW visible=%u before=%08" PRIx32 " cleared=%08" PRIx32 " after=%08" PRIx32 "\n",
            visible, before, cleared, after);
    }
    XCloseDisplay(display);
    return 0;
}
