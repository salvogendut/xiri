/* Native control for a query-loop client competing with a delayed XTest release.
 * The receiver behaves like a drag handler: query the pointer until button up.
 * No IRIX application, server grab, grab immunity or extended click deadline.
 */
#include <X11/Xlib.h>
#include <X11/extensions/XTest.h>
#include <sys/wait.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>

static void expired(int signal_number)
{
    const char message[] = "FAIRNESS_TIMEOUT\n";
    (void)signal_number;
    (void)write(STDERR_FILENO, message, sizeof(message)-1);
    _exit(125);
}

static double now(void)
{
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) exit(2);
    return (double)t.tv_sec + (double)t.tv_nsec / 1000000000.;
}

int main(int argc, char **argv)
{
    if (argc != 2) return 2;
    struct sigaction action = {0};
    action.sa_handler = expired;
    sigemptyset(&action.sa_mask);
    if (sigaction(SIGALRM, &action, NULL)) return 2;
    setvbuf(stdout, NULL, _IOLBF, 0);
    alarm(20);
    Display *d = XOpenDisplay(NULL);
    if (!d) return 3;
    XSetWindowAttributes a = {0};
    a.override_redirect = True;
    a.background_pixel = WhitePixel(d, DefaultScreen(d));
    a.event_mask = ButtonPressMask | ButtonReleaseMask;
    Window w = XCreateWindow(d, DefaultRootWindow(d), 240, 300, 160, 120,
        0, CopyFromParent, InputOutput, CopyFromParent,
        CWOverrideRedirect | CWBackPixel | CWEventMask, &a);
    XStoreName(d, w, "Xiri native pointer-query control");
    XMapRaised(d, w);
    XTestFakeMotionEvent(d, DefaultScreen(d), 300, 350, 0);
    /* Exercise the server's normal input-priority boost before the control. */
    for (unsigned i = 0; i < 20; i++) {
        XTestFakeButtonEvent(d, 1, True, 0);
        XTestFakeButtonEvent(d, 1, False, 0);
    }
    XSync(d, False);
    unsigned warmup = 0;
    while (XPending(d)) {
        XEvent event;
        XNextEvent(d, &event);
        if (event.type == ButtonPress || event.type == ButtonRelease) warmup++;
    }
    if (warmup != 40) return 4;
    double began = now();
    pid_t child = fork();
    if (child < 0) return 2;
    if (!child) {
        close(ConnectionNumber(d));
        execl(argv[1], argv[1], "300", "350", (char *)NULL);
        _exit(127);
    }
    printf("FAIRNESS_BEGIN pid=%d uid=%lu sender=%d window=0x%lx warmup=%u\n",
        getpid(), (unsigned long)getuid(), child, w, warmup);
    XEvent event;
    do { XNextEvent(d, &event); } while (event.type != ButtonPress);
    unsigned long queries = 0;
    unsigned mask = Button1Mask;
    Window root, under;
    int rx, ry, wx, wy;
    while ((mask & Button1Mask) && now() - began < 12.) {
        if (!XQueryPointer(d, w, &root, &under, &rx, &ry, &wx, &wy, &mask)) return 4;
        queries++;
    }
    int released = !(mask & Button1Mask), status;
    double elapsed = now() - began;
    if (waitpid(child, &status, 0) != child) return 2;
    int code = WIFEXITED(status) ? WEXITSTATUS(status) : 128+WTERMSIG(status);
    /* Reset synthetic button state after recording the failed/successful case. */
    XTestFakeButtonEvent(d, 1, False, 0);
    XSync(d, False);
    XDestroyWindow(d, w);
    XCloseDisplay(d);
    alarm(0);
    printf("FAIRNESS_RESULT released=%d sender_status=%d queries=%lu seconds=%.6f\n",
        released, code, queries, elapsed);
    return released && code == 0 ? 0 : 1;
}
