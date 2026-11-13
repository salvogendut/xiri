/* Real XTest mouse/key gestures, relative to the named application's window. */
#include <X11/Xlib.h>
#include <X11/keysym.h>
#include <X11/extensions/XTest.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
static Window find(Display *d, Window w, const char *name)
{
    char *s = NULL;
    if (XFetchName(d, w, &s) && s) {
        int equal = !strcmp(s, name); XFree(s); if (equal) return w;
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
    if (argc < 4) return 2;
    signal(SIGALRM, expired); alarm(30);
    Display *d = XOpenDisplay(NULL); if (!d) return 2;
    int a,b,c,e; if (!XTestQueryExtension(d,&a,&b,&c,&e)) return 2;
    Window w = !strncmp(argv[1], "0x", 2) ? strtoul(argv[1], NULL, 16) :
        find(d, DefaultRootWindow(d), argv[1]);
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
    if (!strcmp(argv[2], "key") && argc == 4) {
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
    } else if (!strcmp(argv[2], "click") && argc == 6) {
        unsigned button = strtoul(argv[3],NULL,0);
        pointer(d,x+atoi(argv[4]),y+atoi(argv[5]));
        XTestFakeButtonEvent(d,button,True,0); XTestFakeButtonEvent(d,button,False,0);
    } else if (!strcmp(argv[2], "drag") && argc == 7) {
        int x1=atoi(argv[3]),y1=atoi(argv[4]),x2=atoi(argv[5]),y2=atoi(argv[6]);
        pointer(d,x+x1,y+y1); XTestFakeButtonEvent(d,1,True,0); XFlush(d); usleep(100000);
        for (int i=1;i<=12;i++) pointer(d,x+x1+(x2-x1)*i/12,y+y1+(y2-y1)*i/12);
        XTestFakeButtonEvent(d,1,False,0);
    } else return 2;
    XSync(d,False); XCloseDisplay(d); return 0;
}
