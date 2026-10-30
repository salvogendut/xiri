/* Compiled by the installed o32 userland to exercise COMPAT_NETBSD32. */
#include <sys/types.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#define CHECK(x) do { if (!(x)) { fprintf(stderr, "line %d: %s errno=%d\n", __LINE__, #x, errno); return 99; } } while (0)
static volatile sig_atomic_t caught;
static uintptr_t alt_low, alt_high;

static void
handler(int signo)
{
    volatile char byte;
    uintptr_t here = (uintptr_t)&byte;
    caught = signo == SIGUSR1 && here >= alt_low && here < alt_high;
}

int
main(void)
{
    char path[] = "/tmp/xiri-native64-XXXXXX", byte;
    int fd, status, pipes[2];
    struct stat st;
    struct timespec now;
    CHECK(sizeof(void *) == 4 && sizeof(long) == 4 && sizeof(off_t) == 8);
    long page = sysconf(_SC_PAGESIZE);
    CHECK(page == 8192);
    CHECK(clock_gettime(CLOCK_MONOTONIC, &now) == 0 && now.tv_nsec >= 0 && now.tv_nsec < 1000000000L);
    CHECK((fd = mkstemp(path)) >= 0);
    CHECK(unlink(path) == 0);
    CHECK(write(fd, "ABC", 3) == 3 && fsync(fd) == 0);
    CHECK(lseek(fd, INT64_C(0x100001234), SEEK_SET) == INT64_C(0x100001234));
    CHECK(read(fd, &byte, 1) == 0);
    CHECK(fstat(fd, &st) == 0 && st.st_size == 3);
    CHECK(pwrite(fd, "Z", 1, 4096) == 1);
    CHECK(pread(fd, &byte, 1, 4095) == 1 && byte == 0);
    CHECK(pread(fd, &byte, 1, 4096) == 1 && byte == 'Z');
    CHECK(ftruncate(fd, 3) == 0 && close(fd) == 0);

    CHECK((fd = open("map-input.bin", O_RDONLY)) >= 0);
    unsigned char *map = mmap(NULL, (size_t)page, PROT_READ | PROT_WRITE, MAP_PRIVATE, fd, page);
    CHECK(map != MAP_FAILED && map[0] == 0x22);
    map[0] = 0x44;
    CHECK(mprotect(map, (size_t)page, PROT_READ) == 0);
    pid_t child = fork();
    CHECK(child >= 0);
    if (child == 0) { map[0] = 0; _exit(98); }
    CHECK(waitpid(child, &status, 0) == child && WIFSIGNALED(status) && WTERMSIG(status) == SIGSEGV);
    CHECK(munmap(map, (size_t)page) == 0);
    CHECK(pread(fd, &byte, 1, page) == 1 && byte == 0x22 && close(fd) == 0);

    stack_t stack = {0};
    stack.ss_size = 65536;
    CHECK((stack.ss_sp = malloc(stack.ss_size)) != NULL);
    alt_low = (uintptr_t)stack.ss_sp;
    alt_high = alt_low + stack.ss_size;
    CHECK(sigaltstack(&stack, NULL) == 0);
    struct sigaction action;
    memset(&action, 0, sizeof(action));
    action.sa_handler = handler;
    action.sa_flags = SA_ONSTACK;
    CHECK(sigemptyset(&action.sa_mask) == 0 && sigaction(SIGUSR1, &action, NULL) == 0);
    volatile double value = 1.5;
    CHECK(raise(SIGUSR1) == 0 && caught);
    value *= 2.0;
    CHECK(value == 3.0);
    stack.ss_flags = SS_DISABLE;
    CHECK(sigaltstack(&stack, NULL) == 0);
    free(stack.ss_sp);

    CHECK(pipe(pipes) == 0);
    CHECK((child = fork()) >= 0);
    if (child == 0) {
        close(pipes[0]);
        if (write(pipes[1], "P", 1) != 1) _exit(98);
        close(pipes[1]);
        execl("/bin/sh", "sh", "-c", "exit 23", (char *)NULL);
        _exit(97);
    }
    CHECK(close(pipes[1]) == 0);
    struct pollfd pollfd = {pipes[0], POLLIN, 0};
    CHECK(poll(&pollfd, 1, 2000) == 1 && (pollfd.revents & POLLIN));
    CHECK(read(pipes[0], &byte, 1) == 1 && byte == 'P' && close(pipes[0]) == 0);
    CHECK(waitpid(child, &status, 0) == child && WIFEXITED(status) && WEXITSTATUS(status) == 23);
    puts("XIRI_O32_COMPAT_OK");
    return 0;
}
