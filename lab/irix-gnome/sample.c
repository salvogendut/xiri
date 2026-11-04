/* Bounded native NetBSD sampler for an unmodified IRIX child.
 * The pinned MIPS64 kernel exposes 38 64-bit register slots to native o32
 * ptrace as well. Keep the guard used by the earlier GIMP diagnostic. */
#include <sys/types.h>
#include <sys/ptrace.h>
#include <sys/wait.h>
#include <errno.h>
#include <fcntl.h>
#include <grp.h>
#include <inttypes.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

static pid_t child = -1;
static volatile sig_atomic_t stop_requested;
static void cleanup(void)
{
    if (child > 0) {
        int status;
        (void)kill(child, SIGKILL);
        for (;;) {
            pid_t got = waitpid(child, &status, 0);
            if (got < 0) { if (errno == EINTR) continue; break; }
            if (WIFEXITED(status) || WIFSIGNALED(status)) break;
        }
        child = -1;
    }
}
static void fail(const char *what) { perror(what); exit(2); }
static void interrupted(int sig) { stop_requested = sig; }
static void pause_ms(long ms)
{
    struct timespec delay = {ms / 1000, (ms % 1000) * 1000000};
    if (stop_requested) exit(130);
    while (nanosleep(&delay, &delay) < 0) {
        if (stop_requested) exit(130);
        if (errno != EINTR) fail("nanosleep");
    }
}
static int waited(void)
{
    struct timespec begin, now;
    int status;
    if (clock_gettime(CLOCK_MONOTONIC, &begin)) fail("clock");
    for (;;) {
        if (stop_requested) exit(130);
        pid_t got = waitpid(child, &status, WNOHANG);
        if (got == child) {
            if (WIFEXITED(status) || WIFSIGNALED(status)) child = -1;
            return status;
        }
        if (got < 0 && errno != EINTR) {
            if (errno == ECHILD) child = -1;
            fail("waitpid");
        }
        if (clock_gettime(CLOCK_MONOTONIC, &now)) fail("clock");
        if (now.tv_sec - begin.tv_sec >= 10) { errno = ETIMEDOUT; fail("wait deadline"); }
        pause_ms(10);
    }
}
static void memory(const char *label, uint64_t address, size_t length)
{
    unsigned char bytes[512];
    if (address > UINT32_MAX || length > sizeof(bytes)) return;
    struct ptrace_io_desc io = {PIOD_READ_D, (void *)(uintptr_t)address, bytes, length};
    errno = 0;
    int rc = ptrace(PT_IO, child, &io, sizeof(io));
    printf("MEM %s address=%08" PRIx64 " error=%d bytes=%zu hex=", label,
        address, rc < 0 ? errno : 0, rc < 0 ? 0 : io.piod_len);
    if (!rc) for (size_t i = 0; i < io.piod_len; i++) printf("%02x", bytes[i]);
    putchar('\n');
}
static void sample(unsigned index, int sig)
{
    struct { uint64_t regs[38]; unsigned char guard[64]; } capture;
    memset(&capture, 0xa5, sizeof(capture));
    if (ptrace(PT_GETREGS, child, capture.regs, 0) < 0) fail("registers");
    for (size_t i = 0; i < sizeof(capture.guard); i++)
        if (capture.guard[i] != 0xa5) { errno = EOVERFLOW; fail("register guard"); }
    uint64_t *r = capture.regs;
    printf("SAMPLE index=%u pid=%ld signal=%d pc=%016" PRIx64 "\n", index, (long)child, sig, r[37]);
    printf("REGS");
    for (size_t i = 0; i < 38; i++) printf(" %zu=%016" PRIx64, i, r[i]);
    putchar('\n');
    memory("pc", r[37] >= 32 ? r[37] - 32 : r[37], 128);
    memory("ra", r[31] >= 32 ? r[31] - 32 : r[31], 128);
    memory("stack", r[29], 512);
    memory("a0", r[4], 128);
    memory("a1", r[5], 128);
    memory("s0", r[16], 128);
    fflush(stdout);
}
int main(int argc, char **argv)
{
    if (argc < 5) return 2; /* uid gid environment-file executable [arguments] */
    char *env[65] = {NULL}, *line = NULL;
    size_t capacity = 0, count = 0;
    FILE *in = fopen(argv[3], "r");
    if (!in) fail("environment");
    while (getline(&line, &capacity, in) >= 0) {
        line[strcspn(line, "\r\n")] = 0;
        if (!*line) continue;
        if (!strchr(line, '=') || count == 64) return 2;
        env[count++] = strdup(line);
        if (!env[count-1]) fail("strdup");
    }
    if (ferror(in) || fclose(in)) fail("environment read");
    free(line);
    char *end;
    errno = 0;
    unsigned long uid = strtoul(argv[1], &end, 10);
    if (errno || end == argv[1] || *end) return 2;
    unsigned long gid = strtoul(argv[2], &end, 10);
    if (errno || end == argv[2] || *end) return 2;
    if (uid > 65534 || gid > 65534 || atexit(cleanup)) return 2;
    signal(SIGTERM, interrupted); signal(SIGINT, interrupted);
    child = fork();
    if (child < 0) fail("fork");
    if (!child) {
        int fd = open("/dev/null", O_RDONLY);
        if (fd < 0 || dup2(fd, 0) < 0) _exit(125);
        close(fd);
        fd = open("sample-child.out", O_WRONLY|O_CREAT|O_TRUNC, 0600);
        if (fd < 0 || dup2(fd, 1) < 0) _exit(125);
        close(fd);
        fd = open("sample-child.err", O_WRONLY|O_CREAT|O_TRUNC, 0600);
        if (fd < 0 || dup2(fd, 2) < 0) _exit(125);
        close(fd);
        if (ptrace(PT_TRACE_ME, 0, NULL, 0) < 0) _exit(124);
        if (setgroups(0, NULL) || setgid((gid_t)gid) || setuid((uid_t)uid)) _exit(125);
        if (chdir("/usr/people/xiritest")) _exit(125);
        execve(argv[4], argv + 4, env);
        _exit(126);
    }
    int status = waited();
    if (!WIFSTOPPED(status) || WSTOPSIG(status) != SIGTRAP) {
        printf("BAD_EXEC status=%d\n", status); return 2;
    }
    sample(0, SIGTRAP);
    for (unsigned i = 1; i <= 12; i++) {
        if (ptrace(PT_CONTINUE, child, (void *)1, 0) < 0) fail("continue");
        pause_ms(i == 1 ? 5000 : 500);
        if (kill(child, SIGSTOP) < 0 && errno != ESRCH) fail("stop sample");
        status = waited();
        if (!WIFSTOPPED(status)) break;
        sample(i, WSTOPSIG(status));
        if (WSTOPSIG(status) != SIGSTOP) break;
    }
    if (WIFSTOPPED(status)) {
        if (kill(child, SIGKILL)) fail("kill sampled child");
        status = waited();
    }
    if (!WIFEXITED(status) && !WIFSIGNALED(status)) return 2;
    printf("END exit=%d signal=%d\n", WIFEXITED(status) ? WEXITSTATUS(status) : -1,
        WIFSIGNALED(status) ? WTERMSIG(status) : 0);
    child = -1;
    for (size_t i = 0; i < count; i++) free(env[i]);
    return 0;
}
