/* Native XTEST driver; targets only the disposable guest's display :98. */
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <X11/keysym.h>
#include <X11/extensions/XTest.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int
main(int argc, char **argv)
{
    alarm(30);
    setvbuf(stdout, NULL, _IONBF, 0);
    Display *d = XOpenDisplay("127.0.0.1:98");
    if (!d || argc < 2) return 2;
    int event, error, major, minor;
    if (!XTestQueryExtension(d, &event, &error, &major, &minor)) return 3;
    if (!strcmp(argv[1], "control")) {
        int screen = DefaultScreen(d);
        Window w = XCreateSimpleWindow(d, DefaultRootWindow(d), 20, 220,
            240, 80, 0, BlackPixel(d, screen), WhitePixel(d, screen));
        XStoreName(d, w, "Xiri_native_input_control");
        XSelectInput(d, w, ExposureMask | ButtonPressMask | ButtonReleaseMask |
            KeyPressMask | KeyReleaseMask);
        XMapWindow(d, w);
        XSync(d, False);
        XSetInputFocus(d, w, RevertToParent, CurrentTime);
        GC gc = XCreateGC(d, w, 0, NULL);
        XSetForeground(d, gc, BlackPixel(d, screen));
        printf("XTEST %d.%d\n", major, minor);
        for (;;) {
            XEvent e;
            XNextEvent(d, &e);
            if (e.type == Expose) {
                XDrawString(d, w, gc, 10, 30, "Native XTEST input control", 25);
                XFlush(d);
            } else if (e.type == ButtonPress || e.type == ButtonRelease) {
                printf("BUTTON type=%d button=%u send_event=%d x=%d y=%d\n",
                    e.type, e.xbutton.button, e.xbutton.send_event,
                    e.xbutton.x, e.xbutton.y);
            } else if (e.type == KeyPress || e.type == KeyRelease) {
                KeySym key = XLookupKeysym(&e.xkey, 0);
                printf("KEY type=%d keysym=%#lx send_event=%d\n",
                    e.type, key, e.xkey.send_event);
                if (e.type == KeyRelease && key == XK_Escape) break;
            }
        }
    } else if (!strcmp(argv[1], "colors")) {
        const char *names[] = {"SGIGray76", "SGIDarkGray", "#c1c1c1", "#555555"};
        for (unsigned i = 0; i < sizeof(names) / sizeof(names[0]); i++) {
            XColor exact = {0}, screen = {0};
            int ok = XLookupColor(d, DefaultColormap(d, DefaultScreen(d)),
                names[i], &exact, &screen);
            printf("COLOR %s ok=%d rgb=%u,%u,%u\n", names[i], ok,
                exact.red, exact.green, exact.blue);
        }
    } else if (!strcmp(argv[1], "focus") && argc == 3) {
        XSetInputFocus(d, strtoul(argv[2], NULL, 0), RevertToParent, CurrentTime);
    } else if ((!strcmp(argv[1], "click") || !strcmp(argv[1], "move")) && argc == 4) {
        XTestFakeMotionEvent(d, DefaultScreen(d), atoi(argv[2]), atoi(argv[3]), CurrentTime);
        if (!strcmp(argv[1], "click")) {
            XTestFakeButtonEvent(d, 1, True, CurrentTime);
            XTestFakeButtonEvent(d, 1, False, 100);
        }
    } else if (!strcmp(argv[1], "key") && argc == 3) {
        KeySym key = XStringToKeysym(argv[2]);
        KeyCode code = XKeysymToKeycode(d, key);
        if (!key || !code) return 4;
        XTestFakeKeyEvent(d, code, True, CurrentTime);
        XTestFakeKeyEvent(d, code, False, 100);
    } else return 2;
    XSync(d, False);
    XCloseDisplay(d);
    return 0;
}
