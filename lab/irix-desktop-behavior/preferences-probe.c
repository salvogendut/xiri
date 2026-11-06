/* Observe saved 4Dwm focus/move behavior through real XTest pointer events. */
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <X11/extensions/XTest.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

static void settle(Display *d)
{
    XSync(d, False);
    usleep(500000);
}

static void position(Display *d, Window w, int *x, int *y)
{
    Window child;
    XTranslateCoordinates(d, w, DefaultRootWindow(d), 0, 0, x, y, &child);
}

static Window frame(Display *d, Window w)
{
    Window root, parent, *children = NULL;
    unsigned int n;
    for (;;) {
        if (!XQueryTree(d, w, &root, &parent, &children, &n)) return None;
        if (children) XFree(children);
        children = NULL;
        if (parent == root) return w;
        w = parent;
    }
}

int main(int argc, char **argv)
{
    if (argc != 3 || (strcmp(argv[1], "explicit") && strcmp(argv[1], "pointer")) ||
        (strcmp(argv[2], "opaque") && strcmp(argv[2], "outline"))) return 2;
    Display *d = XOpenDisplay(NULL);
    if (!d) return 3;
    Window root = DefaultRootWindow(d), a, b, focus;
    int revert, ax, ay, bx, by, fx, fy, mx, my, ex, ey;
    a = XCreateSimpleWindow(d, root, 200, 200, 160, 100, 0, 0, 0xeeeeee);
    b = XCreateSimpleWindow(d, root, 500, 200, 160, 100, 0, 0, 0xaaaaaa);
    XStoreName(d, a, "Xiri preference focus A");
    XStoreName(d, b, "Xiri preference focus B");
    XMapWindow(d, a); XMapWindow(d, b); settle(d);
    XMoveWindow(d, a, 200, 200); XMoveWindow(d, b, 500, 200);
    XRaiseWindow(d, a); XRaiseWindow(d, b); settle(d);
    position(d, a, &ax, &ay); position(d, b, &bx, &by);
    XTestFakeMotionEvent(d, DefaultScreen(d), ax + 70, ay + 50, 0);
    XTestFakeButtonEvent(d, 1, True, 0); XTestFakeButtonEvent(d, 1, False, 0);
    settle(d); XGetInputFocus(d, &focus, &revert);
    int clicked_a = focus == a;
    XTestFakeMotionEvent(d, DefaultScreen(d), bx + 70, by + 50, 0);
    settle(d); XGetInputFocus(d, &focus, &revert);
    int follows = focus == b, remains = focus == a;
    Window f = frame(d, b);
    if (!f || f == b) return 4;
    position(d, f, &fx, &fy);
    XTestFakeMotionEvent(d, DefaultScreen(d), fx + 80, fy + 10, 0);
    XTestFakeButtonEvent(d, 1, True, 0); settle(d);
    XTestFakeMotionEvent(d, DefaultScreen(d), fx + 160, fy + 60, 0);
    settle(d); position(d, b, &mx, &my);
    XTestFakeButtonEvent(d, 1, False, 0); settle(d);
    position(d, b, &ex, &ey);
    int opaque = mx != bx || my != by;
    int moved = ex != bx || ey != by;
    int ok = clicked_a && moved &&
        (!strcmp(argv[1], "pointer") ? follows : remains) &&
        (opaque == !strcmp(argv[2], "opaque"));
    printf("PREFERENCES_%s focus=%s clicked=%d follows=%d remains=%d "
        "move=%s before=%d,%d held=%d,%d released=%d,%d\n",
        ok ? "PASS" : "FAIL", argv[1], clicked_a, follows, remains,
        opaque ? "opaque" : "outline", bx, by, mx, my, ex, ey);
    XDestroyWindow(d, a); XDestroyWindow(d, b); XSync(d, False);
    XCloseDisplay(d);
    return ok ? 0 : 1;
}
