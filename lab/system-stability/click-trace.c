/* The previous focus helper's X calls/timing, with blocking-stage diagnostics. */
#include <X11/Xlib.h>
#include <X11/extensions/XTest.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>

static void expired(int sig)
{
    static const char text[] = "CLICK_TIMEOUT see last BEGIN stage\n";
    (void)sig;
    (void)write(STDERR_FILENO, text, sizeof(text) - 1);
    _exit(124);
}

static void stage(const char *name, const char *state)
{
    struct timespec now;
    if (clock_gettime(CLOCK_MONOTONIC, &now)) exit(2);
    fprintf(stderr, "CLICK %s stage=%s mono=%lld.%09ld\n", state, name,
        (long long)now.tv_sec, now.tv_nsec);
}

int main(int argc, char **argv)
{
    if (argc != 3) return 2;
    struct sigaction action = {0};
    action.sa_handler = expired;
    sigemptyset(&action.sa_mask);
    if (sigaction(SIGALRM, &action, NULL)) return 2;
    setvbuf(stderr, NULL, _IONBF, 0);
    alarm(10);
    stage("open", "BEGIN");
    Display *display = XOpenDisplay(NULL);
    if (!display) return 3;
    stage("open", "END");
    stage("motion-sync", "BEGIN");
    XTestFakeMotionEvent(display, DefaultScreen(display), atoi(argv[1]), atoi(argv[2]), 0);
    XSync(display, False);
    stage("motion-sync", "END");
    usleep(200000);
    stage("button-sync", "BEGIN");
    XTestFakeButtonEvent(display, 1, True, 0);
    XTestFakeButtonEvent(display, 1, False, 100);
    XSync(display, False);
    stage("button-sync", "END");
    stage("close", "BEGIN");
    XCloseDisplay(display);
    stage("close", "END");
    alarm(0);
    return 0;
}
