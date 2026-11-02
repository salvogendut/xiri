/* Native XTEST input for a disposable guest's Icon Catalog launch check. */
#include <X11/Xlib.h>
#include <X11/keysym.h>
#include <X11/extensions/XTest.h>
#include <signal.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int
main(int argc, char **argv)
{
    alarm(15);
    if (argc < 4) return 2;
    Display *d = XOpenDisplay(argv[1]);
    if (!d) return 3;
    Window w = strtoul(argv[2], NULL, 0);
    int event, error, major, minor;
    if (!XTestQueryExtension(d, &event, &error, &major, &minor)) return 4;
    XRaiseWindow(d, w);
    XWarpPointer(d, None, w, 0, 0, 0, 0, 100, 100);
    XSetInputFocus(d, w, RevertToParent, CurrentTime);
    XSync(d, False);
    usleep(200000);
    if (!strcmp(argv[3], "key") && argc == 5) {
        KeySym sym = XStringToKeysym(argv[4]);
        KeyCode code = XKeysymToKeycode(d, sym);
        if (!sym || !code) return 5;
        XTestFakeKeyEvent(d, code, True, 0);
        XTestFakeKeyEvent(d, code, False, 0);
    } else if (!strcmp(argv[3], "double") && argc == 6) {
        XTestFakeMotionEvent(d, DefaultScreen(d), atoi(argv[4]), atoi(argv[5]), 0);
        for (int i = 0; i < 2; i++) {
            XTestFakeButtonEvent(d, 1, True, 0);
            XTestFakeButtonEvent(d, 1, False, 0);
        }
    } else return 2;
    XSync(d, False);
    XCloseDisplay(d);
    return 0;
}
