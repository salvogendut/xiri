/* List only viewable named/classed X windows; ignore windows closing mid-query. */
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
static unsigned int visited;
static int limited;
static int ignore_error(Display *d, XErrorEvent *e) {(void)d;(void)e;return 0;}
static void hex(const char *s)
{
    if(s)for(;*s;s++)printf("%02x",(unsigned char)*s);
}
static void walk(Display *d, Window w, unsigned int depth)
{
    Window root,parent,*children=NULL;
    unsigned int count=0;
    XWindowAttributes a;
    if(depth>64 || ++visited>20000){limited=1;return;}
    if(!XGetWindowAttributes(d,w,&a))return;
    if(a.map_state==IsViewable && a.width>1 && a.height>1) {
        char *name=NULL;
        XClassHint c={0};
        XFetchName(d,w,&name);XGetClassHint(d,w,&c);
        if((name && *name) || c.res_class) {
            printf("WINDOW id=%lx width=%d height=%d name=",w,a.width,a.height);hex(name);
            printf(" class=");hex(c.res_class);printf(" instance=");hex(c.res_name);putchar('\n');
        }
        if(name)XFree(name);
        if(c.res_name)XFree(c.res_name);
        if(c.res_class)XFree(c.res_class);
    }
    if(XQueryTree(d,w,&root,&parent,&children,&count)) {
        for(unsigned int i=0;i<count;i++)walk(d,children[i],depth+1);
        if(children)XFree(children);
    }
}
int main(void)
{
    alarm(15);
    Display *d=XOpenDisplay(NULL);
    if(!d){fputs("Cannot open survey display\n",stderr);return 2;}
    XSetErrorHandler(ignore_error);walk(d,DefaultRootWindow(d),0);XCloseDisplay(d);
    return limited ? 3 : 0;
}
