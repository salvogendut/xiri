/* Send actual XTest keyboard events to a named terminal window. */
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <X11/keysym.h>
#include <X11/extensions/XTest.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
static Window find(Display *d, Window w, const char *name)
{
    char *s = NULL;
    if (XFetchName(d, w, &s) && s) {
        int match = !strcmp(s, name);
        XFree(s);
        if (match) return w;
    }
    Window root, parent, *children = NULL, found = None;
    unsigned count;
    if (XQueryTree(d, w, &root, &parent, &children, &count)) {
        for (unsigned i = 0; i < count && !found; i++) found = find(d, children[i], name);
        if (children) XFree(children);
    }
    return found;
}
int main(int argc, char **argv)
{
    if (argc != 4) return 2;
    Display *d = XOpenDisplay(argv[1]);
    if (!d) return 2;
    int a,b,c,e;
    if (!XTestQueryExtension(d,&a,&b,&c,&e)) return 2;
    Window w = find(d, DefaultRootWindow(d), argv[2]);
    if (!w) return 3;
    XWindowAttributes attrs;
    int ready = 0;
    for (int i = 0; i < 100; i++) {
        if (XGetWindowAttributes(d, w, &attrs) &&
            attrs.map_state == IsViewable && attrs.width > 200 && attrs.height > 120) {
            ready = 1; break;
        }
        usleep(100000);
    }
    if (!ready) { fprintf(stderr, "terminal not viewable at usable geometry\n"); return 5; }
    printf("TYPE_WINDOW width=%d height=%d viewable=1\n", attrs.width, attrs.height);
    XRaiseWindow(d,w);
    XWarpPointer(d,None,w,0,0,0,0,100,100);
    XSetInputFocus(d,w,RevertToParent,CurrentTime);
    XSync(d,False);
    usleep(200000);
    int low,high,width;
    XDisplayKeycodes(d,&low,&high);
    KeySym *map = XGetKeyboardMapping(d,low,high-low+1,&width);
    KeyCode shift = XKeysymToKeycode(d,XK_Shift_L);
    for (const unsigned char *s=(const unsigned char *)argv[3]; *s; s++) {
        KeySym target = *s=='\n' ? XK_Return : *s;
        int code=0, shifted=0;
        for (int col=0;col<2 && !code;col++)
            for (int k=low;k<=high;k++)
                if (map[(k-low)*width+col]==target) { code=k;shifted=col;break; }
        if (!code) { fprintf(stderr,"unmapped character %u\n",*s); return 4; }
        if (shifted) XTestFakeKeyEvent(d,shift,True,0);
        XTestFakeKeyEvent(d,code,True,0);
        XTestFakeKeyEvent(d,code,False,0);
        if (shifted) XTestFakeKeyEvent(d,shift,False,0);
        XFlush(d);
        usleep(10000);
    }
    XSync(d,False);
    XFree(map); XCloseDisplay(d);
    return 0;
}
