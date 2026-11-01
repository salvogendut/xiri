/* Independent native controls, before and after foreign mappings. */
#include <sys/types.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

#define CHECK(x) do { if (!(x)) { fprintf(stderr, "line %d errno %d\n", __LINE__, errno); return 1; } } while (0)

static int
inherit(int fd, size_t len, int flags)
{
    volatile unsigned char *p = mmap(NULL, len, PROT_READ | PROT_WRITE,
        flags, fd, 0);
    CHECK(p != MAP_FAILED && p[0] == 0 && p[len - 1] == 0);
    p[0] = 0x5a; p[len - 1] = 0xa6;
    pid_t pid = fork(); CHECK(pid >= 0);
    if (!pid) {
        if (p[0] != 0x5a || p[len - 1] != 0xa6) _exit(2);
        p[0] = 0x8b; p[len - 1] = 0xc9;
        _exit(37);
    }
    int status;
    CHECK(waitpid(pid, &status, 0) == pid && WIFEXITED(status) &&
        WEXITSTATUS(status) == 37);
    CHECK(p[0] == (flags == MAP_SHARED ? 0x8b : 0x5a));
    CHECK(p[len - 1] == (flags == MAP_SHARED ? 0xc9 : 0xa6));
    CHECK(munmap((void *)p, len) == 0);
    return 0;
}

int
main(void)
{
    size_t len = (size_t)getpagesize() * 2;
    int fd = open("/dev/zero", O_RDWR), status;
    CHECK(fd >= 0 && inherit(fd, len, MAP_SHARED) == 0 &&
        inherit(fd, len, MAP_PRIVATE) == 0);
    volatile unsigned char *p = mmap(NULL, len, PROT_READ | PROT_WRITE,
        MAP_SHARED, fd, 0);
    volatile unsigned char *q = mmap(NULL, len, PROT_READ | PROT_WRITE,
        MAP_SHARED, fd, 0);
    CHECK(p != MAP_FAILED && q != MAP_FAILED && close(fd) == 0);
    p[0] = 0x55; q[0] = 0x77;
    CHECK(p[0] == 0x55 && q[0] == 0x77);
    CHECK(munmap((void *)p, len) == 0 && munmap((void *)q, len) == 0);

    char path[] = "/tmp/xiri-native-mmap-XXXXXX";
    fd = mkstemp(path); CHECK(fd >= 0);
    CHECK(ftruncate(fd, (off_t)len) == 0);
    p = mmap(NULL, len, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    q = mmap(NULL, len, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    CHECK(p != MAP_FAILED && q != MAP_FAILED);
    p[0] = 0x5a; CHECK(q[0] == 0x5a); q[len - 1] = 0xc9;
    CHECK(p[len - 1] == 0xc9);
    CHECK(msync((void *)p, len, MS_SYNC) == 0);
    unsigned char byte;
    CHECK(pread(fd, &byte, 1, 0) == 1 && byte == 0x5a);
    CHECK(pread(fd, &byte, 1, (off_t)len - 1) == 1 && byte == 0xc9);
    CHECK(munmap((void *)p, len) == 0 && munmap((void *)q, len) == 0);
    int ro = open(path, O_RDONLY); CHECK(ro >= 0);
    CHECK(mmap(NULL, len, PROT_WRITE, MAP_SHARED, ro, 0) == MAP_FAILED &&
        errno == EACCES);
    CHECK(close(ro) == 0 && ftruncate(fd, 17) == 0);
    p = mmap(NULL, len, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    CHECK(p != MAP_FAILED);
    pid_t pid = fork(); CHECK(pid >= 0);
    if (!pid) { p[len / 2] = 0x73; _exit(37); }
    CHECK(waitpid(pid, &status, 0) == pid && WIFSIGNALED(status) &&
        WTERMSIG(status) == SIGBUS);
    CHECK(lseek(fd, 0, SEEK_END) == 17);
    CHECK(munmap((void *)p, len) == 0 && close(fd) == 0 && unlink(path) == 0);
    printf("NATIVE_MMAP uid=%u zero=1 shared=1 private=1 close=1 file=1 eof=1\n",
        (unsigned)getuid());
    return 0;
}
