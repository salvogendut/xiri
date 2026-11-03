/* Native readiness checks; no process or server ownership is acquired. */
#include <X11/Xlib.h>
#include <X11/Xatom.h>
#include <stdio.h>
#include <string.h>
static int xerror;
static int error(Display *d, XErrorEvent *e) { (void)d; (void)e; xerror = 1; return 0; }
int main(int argc, char **argv)
{
    if (argc != 2) return 2;
    Display *d = XOpenDisplay(NULL);
    if (!d) return 2;
    XSetErrorHandler(error);
    Window root = DefaultRootWindow(d);
    int ok = 0;
    if (!strcmp(argv[1], "vacant")) {
        XSelectInput(d, root, SubstructureRedirectMask);
        XSync(d, False);
        ok = !xerror;
        XSelectInput(d, root, 0);
    } else if (!strcmp(argv[1], "ready")) {
        Atom type, prop = XInternAtom(d, "_MOTIF_WM_INFO", False);
        int format;
        unsigned long items, left;
        unsigned char *data = NULL;
        if (XGetWindowProperty(d, root, prop, 0, 2, False, AnyPropertyType,
            &type, &format, &items, &left, &data) == Success && format == 32 && items == 2) {
            XWindowAttributes attr;
            ok = XGetWindowAttributes(d, ((unsigned long *)data)[1], &attr) != 0;
            XSync(d, False);
            ok = ok && !xerror;
        }
        if (data) XFree(data);
    }
    XCloseDisplay(d);
    return ok ? 0 : 1;
}
