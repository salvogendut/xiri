/* Native NetBSD PTY allocation/control/data baseline, run in a disposable guest. */
#include <sys/types.h>
#include <sys/stat.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <termios.h>
#include <unistd.h>

static int master = -1, slave = -1;
static void cleanup(void) {
    if (slave >= 0) close(slave);
    if (master >= 0) close(master);
}
static void fail(const char *where) { perror(where); exit(2); }
static void metadata(const char *name, int fd) {
    struct stat s;
    if (fstat(fd, &s)) fail("fstat");
    printf("%s fd=%d mode=%#o uid=%lu gid=%lu major=%u minor=%u flags=%#x\n",
        name, fd, (unsigned)s.st_mode, (unsigned long)s.st_uid,
        (unsigned long)s.st_gid, (unsigned)major(s.st_rdev),
        (unsigned)minor(s.st_rdev), fcntl(fd, F_GETFL));
}
static void transfer(int from, int to, const char *message) {
    char data[64]; size_t size = strlen(message);
    if (write(from, message, size) != (ssize_t)size) fail("write");
    ssize_t n = read(to, data, sizeof(data));
    if (n != (ssize_t)size || memcmp(data, message, size)) {
        fprintf(stderr, "transfer n=%ld expected=%zu errno=%d\n", (long)n, size, errno);
        exit(3);
    }
    printf("TRANSFER %s", message);
}
int main(void) {
    atexit(cleanup);
    for (int round = 0; round < 3; round++) {
        printf("ROUND %d uid=%lu gid=%lu\n", round,
            (unsigned long)getuid(), (unsigned long)getgid());
        master = posix_openpt(O_RDWR | O_NOCTTY | O_NONBLOCK);
        if (master < 0) fail("posix_openpt");
        metadata("MASTER", master);
        if (grantpt(master) || unlockpt(master)) fail("grant/unlock");
        char *path = ptsname(master);
        if (!path) fail("ptsname");
        printf("SLAVE_PATH %s\n", path);
        slave = open(path, O_RDWR | O_NOCTTY | O_NONBLOCK);
        if (slave < 0) fail("slave open");
        metadata("SLAVE", slave);
        struct termios t;
        if (tcgetattr(slave, &t)) fail("tcgetattr");
        cfmakeraw(&t);
        if (tcsetattr(slave, TCSANOW, &t)) fail("tcsetattr");
        transfer(master, slave, "XIRI_MASTER_TO_SLAVE\n");
        transfer(slave, master, "XIRI_SLAVE_TO_MASTER\n");
        char c; errno = 0;
        ssize_t n = read(master, &c, 1);
        printf("EMPTY n=%ld errno=%d\n", (long)n, errno);
        if (n != -1 || errno != EAGAIN) return 4;
        if (close(slave)) fail("slave close");
        slave = -1;
        if (close(master)) fail("master close");
        master = -1;
    }
    puts("NATIVE_PTY_PASS");
    return 0;
}
