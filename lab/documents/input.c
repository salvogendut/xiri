/* Document integration gestures; X coordinates avoid emulated cursor-hotspot changes. */
#include <X11/Xlib.h>
#include <X11/keysym.h>
#include <X11/extensions/XTest.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
static int lookup_error(Display *d, XErrorEvent *event)
{
    /* A client can destroy a child between XQueryTree and XFetchName. */
    if (event->error_code == BadWindow) return 0;
    char message[128]; XGetErrorText(d,event->error_code,message,sizeof(message));
    fprintf(stderr,"Window lookup: %s\n",message); _exit(1);
}
static Window find(Display *d, Window w, const char *name)
{
    char *s = NULL;
    if (XFetchName(d, w, &s) && s) {
        int equal = !strcmp(s, name); XFree(s);
        XWindowAttributes attrs;
        if (equal && XGetWindowAttributes(d,w,&attrs) && attrs.map_state == IsViewable)
            return w;
    }
    Window root, parent, *children = NULL, found = None; unsigned count;
    if (XQueryTree(d, w, &root, &parent, &children, &count)) {
        for (unsigned i = 0; i < count && !found; i++) found = find(d, children[i], name);
        if (children) XFree(children);
    }
    return found;
}
static void expired(int s) { (void)s; _exit(124); }
static void pointer(Display *d, int x, int y)
{ XTestFakeMotionEvent(d, -1, x, y, 0); XFlush(d); usleep(100000); }
int main(int argc, char **argv)
{
    if (argc < 2) return 2;
    signal(SIGALRM, expired); alarm(30);
    Display *d = XOpenDisplay(NULL); if (!d) return 2;
    int a,b,c,e; if (!XTestQueryExtension(d,&a,&b,&c,&e)) return 2;
    if (argc == 2 && !strcmp(argv[1], "pointer")) {
        Window root, child; int rx, ry, wx, wy; unsigned mask;
        if (!XQueryPointer(d, DefaultRootWindow(d), &root, &child, &rx, &ry, &wx, &wy, &mask)) return 3;
        printf("x=%d y=%d mask=0x%x child=0x%lx\n", rx, ry, mask, child);
        XCloseDisplay(d); return 0;
    }
    if (argc < 4) return 2;
    XErrorHandler previous = XSetErrorHandler(lookup_error);
    Window w = !strncmp(argv[1], "0x", 2) ? strtoul(argv[1], NULL, 16) :
        find(d, DefaultRootWindow(d), argv[1]);
    XSync(d,False); XSetErrorHandler(previous);
    if (!w) return 3;
    XWindowAttributes attrs; XGetWindowAttributes(d, w, &attrs);
    if (attrs.map_state != IsViewable) return 4;
    Window child; int x,y;
    XTranslateCoordinates(d, w, DefaultRootWindow(d), 0, 0, &x, &y, &child);
    printf("window=0x%lx x=%d y=%d width=%d height=%d\n", w,x,y,attrs.width,attrs.height);
    XRaiseWindow(d,w);
    if (!strcmp(argv[2], "key")) pointer(d,x+attrs.width/2,y+attrs.height/2);
    XSetInputFocus(d,w,RevertToParent,CurrentTime);
    XSync(d,False); usleep(200000);
    if (!strcmp(argv[2], "place") && argc == 7) {
        XMoveResizeWindow(d,w,atoi(argv[3]),atoi(argv[4]),atoi(argv[5]),atoi(argv[6]));
    } else if (!strcmp(argv[2], "key") && argc == 4) {
        KeyCode held[8]; unsigned count = 0;
        char *s = strtok(argv[3], "+");
        while (s) {
            KeySym k = !strcmp(s,"Ctrl") ? XK_Control_L : !strcmp(s,"Shift") ? XK_Shift_L :
                !strcmp(s,"Alt") ? XK_Alt_L : XStringToKeysym(s);
            KeyCode code = XKeysymToKeycode(d,k);
            if (!code || count == 8) return 2;
            held[count++] = code; XTestFakeKeyEvent(d,code,True,0); s = strtok(NULL,"+");
        }
        while (count) XTestFakeKeyEvent(d,held[--count],False,0);
    } else if ((!strcmp(argv[2], "click") || !strcmp(argv[2], "double")) && argc == 6) {
        unsigned button = strtoul(argv[3],NULL,0);
        pointer(d,x+atoi(argv[4]),y+atoi(argv[5]));
        int count = !strcmp(argv[2], "double") ? 2 : 1;
        for (int i=0;i<count;i++) {
            XTestFakeButtonEvent(d,button,True,0); XTestFakeButtonEvent(d,button,False,0);
        }
    } else if ((!strcmp(argv[2], "drag") || !strcmp(argv[2], "cancel-drag")) && argc == 8) {
        unsigned button=strtoul(argv[3],NULL,0);
        if (button < 1 || button > 3) return 2;
        int x1=atoi(argv[4]),y1=atoi(argv[5]),x2=atoi(argv[6]),y2=atoi(argv[7]);
        pointer(d,x+x1,y+y1); XTestFakeButtonEvent(d,button,True,0); XFlush(d); usleep(500000);
        for (int i=1;i<=24;i++) pointer(d,x+x1+(x2-x1)*i/24,y+y1+(y2-y1)*i/24);
        usleep(1500000);
        if (!strcmp(argv[2], "cancel-drag")) {
            KeyCode escape = XKeysymToKeycode(d, XK_Escape);
            XTestFakeKeyEvent(d,escape,True,0); XTestFakeKeyEvent(d,escape,False,0);
            XFlush(d); usleep(300000);
        }
        XTestFakeButtonEvent(d,button,False,0);
    } else return 2;
    XSync(d,False); XCloseDisplay(d); return 0;
}
