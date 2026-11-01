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
/* BREAK 514 preserves EPC in NetBSD's MIPS debugger trap path. */
#define BREAKPOINT 0x0202000d
static uint32_t instruction(uint32_t address) {
    uint32_t word;
    struct ptrace_io_desc io={PIOD_READ_I,(void *)(uintptr_t)address,&word,4};
    if(ptrace(PT_IO,child,&io,sizeof(io))<0 || io.piod_len!=4) fail("read instruction");
    return word;
}
static void patch(uint32_t address,uint32_t word) {
    struct ptrace_io_desc io={PIOD_WRITE_I,(void *)(uintptr_t)address,&word,4};
    if(ptrace(PT_IO,child,&io,sizeof(io))<0 || io.piod_len!=4) fail("write instruction");
    if(instruction(address)!=word) {errno=EINVAL;fail("verify instruction");}
}
static int lookups(void) {
    struct stub {const char *name;uint32_t pc,number;int post;} stubs[]={
        {"mmap",0x0fa51da0,1134,0}};
    for(size_t i=0;i<1;i++) {
        if(instruction(stubs[i].pc)!=0x0000000c || instruction(stubs[i].pc+4)!=0x14e00003) {
            errno=EINVAL;fail("pinned syscall stub");
        }
        patch(stubs[i].pc,BREAKPOINT);
    }
    for(unsigned stop=0;stop<1024;stop++) {
        fflush(stdout);
        if(ptrace(PT_CONTINUE,child,(void *)1,0)<0) fail("continue lookup");
        int status=waited();
        if(!WIFSTOPPED(status) || WSTOPSIG(status)!=SIGTRAP) return status;
        struct {uint64_t regs[38];unsigned char guard[64];} c;
        memset(&c,0xa5,sizeof(c));
        if(ptrace(PT_GETREGS,child,c.regs,0)<0) fail("lookup registers");
        for(size_t i=0;i<sizeof(c.guard);i++) if(c.guard[i]!=0xa5) {errno=EOVERFLOW;fail("lookup guard");}
        struct stub *s=NULL;
        for(size_t i=0;i<1;i++) if(c.regs[37]==stubs[i].pc+(stubs[i].post?4:0))s=&stubs[i];
        if(!s) {errno=EINVAL;fail("unexpected lookup breakpoint");}
        if(!s->post) {
            if(c.regs[2]!=s->number){errno=EINVAL;fail("lookup syscall number");}
            printf("LOOKUP name=%s a0=%016" PRIx64 " a1=%016" PRIx64 " a2=%016" PRIx64 " a3=%016" PRIx64 " a4=%016" PRIx64 " a5=%016" PRIx64 " ra=%016" PRIx64 "\n",s->name,c.regs[4],c.regs[5],c.regs[6],c.regs[7],c.regs[8],c.regs[9],c.regs[31]);
            if(s->number==1033) {
                /* Bound to the remainder of the page, avoiding an unrelated
                 * inaccessible next page while reading a short pathname. */
                size_t n=8192-(c.regs[4]&8191);if(n>512)n=512;
                memory("access-path",c.regs[4],n);
            }
            patch(s->pc,0x0000000c);patch(s->pc+4,BREAKPOINT);s->post=1;
        } else {
            printf("LOOKUP_RETURN name=%s v0=%016" PRIx64 " a3=%016" PRIx64 "\n",s->name,c.regs[2],c.regs[7]);
            patch(s->pc+4,0x14e00003);patch(s->pc,BREAKPOINT);s->post=0;
        }
    }
    errno=EOVERFLOW;fail("lookup stop bound");return 0;
}
int main(int argc, char **argv) {
    int trace_lookups=argc>1 && !strcmp(argv[1],"--lookups");
    if(trace_lookups){argc--;argv++;}
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
        /* Attach while parent and child still have matching credentials.
         * PT_TRACE_ME after a uid change is rejected by NetBSD. */
        if (ptrace(PT_TRACE_ME, 0, NULL, 0) < 0) { perror("PT_TRACE_ME"); _exit(124); }
        if (setgroups(0, NULL) || setgid((gid_t)gid) || setuid((uid_t)uid)) _exit(125);
        execve(argv[4], argv + 4, env); _exit(126);
    }
    int status = waited();
    if (!WIFSTOPPED(status) || WSTOPSIG(status) != SIGTRAP) { printf("BAD_EXEC status=%d\n", status); return 2; }
    registers("exec", WSTOPSIG(status));
    if(trace_lookups) status=lookups();
    else {
        if (ptrace(PT_CONTINUE, child, (void *)1, 0) < 0) fail("PT_CONTINUE");
        status = waited();
    }
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
