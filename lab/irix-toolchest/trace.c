/* Native o32 tracer for the pinned LP64 MIPS kernel. Vendor bytes stay private. */
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
static void cleanup(void) {
    if (child > 0) {
        (void)kill(child, SIGKILL);
        while (waitpid(child, NULL, 0) < 0 && errno == EINTR) {}
    }
}
static void fail(const char *what) { perror(what); exit(2); }
static int waited(void) {
    int status;
    struct timespec begin, now, pause = {0, 10000000};
    if (clock_gettime(CLOCK_MONOTONIC, &begin)) fail("clock");
    for (;;) {
        pid_t got = waitpid(child, &status, WNOHANG);
        if (got == child) return status;
        if (got < 0 && errno != EINTR) fail("waitpid");
        if (clock_gettime(CLOCK_MONOTONIC, &now)) fail("clock");
        if (now.tv_sec - begin.tv_sec >= 30) { errno = ETIMEDOUT; fail("trace deadline"); }
        nanosleep(&pause, NULL);
    }
}
static void memory(const char *label, uint64_t address, size_t size) {
    unsigned char data[512];
    if (address > UINT32_MAX || size > sizeof(data)) return;
    struct ptrace_io_desc io = {PIOD_READ_D, (void *)(uintptr_t)address, data, size};
    errno = 0;
    int rc = ptrace(PT_IO, child, &io, sizeof(io));
    printf("MEM %s address=%08" PRIx64 " error=%d bytes=%zu hex=", label, address, rc < 0 ? errno : 0, rc < 0 ? 0 : io.piod_len);
    if (rc == 0) for (size_t i = 0; i < io.piod_len; i++) printf("%02x", data[i]);
    putchar('\n');
}
static void registers(const char *phase, int sig) {
    /* sys/arch/mips supplies no process_reg32/read_regs32 overrides:
     * netbsd32 ptrace therefore copies the kernel's 38 x 64-bit slots.
     * The raw trap-frame PC is slot 37 (slot 35 is BadVAddr). */
    struct { uint64_t regs[38]; unsigned char guard[64]; } capture;
    memset(&capture, 0xa5, sizeof(capture));
    if (ptrace(PT_GETREGS, child, capture.regs, 0) < 0) fail("PT_GETREGS");
    for (size_t i = 0; i < sizeof(capture.guard); i++)
        if (capture.guard[i] != 0xa5) { errno = EOVERFLOW; fail("register guard"); }
    struct ptrace_siginfo info;
    if (ptrace(PT_GET_SIGINFO, child, &info, sizeof(info)) < 0) fail("PT_GET_SIGINFO");
    printf("STOP phase=%s signal=%d code=%d address=%08" PRIxPTR " pc=%016" PRIx64 "\n", phase, sig, info.psi_siginfo.si_code, (uintptr_t)info.psi_siginfo.si_addr, capture.regs[37]);
    printf("REGS");
    for (size_t i = 0; i < 38; i++) printf(" %zu=%016" PRIx64, i, capture.regs[i]);
    putchar('\n');
    if (!strcmp(phase, "fault")) {
        uint64_t pc = capture.regs[37];
        memory("pc", pc >= 32 ? pc - 32 : pc, 128);
        memory("stack", capture.regs[29], 512);
        memory("ra", capture.regs[31] >= 32 ? capture.regs[31] - 32 : capture.regs[31], 128);
        memory("a0", capture.regs[4], 128);
        memory("a1", capture.regs[5], 128);
        memory("a2", capture.regs[6], 128);
        memory("gp", capture.regs[28], 128);
    }
    fflush(stdout);
}
int main(int argc, char **argv) {
    if (argc < 5) return 2; /* uid gid environment-file executable [arguments] */
    char *env[33] = {NULL}, *line = NULL; size_t cap = 0, count = 0;
    FILE *in = fopen(argv[3], "r"); if (!in) fail("environment");
    while (getline(&line, &cap, in) >= 0) {
        line[strcspn(line, "\r\n")] = 0;
        if (!*line) continue;
        if (!strchr(line, '=') || count == 32) return 2;
        env[count++] = strdup(line); if (!env[count-1]) fail("strdup");
    }
    if (ferror(in) || fclose(in)) fail("environment read");
    free(line);
    unsigned long uid = strtoul(argv[1], NULL, 10), gid = strtoul(argv[2], NULL, 10);
    if (uid > 65534 || gid > 65534) return 2;
    if (atexit(cleanup)) return 2;
    child = fork(); if (child < 0) fail("fork");
    if (!child) {
        int fd = open("input.txt", O_RDONLY); if (fd < 0 || dup2(fd, 0) < 0) _exit(125); close(fd);
        fd = open("trace-child.out", O_WRONLY|O_CREAT|O_TRUNC, 0666); if (fd < 0 || dup2(fd, 1) < 0) _exit(125); close(fd);
        fd = open("trace-child.err", O_WRONLY|O_CREAT|O_TRUNC, 0666); if (fd < 0 || dup2(fd, 2) < 0) _exit(125); close(fd);
        if (setgroups(0, NULL) || setgid((gid_t)gid) || setuid((uid_t)uid)) _exit(125);
        if (ptrace(PT_TRACE_ME, 0, NULL, 0) < 0) _exit(124);
        execve(argv[4], argv + 4, env); _exit(126);
    }
    int status = waited();
    if (!WIFSTOPPED(status) || WSTOPSIG(status) != SIGTRAP) { printf("BAD_EXEC status=%d\n", status); return 2; }
    registers("exec", WSTOPSIG(status));
    if (ptrace(PT_CONTINUE, child, (void *)1, 0) < 0) fail("PT_CONTINUE");
    status = waited();
    if (WIFSTOPPED(status)) {
        int sig = WSTOPSIG(status);
        registers("fault", sig);
        if (kill(child, SIGKILL)) fail("kill after capture");
        status = waited();
    }
    if (!WIFEXITED(status) && !WIFSIGNALED(status)) return 2;
    printf("END exit=%d signal=%d\n", WIFEXITED(status) ? WEXITSTATUS(status) : -1, WIFSIGNALED(status) ? WTERMSIG(status) : 0);
    child = -1;
    for (size_t i = 0; i < count; i++) free(env[i]);
    return 0;
}
