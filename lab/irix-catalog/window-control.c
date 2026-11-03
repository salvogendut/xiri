#include <X11/Xlib.h>
#include <unistd.h>
int main(void){alarm(15);Display*d=XOpenDisplay(0);if(!d)return 2;Window r=DefaultRootWindow(d);Window a=XCreateSimpleWindow(d,r,0,0,100,100,0,0,0),b=XCreateSimpleWindow(d,r,110,0,100,100,0,0,0);XStoreName(d,a,"SURVEY_VISIBLE");XStoreName(d,b,"SURVEY_HIDDEN");XMapWindow(d,a);XSync(d,False);pause();return 0;}
