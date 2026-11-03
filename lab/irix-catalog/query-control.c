/* Deliberately block other X clients to verify the survey query deadline. */
#include <X11/Xlib.h>
#include <stdio.h>
#include <unistd.h>
int main(void)
{
    alarm(30);
    Display *d=XOpenDisplay(NULL);
    if (!d) return 2;
    XGrabServer(d);
    XSync(d,False);
    puts("SURVEY_SERVER_HELD");
    fflush(stdout);
    sleep(20);
    XUngrabServer(d);
    XSync(d,False);
    XCloseDisplay(d);
    return 0;
}
