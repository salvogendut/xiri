/* Native X client: verify pointer-root focus by its actual input destination. */
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <X11/keysym.h>
#include <X11/extensions/XTest.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

static Window parent(Display *d, Window w)
{
    Window root, p, *children = NULL;
    unsigned count;
    if (!XQueryTree(d, w, &root, &p, &children, &count)) return None;
    if (children) XFree(children);
    return p;
}

static int position(Display *d, Window w, int *x, int *y)
{
    Window child;
    return XTranslateCoordinates(d, w, DefaultRootWindow(d), 0, 0,
        x, y, &child);
}

static int descendant(Display *d, Window w, Window ancestor)
{
    if (w == None || w == PointerRoot) return 0;
    for (int i = 0; w && i < 16; i++, w = parent(d, w))
        if (w == ancestor) return 1;
    return 0;
}

int main(int argc, char **argv)
{
    if (argc != 2) return 2;
    Display *d = XOpenDisplay(argv[1]);
    if (!d) return 2;
    int a, b, c, e;
    if (!XTestQueryExtension(d, &a, &b, &c, &e)) return 2;
    Window root = DefaultRootWindow(d), windows[2];
    for (int i = 0; i < 2; i++) {
        windows[i] = XCreateSimpleWindow(d, root, 150 + i * 420, 160,
            300, 160, 0, 0, i ? 0xc8c8c8 : 0xdee8f0);
        XStoreName(d, windows[i], i ? "Xiri native window B" : "Xiri native window A");
        XClassHint cls = {(char *)"xiri-wm-probe", (char *)"XiriWMProbe"};
        XSetClassHint(d, windows[i], &cls);
        XSizeHints size = {0};
        size.flags = USPosition | USSize;
        size.x = 150 + i * 420; size.y = 160;
        size.width = 300; size.height = 160;
        XSetWMNormalHints(d, windows[i], &size);
        XSelectInput(d, windows[i], StructureNotifyMask | KeyPressMask);
        XMapWindow(d, windows[i]);
    }
    XSync(d, False);
    int reparented = 0;
    for (int i = 0; i < 100; i++) {
        Window p0 = parent(d, windows[0]), p1 = parent(d, windows[1]);
        XWindowAttributes a0, a1;
        if (p0 && p1 && p0 != root && p1 != root &&
            XGetWindowAttributes(d, windows[0], &a0) &&
            XGetWindowAttributes(d, windows[1], &a1) &&
            a0.map_state == IsViewable && a1.map_state == IsViewable) {
            reparented = 1; break;
        }
        usleep(100000);
    }
    if (!reparented) { fprintf(stderr, "windows were not reparented and viewable\n"); return 3; }
    puts("WM_VIEWABLE clients=2");
    Window frame = windows[0], next;
    for (int i = 0; i < 16; i++) {
        next = parent(d, frame);
        if (next == root) break;
        if (!next) return 3;
        frame = next;
    }
    int x, y, fx, fy, moved_x, moved_y;
    if (!position(d, windows[0], &x, &y) || !position(d, frame, &fx, &fy)) return 3;
    printf("WM_REPARENT client=%lu frame=%lu x=%d y=%d frame_x=%d frame_y=%d\n",
        windows[0], frame, x, y, fx, fy);
    if (y - fy < 8 || y - fy > 100) return 4;
    XTestFakeMotionEvent(d, DefaultScreen(d), x + 120, y + 70, 0);
    XSync(d, False); usleep(500000);
    Window focus;
    int revert;
    XGetInputFocus(d, &focus, &revert);
    Window pointer = root;
    if (focus == PointerRoot) {
        /* PointerRoot is an X focus policy, not a Window resource. Resolve
         * the deepest child under the real pointer and require our client. */
        for (int i = 0; i < 16; i++) {
            Window pr, child;
            int rx, ry, wx, wy;
            unsigned mask;
            if (!XQueryPointer(d, pointer, &pr, &child, &rx, &ry,
                &wx, &wy, &mask)) return 5;
            if (!child) break;
            pointer = child;
        }
    }
    int focused = descendant(d, focus == PointerRoot ? pointer : focus, windows[0]);
    printf("WM_FOCUS_POLICY pointer_root=%d pointer_leaf=%lu\n", focus == PointerRoot, pointer);
    printf("WM_FOCUS client=%lu focus=%lu matched=%d\n", windows[0], focus, focused);
    if (!focused) return 5;
    KeyCode key = XKeysymToKeycode(d, XK_k);
    XTestFakeKeyEvent(d, key, True, 0);
    XTestFakeKeyEvent(d, key, False, 0);
    XSync(d, False); usleep(200000);
    int received = 0;
    while (XPending(d)) {
        XEvent event;
        XNextEvent(d, &event);
        if (event.type == KeyPress && event.xkey.window == windows[0] &&
            event.xkey.keycode == key) received = 1;
    }
    printf("WM_KEY delivered=%d\n", received);
    if (!received) return 5;
    /* The middle of the top decoration avoids the outer resize handle and
     * the buttons at either end. Use real pointer/button events. */
    int drag_x = x + 120, drag_y = fy + (y - fy) / 2;
    XTestFakeMotionEvent(d, DefaultScreen(d), drag_x, drag_y, 0);
    XSync(d, False); usleep(200000);
    XTestFakeButtonEvent(d, 1, True, 0);
    XSync(d, False); usleep(200000);
    for (int i = 1; i <= 10; i++) {
        XTestFakeMotionEvent(d, DefaultScreen(d), drag_x + i * 5,
            drag_y + i * 3, 0);
        XSync(d, False); usleep(30000);
    }
    XTestFakeButtonEvent(d, 1, False, 0);
    XSync(d, False); usleep(500000);
    if (!position(d, windows[0], &moved_x, &moved_y)) return 6;
    printf("WM_DRAG dx=%d dy=%d\n", moved_x - x, moved_y - y);
    if (abs(moved_x - x - 50) > 3 || abs(moved_y - y - 30) > 3) return 6;
    puts("WM_CHECK passed"); fflush(stdout);
    sleep(5);
    for (int i = 0; i < 2; i++) XDestroyWindow(d, windows[i]);
    XCloseDisplay(d);
    return 0;
}
