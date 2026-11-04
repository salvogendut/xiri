/* Native X11/XTest round trips with a private receiver and stage diagnostics.
 * A watchdog expiry leaves the last BEGIN in the log; no Xlib in the handler. */
#include <X11/Xlib.h>
#include <X11/extensions/XTest.h>
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>

static unsigned iteration;
static const char *transport;

static void expired(int sig)
{
    static const char message[] = "XINPUT_TIMEOUT see last BEGIN stage\n";
    (void)sig;
    (void)write(STDERR_FILENO, message, sizeof(message) - 1);
    _exit(124);
}

static void stage(const char *name, const char *state)
{
    struct timespec now;
    if (clock_gettime(CLOCK_MONOTONIC, &now)) { perror("clock_gettime"); exit(2); }
    fprintf(stderr, "XINPUT %s iteration=%u display=%s stage=%s mono=%lld.%09ld\n",
        state, iteration, transport, name, (long long)now.tv_sec, now.tv_nsec);
}

static unsigned number(const char *text, unsigned limit)
{
    char *end;
    errno = 0;
    unsigned long n = strtoul(text, &end, 10);
    if (errno || !*text || *end || !n || n > limit) exit(2);
    return (unsigned)n;
}

int main(int argc, char **argv)
{
    if (argc != 4) {
        fprintf(stderr, "usage: xinput DISPLAY iterations watchdog-seconds\n");
        return 2;
    }
    transport = argv[1];
    unsigned count = number(argv[2], 10000), seconds = number(argv[3], 60);
    struct sigaction action = {0};
    action.sa_handler = expired;
    sigemptyset(&action.sa_mask);
    if (sigaction(SIGALRM, &action, NULL)) return 2;
    setvbuf(stdout, NULL, _IOLBF, 0);
    setvbuf(stderr, NULL, _IONBF, 0);
    alarm(seconds);
    stage("receiver-open", "BEGIN");
    Display *receiver = XOpenDisplay(transport);
    if (!receiver) return 3;
    stage("receiver-open", "END");
    XSetWindowAttributes attr = {0};
    attr.override_redirect = True;
    attr.background_pixel = WhitePixel(receiver, DefaultScreen(receiver));
    attr.event_mask = ButtonPressMask | ButtonReleaseMask;
    Window window = XCreateWindow(receiver, DefaultRootWindow(receiver),
        240, 300, 160, 120, 0, CopyFromParent, InputOutput, CopyFromParent,
        CWOverrideRedirect | CWBackPixel | CWEventMask, &attr);
    XStoreName(receiver, window, "Xiri native input receiver");
    XMapRaised(receiver, window);
    stage("receiver-map", "BEGIN");
    XSync(receiver, False);
    stage("receiver-map", "END");
    for (iteration = 1; iteration <= count; ++iteration) {
        alarm(seconds);
        stage("sender-open", "BEGIN");
        Display *sender = XOpenDisplay(transport);
        if (!sender) return 3;
        stage("sender-open", "END");
        int event, error, major, minor;
        stage("extension", "BEGIN");
        if (!XTestQueryExtension(sender, &event, &error, &major, &minor)) return 4;
        stage("extension", "END");
        stage("motion-sync", "BEGIN");
        if (!XTestFakeMotionEvent(sender, DefaultScreen(sender), 300, 350, 0)) return 4;
        XSync(sender, False);
        stage("motion-sync", "END");
        /* Match the original helper's timing, including the delayed release. */
        usleep(200000);
        stage("button-sync", "BEGIN");
        if (!XTestFakeButtonEvent(sender, 1, True, 0) ||
            !XTestFakeButtonEvent(sender, 1, False, 100)) return 4;
        XSync(sender, False);
        stage("button-sync", "END");
        stage("receive", "BEGIN");
        for (int expected = ButtonPress; expected <= ButtonRelease; ++expected) {
            XEvent ev;
            XNextEvent(receiver, &ev);
            if (ev.type != expected || ev.xbutton.window != window ||
                ev.xbutton.button != 1 || ev.xbutton.x_root != 300 ||
                ev.xbutton.y_root != 350) {
                fprintf(stderr, "unexpected input type=%d expected=%d\n", ev.type, expected);
                return 5;
            }
        }
        stage("receive", "END");
        stage("sender-close", "BEGIN");
        XCloseDisplay(sender);
        stage("sender-close", "END");
    }
    stage("receiver-close", "BEGIN");
    XDestroyWindow(receiver, window);
    XCloseDisplay(receiver);
    stage("receiver-close", "END");
    alarm(0);
    printf("XINPUT_PASS display=%s iterations=%u events=%u\n", transport, count, 2 * count);
    return 0;
}
