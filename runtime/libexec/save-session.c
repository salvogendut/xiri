/* Coordinate the original 4Dwm end_session/reaper protocol with our native
 * descendant supervisor. 4Dwm owns saving, including explicit-save policy. */
#include <sys/types.h>
#include <sys/wait.h>
#include <X11/Xlib.h>
#include <X11/Xatom.h>
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

static void timeout(int sig) { (void)sig; _exit(2); }

int main(void)
{
    /* Also bound XOpenDisplay/XSync, not just the event wait. The guard owns
     * cleanup of this helper and tellwm if either cannot finish. */
    signal(SIGALRM, timeout);
    alarm(12);
    Display *d = XOpenDisplay(NULL);
    if (!d) return 2;
    Window root = DefaultRootWindow(d);
    Atom type, commands = XInternAtom(d, "_SGI_TELL_WM", False);
    int format, supported = 0;
    unsigned long items, left;
    unsigned char *data = NULL;
    if (XGetWindowProperty(d, root, commands, 0, 4096, False, XA_STRING,
        &type, &format, &items, &left, &data) == Success && type == XA_STRING && format == 8 && !left) {
        for (unsigned long i = 0; i < items;) {
            size_t n = strnlen((char *)data + i, items - i);
            if (n == 11 && !memcmp(data + i, "end_session", n)) supported = 1;
            i += n + 1;
        }
    }
    if (data) XFree(data);
    if (!supported) {
        puts("SESSION_SAVE disabled (no end_session capability)");
        XCloseDisplay(d); return 0;
    }
    Atom property = XInternAtom(d, "_SGI_SESSION_PROPERTY", False);
    XSelectInput(d, root, PropertyChangeMask);
    const unsigned char value[] = "xiri";
    XChangeProperty(d, root, property, XA_STRING, 8, PropModeReplace, value, sizeof(value)-1);
    XSync(d, False);
    pid_t child = fork();
    if (child < 0) { perror("tellwm fork"); XCloseDisplay(d); return 2; }
    if (!child) {
        close(ConnectionNumber(d));
        execl("/emul/irix/usr/bin/X11/tellwm", "tellwm", "end_session", (char *)NULL);
        perror("tellwm exec"); _exit(126);
    }
    int status;
    while (waitpid(child, &status, 0) < 0) if (errno != EINTR) return 2;
    if (!WIFEXITED(status) || WEXITSTATUS(status)) { XCloseDisplay(d); return 2; }
    for (;;) {
        XEvent event;
        XNextEvent(d, &event);
        if (event.type == PropertyNotify && event.xproperty.atom == property &&
            event.xproperty.state == PropertyDelete) break;
    }
    puts("SESSION_SAVE acknowledged by 4Dwm");
    XCloseDisplay(d);
    return 0;
}
