/* Native X11/XTest round trips with a private receiver and stage diagnostics.
 * A watchdog expiry leaves the last BEGIN in the log; no Xlib in the handler. */
#include <X11/Xlib.h>
#include <X11/extensions/XTest.h>
#include <dlfcn.h>
#include <errno.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <ucontext.h>
#include <unistd.h>

static unsigned iteration;
static const char *transport;
static volatile sig_atomic_t delaying;

/* The watchdog must not enter Xlib or stdio. Preserve the interrupted native
 * PC and actual clock as well as the last stage, including time in usleep. */
static char *hexfield(char *out, const char *name, uint64_t value)
{
    static const char digits[] = "0123456789abcdef";
    while (*name) *out++ = *name++;
    for (int shift = 60; shift >= 0; shift -= 4)
        *out++ = digits[(value >> shift) & 15];
    return out;
}

static void expired(int sig, siginfo_t *info, void *context)
{
    static const char message[] = "XINPUT_TIMEOUT see last BEGIN stage\n";
    (void)sig; (void)info;
    (void)write(STDERR_FILENO, message, sizeof(message) - 1);
    struct timespec now = {0, 0};
    int clock_error = clock_gettime(CLOCK_MONOTONIC, &now);
    uint64_t pc = 0, ra = 0, sp = 0, a0 = 0, request[2] = {0, 0};
    int have_request = 0;
#if defined(__NetBSD__) && defined(__mips__)
    const ucontext_t *uc = context;
    pc = uc->uc_mcontext.__gregs[_REG_EPC];
    ra = uc->uc_mcontext.__gregs[_REG_RA];
    sp = uc->uc_mcontext.__gregs[_REG_SP];
    a0 = uc->uc_mcontext.__gregs[_REG_A0];
    /* The pinned native o32 libc keeps usleep's timespec inside its
     * 48-byte frame. Read only bytes inside that live stack frame while
     * usleep is active. PC and symbol addresses establish the call site;
     * these raw bytes alone do not assert that the request was initialized. */
    if (delaying && a0 >= sp && a0-sp <= 48-16 && (a0 & 7) == 0) {
        const volatile unsigned char *bytes = (const volatile unsigned char *)(uintptr_t)a0;
        for (unsigned i = 0; i < 16; ++i)
            request[i/8] = (request[i/8] << 8) | bytes[i];
        have_request = 1;
    }
#else
    (void)context;
#endif
    char line[512], *out = line;
    out = hexfield(out, "XINPUT_ALARM mono_sec=", (uint64_t)now.tv_sec);
    out = hexfield(out, " mono_nsec=", (uint64_t)now.tv_nsec);
    out = hexfield(out, " clock_error=", (uint64_t)clock_error);
    out = hexfield(out, " pc=", pc);
    out = hexfield(out, " ra=", ra);
    out = hexfield(out, " sp=", sp);
    out = hexfield(out, " a0=", a0);
    out = hexfield(out, " request_captured=", (uint64_t)have_request);
    out = hexfield(out, " request0=", request[0]);
    out = hexfield(out, " request1=", request[1]);
    *out++ = '\n';
    (void)write(STDERR_FILENO, line, (size_t)(out-line));
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
    action.sa_sigaction = expired;
    action.sa_flags = SA_SIGINFO;
    sigemptyset(&action.sa_mask);
    if (sigaction(SIGALRM, &action, NULL)) return 2;
    setvbuf(stdout, NULL, _IOLBF, 0);
    setvbuf(stderr, NULL, _IONBF, 0);
    fprintf(stderr, "XINPUT_NATIVE usleep=%p nanosleep=%p\n",
        dlsym(RTLD_DEFAULT, "usleep"), dlsym(RTLD_DEFAULT, "__nanosleep50"));
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
        stage("delay", "BEGIN");
        delaying = 1;
        usleep(200000);
        delaying = 0;
        stage("delay", "END");
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
