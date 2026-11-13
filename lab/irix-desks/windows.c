/* Observe managed windows without changing their focus, geometry or stacking.
 * Input modes send real XTest events and deliberately do not focus/raise first. */
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <X11/keysym.h>
#include <X11/extensions/XTest.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static Display *display;
static Window root;
static Atom state_atom;
static unsigned visited, emitted;
static void expired(int signo) { (void)signo; _exit(124); }
static int error(Display *d, XErrorEvent *e)
{
    if (e->error_code == BadWindow) return 0;
    char text[128]; XGetErrorText(d,e->error_code,text,sizeof(text));
    fprintf(stderr,"X error: %s\n",text); _exit(1);
}
static void string(const char *text)
{
    putchar('"');
    if (text) for (const unsigned char *p=(const unsigned char *)text; *p; p++) {
        if (*p=='"' || *p=='\\') printf("\\%c",*p);
        else if (*p<32 || *p>=127) printf("\\u%04x",*p);
        else putchar(*p);
    }
    putchar('"');
}
static void geometry(Window w)
{
    XWindowAttributes a; Window child; int x,y;
    if (!w || !XGetWindowAttributes(display,w,&a) ||
        !XTranslateCoordinates(display,w,root,0,0,&x,&y,&child)) { printf("null"); return; }
    printf("{\"x\":%d,\"y\":%d,\"width\":%d,\"height\":%d,\"map\":%d}",
        x,y,a.width,a.height,a.map_state);
}
static void visit(Window w, Window frame, unsigned stack, unsigned depth)
{
    if (++visited>8192 || depth>32) { fputs("window tree limit\n",stderr); exit(2); }
    Atom type; int format; unsigned long count,after; unsigned char *data=NULL;
    if (XGetWindowProperty(display,w,state_atom,0,2,False,AnyPropertyType,
            &type,&format,&count,&after,&data)==Success && type==state_atom &&
            format==32 && count==2 && !after) {
        unsigned long *state=(unsigned long *)data;
        char *name=NULL; XClassHint hint={0};
        XFetchName(display,w,&name); XGetClassHint(display,w,&hint);
        if (emitted++) putchar(',');
        printf("{\"id\":%lu,\"frame\":%lu,\"stack\":%u,\"state\":%lu,\"icon\":%lu,\"name\":",
            w,frame,stack,state[0],state[1]);
        string(name); printf(",\"instance\":"); string(hint.res_name);
        printf(",\"class\":"); string(hint.res_class);
        printf(",\"client\":"); geometry(w);
        printf(",\"frame_geometry\":"); geometry(frame);
        printf(",\"icon_geometry\":"); geometry(state[1]); putchar('}');
        if (name) XFree(name);
        if (hint.res_name) XFree(hint.res_name);
        if (hint.res_class) XFree(hint.res_class);
        XFree(data); return;
    }
    if (data) XFree(data);
    Window r,parent,*children=NULL; unsigned n=0;
    if (XQueryTree(display,w,&r,&parent,&children,&n)) {
        for (unsigned i=0;i<n;i++) visit(children[i],frame,stack,depth+1);
        if (children) XFree(children);
    }
}
static void motion(int x,int y)
{ XTestFakeMotionEvent(display,-1,x,y,0); XFlush(display); usleep(100000); }
static void key(char *spec)
{
    KeyCode codes[8]; unsigned n=0;
    for (char *s=strtok(spec,"+");s;s=strtok(NULL,"+")) {
        KeySym symbol=!strcmp(s,"Alt")?XK_Alt_L:!strcmp(s,"Ctrl")?XK_Control_L:
            !strcmp(s,"Shift")?XK_Shift_L:XStringToKeysym(s);
        KeyCode code=XKeysymToKeycode(display,symbol);
        if (!code || n==8) { fputs("invalid key\n",stderr); exit(2); }
        codes[n++]=code;
    }
    for (unsigned i=0;i<n;i++) XTestFakeKeyEvent(display,codes[i],True,0);
    while (n) XTestFakeKeyEvent(display,codes[--n],False,0);
    XFlush(display); usleep(200000);
}
int main(int argc,char **argv)
{
    if (argc<2) return 2;
    signal(SIGALRM,expired); alarm(30);
    display=XOpenDisplay(NULL); if (!display) return 2;
    XSetErrorHandler(error); root=DefaultRootWindow(display);
    if (!strcmp(argv[1],"list") && argc==2) {
        Window focus,r,parent,*children=NULL; int revert; unsigned n=0;
        state_atom=XInternAtom(display,"WM_STATE",False);
        XGetInputFocus(display,&focus,&revert);
        printf("{\"root\":%lu,\"focus\":%lu,\"windows\":[",root,focus);
        if (!XQueryTree(display,root,&r,&parent,&children,&n)) return 3;
        for (unsigned i=0;i<n;i++) visit(children[i],children[i],i,0);
        if (children) XFree(children);
        puts("]}");
    } else {
        int a,b,c,d; if (!XTestQueryExtension(display,&a,&b,&c,&d)) return 3;
        if (!strcmp(argv[1],"key") && argc>=3) {
            for (int i=2;i<argc;i++) key(argv[i]);
        } else if (!strcmp(argv[1],"point") && argc==4) {
            motion(atoi(argv[2]),atoi(argv[3]));
        } else if ((!strcmp(argv[1],"click") && argc==5) ||
                   (!strcmp(argv[1],"drag") && argc==7)) {
            unsigned button=strtoul(argv[2],NULL,0); if (button<1 || button>3) return 2;
            int x=atoi(argv[3]),y=atoi(argv[4]); motion(x,y);
            XTestFakeButtonEvent(display,button,True,0); XFlush(display); usleep(200000);
            if (argc==7) {
                int dx=atoi(argv[5])-x,dy=atoi(argv[6])-y;
                for (int i=1;i<=20;i++) motion(x+dx*i/20,y+dy*i/20);
                usleep(300000);
            }
            XTestFakeButtonEvent(display,button,False,0);
        } else return 2;
    }
    XSync(display,False); XCloseDisplay(display); return 0;
}
