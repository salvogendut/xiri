/* Diagnostic only: preserve the traced click's X requests and alarm. */
#include <X11/Xlibint.h>
#include <X11/extensions/XTest.h>
#include <sys/types.h>
#include <fcntl.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <ucontext.h>
#include <unistd.h>

static int memfd = -1, outfd = -1, regsfd = -1;
static pid_t server;
static Display *display;
static struct item { char name[40]; uint32_t address, words; } items[32];
static unsigned nitems;

/* No stdio, allocation or Xlib calls from the signal handler. */
static void hexword(uint32_t value)
{
    const char digits[] = "0123456789abcdef";
    char out[9];
    for (unsigned i = 0; i < 8; i++) out[i] = digits[(value >> (28-4*i)) & 15];
    out[8] = ' ';
    (void)write(outfd, out, sizeof(out));
}

static void words(const char *name, const uint32_t *data, unsigned count)
{
    unsigned len = 0;
    while (name[len]) len++;
    (void)write(outfd, name, len);
    (void)write(outfd, " ", 1);
    for (unsigned i = 0; i < count; i++) hexword(data[i]);
    (void)write(outfd, "\n", 1);
}

static uint32_t remote(const char *name, uint32_t address, unsigned count)
{
    uint32_t data[256] = {0};
    ssize_t bytes = pread(memfd, data, count*4, address);
    uint32_t meta[] = {address, (uint32_t)bytes};
    words("READ", meta, 2);
    if (bytes > 0) words(name, data, (unsigned)bytes/4);
    return bytes >= 4 ? data[0] : 0;
}

static void expired(int sig, siginfo_t *info, void *context)
{
    static const char text[] = "CLICK_TIMEOUT state captured in snapshot\n";
    ucontext_t *uc = context;
    struct timespec mono = {0}, real = {0};
    (void)sig; (void)info;
    clock_gettime(CLOCK_MONOTONIC, &mono);
    clock_gettime(CLOCK_REALTIME, &real);
    uint32_t timewords[] = {(uint32_t)mono.tv_sec, (uint32_t)mono.tv_nsec,
                           (uint32_t)real.tv_sec, (uint32_t)real.tv_nsec};
    words("TIME", timewords, 4);
    words("CLIENT_REGS", (uint32_t *)uc->uc_mcontext.__gregs, _NGREG);
    if (display) {
        uint32_t xstate[] = {display->fd, display->request, display->last_request_read,
            display->qlen, (uintptr_t)display->buffer, (uintptr_t)display->bufptr, display->resource_base};
        words("XLIB", xstate, 7);
    }
    int stopped = kill(server, SIGSTOP) == 0;
    uint32_t stop = stopped;
    words("SERVER_STOP", &stop, 1);
    if (regsfd >= 0) {
        uint32_t regs[256] = {0};
        ssize_t bytes = read(regsfd, regs, sizeof(regs));
        uint32_t meta = bytes;
        words("SERVER_REG_BYTES", &meta, 1);
        if (bytes > 0) words("SERVER_REGS", regs, (unsigned)bytes/4);
    }
    for (unsigned i = 0; i < nitems; i++) {
        uint32_t pointer = remote(items[i].name, items[i].address, items[i].words);
        if (items[i].name[0]=='c' && items[i].name[1]=='l') {
            uint32_t clients[64] = {0};
            if (pread(memfd, clients, sizeof(clients), items[i].address)==sizeof(clients)) {
                for (unsigned c=0;c<64;c++) if (clients[c]) {
                    uint32_t data[32] = {0};
                    if (pread(memfd, data, sizeof(data), clients[c])!=sizeof(data)) continue;
                    words("CLIENT", data, 32);
                    if (data[2]) remote("CLIENT_REQUEST", data[2], 16);
                    if (data[3]) {
                        uint32_t oc[7] = {0};
                        if (pread(memfd,oc,sizeof(oc),data[3])==sizeof(oc)) {
                            words("CLIENT_OS",oc,7);
                            if (oc[1]) remote("CLIENT_INPUT",oc[1],7);
                            if (oc[2]) remote("CLIENT_OUTPUT",oc[2],4);
                        }
                    }
                }
            }
        }
        if (pointer && items[i].name[0] == 'p') {
            uint32_t pending[7] = {0};
            if (pread(memfd, pending, sizeof(pending), pointer) == sizeof(pending)) {
                words("PENDING_NODE", pending, 7);
                remote("PENDING_CLIENT", pending[3], 64);
            }
        }
        if (pointer && items[i].name[0] == 'g' && items[i].name[4] == 'C')
            remote("GRAB_CLIENT", pointer, 64);
    }
    if (stopped) (void)kill(server, SIGCONT);
    (void)write(STDERR_FILENO, text, sizeof(text)-1);
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
    if (argc != 5) return 2;
    FILE *config = fopen(argv[3], "r");
    if (!config || fscanf(config, "%d", &server) != 1 || server <= 1) return 2;
    while (nitems < 32 && fscanf(config, "%39s %x %u", items[nitems].name,
           &items[nitems].address, &items[nitems].words) == 3) {
        if (items[nitems].words > 256) return 2;
        nitems++;
    }
    fclose(config);
    char path[80];
    snprintf(path, sizeof(path), "/proc/%d/mem", server);
    memfd = open(path, O_RDONLY);
    outfd = open(argv[4], O_CREAT | O_TRUNC | O_WRONLY, 0600);
    if (memfd < 0 || outfd < 0) { perror("snapshot open"); return 2; }
    snprintf(path, sizeof(path), "/proc/%d/regs", server);
    regsfd = open(path, O_RDONLY);
    snprintf(path, sizeof(path), "/proc/%d/maps", getpid());
    int maps = open(path, O_RDONLY);
    if (maps >= 0) {
        char buffer[4096]; ssize_t got;
        (void)write(outfd,"SELF_MAPS_BEGIN\n",16);
        while ((got=read(maps,buffer,sizeof(buffer)))>0) (void)write(outfd,buffer,(size_t)got);
        (void)write(outfd,"SELF_MAPS_END\n",14);
        close(maps);
    }
    struct sigaction action = {0};
    action.sa_sigaction = expired;
    action.sa_flags = SA_SIGINFO;
    sigemptyset(&action.sa_mask);
    if (sigaction(SIGALRM, &action, NULL)) return 2;
    setvbuf(stderr, NULL, _IONBF, 0);
    alarm(10);
    stage("open", "BEGIN");
    display = XOpenDisplay(NULL);
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
    display = NULL;
    stage("close", "END");
    alarm(0);
    return 0;
}
