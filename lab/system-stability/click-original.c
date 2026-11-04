#include <X11/Xlib.h>
#include <X11/extensions/XTest.h>
#include <signal.h>
#include <stdlib.h>
#include <unistd.h>
int main(int argc,char **argv) {
    alarm(10);
    if(argc!=3) return 2;
    Display *d=XOpenDisplay(NULL);
    if(!d) return 3;
    XTestFakeMotionEvent(d,DefaultScreen(d),atoi(argv[1]),atoi(argv[2]),0);
    XSync(d,False);usleep(200000);
    XTestFakeButtonEvent(d,1,True,0);XTestFakeButtonEvent(d,1,False,100);
    XSync(d,False);XCloseDisplay(d);return 0;
}
