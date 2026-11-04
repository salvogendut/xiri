/* A bounded native allocation for process/shutdown tests under memory pressure. */
#include <sys/mman.h>
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    if (argc != 2) return 2;
    char *end;
    errno = 0;
    unsigned long mib = strtoul(argv[1], &end, 10);
    if (errno || !*argv[1] || *end || !mib || mib > 192) return 2;
    sigset_t signals;
    sigemptyset(&signals);
    sigaddset(&signals, SIGTERM);
    sigaddset(&signals, SIGINT);
    if (sigprocmask(SIG_BLOCK, &signals, NULL)) return 2;
    /* A failed controller cannot leave this fixture alive indefinitely. */
    alarm(1800);
    size_t bytes = (size_t)mib * 1024 * 1024;
    unsigned char *memory = mmap(NULL, bytes, PROT_READ | PROT_WRITE,
        MAP_PRIVATE | MAP_ANON, -1, 0);
    if (memory == MAP_FAILED) { perror("mmap"); return 3; }
    volatile unsigned char *pages = memory;
    unsigned long checksum = 0;
    for (size_t i = 0; i < bytes; i += 4096) {
        pages[i] = (unsigned char)(1 + (i / 4096) % 255);
        checksum += pages[i];
    }
    printf("MEMORY_READY pid=%d bytes=%zu checksum=%lu\n", getpid(), bytes, checksum);
    fflush(stdout);
    int signum;
    if (sigwait(&signals, &signum)) return 4;
    if (munmap(memory, bytes)) return 5;
    printf("MEMORY_RELEASED signal=%d\n", signum);
    return 0;
}
