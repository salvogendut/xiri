/* Drive the actual decorated winterm through XTEST and its existing PTY. */
#include <X11/Xlib.h>
#include <X11/extensions/XTest.h>
#include <sys/ioctl.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static void
position(Display *d, Window w, int *x, int *y)
{
    Window child;
    if (!XTranslateCoordinates(d, w, DefaultRootWindow(d), 0, 0, x, y, &child))
        exit(3);
}

static void
lines(FILE *tty, int count, int cols, int *line)
{
    for (int i = 0; i < count; i++, (*line)++) {
        int c = (*line / 8) % 2 ? 'M' : '.';
        for (int j = 0; j < cols - 2; j++)
            fputc(c, tty);
        fputs("\r\n", tty);
    }
    if (fflush(tty) == EOF)
        exit(4);
}

int
main(int argc, char **argv)
{
    if (argc != 3)
        return 2;
    Display *d = XOpenDisplay(NULL);
    if (!d)
        return 3;
    Window root = DefaultRootWindow(d);
    Window client = strtoul(argv[1], NULL, 0), frame = client;
    Window parent, rr, *kids;
    unsigned int nk;
    while (XQueryTree(d, frame, &rr, &parent, &kids, &nk)) {
        if (kids)
            XFree(kids);
        if (parent == root)
            break;
        frame = parent;
    }
    if (frame == client)
        return 3;
    int fd = open(argv[2], O_WRONLY | O_NOCTTY);
    struct winsize ws;
    if (fd < 0 || ioctl(fd, TIOCGWINSZ, &ws) || ws.ws_row < 12 || ws.ws_col < 20)
        return 4;
    FILE *tty = fdopen(fd, "w");
    if (!tty)
        return 4;
    XRaiseWindow(d, frame);
    XSync(d, False);
    int x, y, fx, fy;
    position(d, client, &x, &y);
    position(d, frame, &fx, &fy);
    XWindowAttributes attrs;
    if (!XGetWindowAttributes(d, client, &attrs) || y-fy < 8 ||
        x < 0 || y < 0 || x + attrs.width + 112 > DisplayWidth(d, DefaultScreen(d)))
        return 3;
    int px = x + 120, py = fy + (y - fy) / 2, line = 0;
    XTestGrabControl(d, True);
    setvbuf(stdout, NULL, _IOLBF, 0);
    fputs("\033[0m\033[2J\033[H", tty);
    lines(tty, ws.ws_row + 16, ws.ws_col, &line);
    printf("READY %d %d %d %d %d %d\n", x, y, attrs.width, attrs.height, ws.ws_row, ws.ws_col);
    char cmd[16];
    while (fgets(cmd, sizeof(cmd), stdin)) {
        switch (cmd[0]) {
        case 'b':
            XTestFakeMotionEvent(d, -1, px, py, 0);
            XTestFakeButtonEvent(d, 1, True, 0);
            break;
        case 'r': case 'l':
            XTestFakeMotionEvent(d, -1, px + (cmd[0] == 'r' ? 112 : 0), py, 0);
            break;
        case 'e':
            XTestFakeButtonEvent(d, 1, False, 0);
            XTestFakeMotionEvent(d, -1, 1150, 920, 0);
            break;
        case 's':
            lines(tty, 8, ws.ws_col, &line);
            break;
        case 'g':
            position(d, client, &fx, &fy);
            printf("POSITION %d %d\n", fx, fy);
            break;
        case 'q':
            XTestFakeButtonEvent(d, 1, False, 0);
            XCloseDisplay(d);
            fclose(tty);
            return 0;
        default:
            return 2;
        }
        XFlush(d);
    }
    return 0;
}
