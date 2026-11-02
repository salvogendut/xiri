/* Arrange real X windows for reproducible, unobscured screenshot evidence. */
#include <X11/Xlib.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static Window find(Display *d,Window w,const char *name)
{
    char *s=NULL;
    if(XFetchName(d,w,&s)&&s) {
        int match=!strcmp(s,name);XFree(s);if(match)return w;
    }
    Window root,parent,*children=NULL,found=None;unsigned n;
    if(XQueryTree(d,w,&root,&parent,&children,&n)) {
        for(unsigned i=0;i<n&&!found;i++)found=find(d,children[i],name);
        if(children)XFree(children);
    }
    return found;
}
int main(int argc,char **argv)
{
    if(argc!=6)return 2;
    Display *d=XOpenDisplay(NULL);if(!d)return 3;
    Window w=find(d,DefaultRootWindow(d),argv[1]);if(!w)return 4;
    XMoveResizeWindow(d,w,atoi(argv[2]),atoi(argv[3]),atoi(argv[4]),atoi(argv[5]));
    XRaiseWindow(d,w);XSync(d,False);XCloseDisplay(d);
    return 0;
}
