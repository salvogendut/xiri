/* Native NetBSD tracer for the pinned LP64 MIPS guest; raw output is private.
 * Observe the two loaded IRIX syscall stubs without changing guest kernel code.
 */
#include <sys/types.h>
#include <sys/ptrace.h>
#include <sys/wait.h>
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

/* NetBSD MIPS debugger BREAK code 514 preserves EPC; BREAK 0 advances it. */
#define BREAKPOINT 0x0202000d
static pid_t child = -1;
static void cleanup(void) {
    if (child > 0) {
        (void)kill(child, SIGKILL);
        while (waitpid(child, NULL, 0) < 0 && errno == EINTR) {}
    }
}
static void fail(const char *what) { perror(what); exit(2); }
static void require(int condition, const char *what) {
    if (!condition) { errno = EINVAL; fail(what); }
}
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
static int transfer(int op, uint32_t address, void *data, size_t size) {
    struct ptrace_io_desc io = {op, (void *)(uintptr_t)address, data, size};
    if (ptrace(PT_IO, child, &io, sizeof(io)) < 0) return -1;
    if (io.piod_len != size) { errno = EIO; return -1; }
    return 0;
}
static uint32_t instruction(uint32_t address) {
    uint32_t word;
    if (transfer(PIOD_READ_I, address, &word, sizeof(word))) fail("read instruction");
    return word;
}
static void write_instruction(uint32_t address, uint32_t word) {
    if (transfer(PIOD_WRITE_I, address, &word, sizeof(word))) fail("write instruction");
    require(instruction(address) == word, "verify instruction");
}
static void registers(uint64_t regs[38]) {
    /* MIPS has no process_reg32/read_regs32 overrides: netbsd32 ptrace copies
     * 38 kernel register_t slots. PC is slot 37; guard catches size changes. */
    struct { uint64_t regs[38]; unsigned char guard[64]; } capture;
    memset(&capture, 0xa5, sizeof(capture));
    if (ptrace(PT_GETREGS, child, capture.regs, 0) < 0) fail("PT_GETREGS");
    for (size_t i = 0; i < sizeof(capture.guard); i++)
        require(capture.guard[i] == 0xa5, "register guard");
    memcpy(regs, capture.regs, sizeof(capture.regs));
}
static void memory(const char *label, uint32_t address, size_t size) {
    unsigned char data[128];
    require(size <= sizeof(data), "memory bound");
    int rc = transfer(PIOD_READ_D, address, data, size);
    printf("MEM %s address=%08" PRIx32 " error=%d bytes=%zu hex=",
        label, address, rc ? errno : 0, rc ? 0 : size);
    if (!rc) for (size_t i = 0; i < size; i++) printf("%02x", data[i]);
    putchar('\n');
}
static void headers(uint32_t address, int probe) {
    uint32_t ph[2][8];
    if (transfer(PIOD_READ_D, address, ph, sizeof(ph))) fail("read headers");
    for (size_t i = 0; i < 2; i++) {
        printf("PHDR index=%zu type=%" PRIu32 " offset=%08" PRIx32
            " vaddr=%08" PRIx32 " paddr=%08" PRIx32 " filesz=%08" PRIx32
            " memsz=%08" PRIx32 " flags=%" PRIu32 " align=%08" PRIx32 "\n",
            i, ph[i][0], ph[i][1], ph[i][2], ph[i][3], ph[i][4], ph[i][5], ph[i][6], ph[i][7]);
        if (probe) memory(i ? "requested-rw-before" : "requested-rx-before", ph[i][2], 128);
    }
}
static void resume(void) {
    fflush(stdout);
    if (ptrace(PT_CONTINUE, child, (void *)1, 0) < 0) fail("PT_CONTINUE");
}
struct stub { const char *name; uint32_t pc; int armed, post; uint64_t request; uint32_t ph; };
int main(int argc, char **argv) {
    if (argc < 3 || (strcmp(argv[1], "native") && strcmp(argv[1], "vendor"))) return 2;
    int native = !strcmp(argv[1], "native");
    char *env[] = {"HOME=/tmp/xiri-home", NULL};
    if (atexit(cleanup)) return 2;
    child = fork(); if (child < 0) fail("fork");
    if (!child) {
        int fd = open("/dev/null", O_RDONLY); if (fd < 0 || dup2(fd, 0) < 0) _exit(125); close(fd);
        fd = open("elfmap-child.out", O_WRONLY|O_CREAT|O_TRUNC, 0600); if (fd < 0 || dup2(fd, 1) < 0) _exit(125); close(fd);
        fd = open("elfmap-child.err", O_WRONLY|O_CREAT|O_TRUNC, 0600); if (fd < 0 || dup2(fd, 2) < 0) _exit(125); close(fd);
        if (ptrace(PT_TRACE_ME, 0, NULL, 0) < 0) _exit(124);
        execve(argv[2], argv + 2, env); _exit(126);
    }
    int status = waited();
    require(WIFSTOPPED(status) && WSTOPSIG(status) == SIGTRAP, "exec stop");
    uint64_t regs[38]; registers(regs);
    printf("EXEC pc=%016" PRIx64 " guard=intact\n", regs[37]);
    if (native) {
        require(regs[37] == 0x00400090, "native entry PC");
        uint32_t original = instruction((uint32_t)regs[37]);
        write_instruction((uint32_t)regs[37], BREAKPOINT);
        resume(); status = waited();
        require(WIFSTOPPED(status) && WSTOPSIG(status) == SIGTRAP, "native breakpoint");
        registers(regs); require(regs[37] == 0x00400090, "native breakpoint PC");
        write_instruction((uint32_t)regs[37], original);
        printf("NATIVE breakpoint=00400090 restored=yes guard=intact\n");
        resume(); status = waited();
    } else {
        struct stub stubs[] = {{"libc", 0x0fa4f9b8, 1, 0, 0, 0}, {"rld", 0x0fb7d28c, 0, 0, 0, 0}};
        require(instruction(stubs[0].pc) == 0x0000000c && instruction(stubs[0].pc + 4) == 0x14e00003, "libc stub words");
        write_instruction(stubs[0].pc, BREAKPOINT);
        for (unsigned stop = 0; stop < 100; stop++) {
            resume(); status = waited();
            if (WIFEXITED(status) || WIFSIGNALED(status)) break;
            require(WIFSTOPPED(status) && WSTOPSIG(status) == SIGTRAP, "unexpected signal");
            registers(regs);
            struct stub *s = NULL;
            for (size_t i = 0; i < 2; i++)
                if (stubs[i].armed && regs[37] == stubs[i].pc + (stubs[i].post ? 4 : 0)) s = &stubs[i];
            require(s != NULL, "unexpected breakpoint PC");
            if (!s->post) {
                require(regs[2] == 1040, "syssgi syscall number");
                s->request = regs[4]; s->ph = (uint32_t)regs[6];
                printf("CALL stub=%s request=%" PRIu64 " fd=%" PRIu64 " phdr=%08" PRIx32 " count=%" PRIu64 "\n",
                    s->name, s->request, regs[5], s->ph, regs[7]);
                if (s->request == 68) { require(regs[7] == 2, "header count"); headers(s->ph, 1); }
                write_instruction(s->pc, 0x0000000c);
                write_instruction(s->pc + 4, BREAKPOINT); s->post = 1;
            } else {
                printf("RETURN stub=%s request=%" PRIu64 " v0=%016" PRIx64 " a3=%016" PRIx64 "\n", s->name, s->request, regs[2], regs[7]);
                if (s->request == 68) headers(s->ph, 0);
                write_instruction(s->pc + 4, 0x14e00003);
                write_instruction(s->pc, BREAKPOINT); s->post = 0;
                if (s == &stubs[0] && s->request == 68 && regs[7] == 0 && !stubs[1].armed) {
                    require(instruction(stubs[1].pc) == 0x0000000c && instruction(stubs[1].pc + 4) == 0x14e00003, "rld stub words");
                    write_instruction(stubs[1].pc, BREAKPOINT); stubs[1].armed = 1;
                    printf("RLD breakpoint=0fb7d28c armed=yes\n");
                }
            }
        }
    }
    require(WIFEXITED(status) || WIFSIGNALED(status), "stop bound exhausted");
    printf("END exit=%d signal=%d\n", WIFEXITED(status) ? WEXITSTATUS(status) : -1, WIFSIGNALED(status) ? WTERMSIG(status) : 0);
    child = -1;
    return 0;
}
