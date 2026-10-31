/* Original test program for the supplied IRIX development tools and libc. */
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/ioctl.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <termios.h>
#include <unistd.h>

extern char *_getpty(int *, int, mode_t, int);
static int master = -1, slave = -1;
static void cleanup(void) {
    if (slave >= 0) close(slave);
    if (master >= 0) close(master);
}
static void metadata(const char *name, int fd) {
    struct stat st;
    int rc; errno = 0; rc = fstat(fd, &st);
    printf("STAT %s rc=%d errno=%d", name, rc, errno);
    if (!rc) printf(" mode=%#o uid=%lu gid=%lu rdev=%#lx", (unsigned)st.st_mode,
        (unsigned long)st.st_uid, (unsigned long)st.st_gid, (unsigned long)st.st_rdev);
    putchar('\n');
}
static void flags(int fd) {
    int rc; errno = 0; rc = fcntl(fd, F_GETFL);
    printf("FLAGS value=%#x errno=%d\n", rc, errno);
}
int main(int argc, char **argv) {
    int requested, rc, i; char *path; struct termios term;
    if (argc != 3) return 2;
    atexit(cleanup);
    requested = atoi(argv[2]);
    printf("IDENTITY uid=%lu euid=%lu gid=%lu egid=%lu abi=%d\n",
        (unsigned long)getuid(), (unsigned long)geteuid(),
        (unsigned long)getgid(), (unsigned long)getegid(), _MIPS_SIM);
    if (!strcmp(argv[1], "getpty")) {
        errno = 0; path = _getpty(&master, requested, 0600, 0);
        printf("GETPTY success=%d errno=%d path=%s\n", path != NULL, errno, path ? path : "-");
        if (!path) return 10;
        metadata("master", master); flags(master);
        errno = 0; slave = open(path, O_RDWR | O_NONBLOCK | O_NOCTTY);
        printf("SLAVE_OPEN success=%d errno=%d\n", slave >= 0, errno);
        if (slave < 0) return 11;
        metadata("slave", slave);
        memset(&term, 0xa5, sizeof(term)); errno = 0; rc = tcgetattr(slave, &term);
        printf("TERM rc=%d errno=%d size=%lu hex=", rc, errno, (unsigned long)sizeof(term));
        for (i = 0; i < sizeof(term); i++) printf("%02x", ((unsigned char *)&term)[i]);
        putchar('\n');
        return rc ? 12 : 0;
    }
    errno = 0; master = open(argv[1], requested, 0600);
    printf("OPEN success=%d errno=%d\n", master >= 0, errno);
    if (master < 0) return 0;
    metadata("open", master); flags(master);
    for (i = 0; i < 4; i++) {
        int modes[4] = {4, 128, 132, 0};
        errno = 0; rc = fcntl(master, F_SETFL, modes[i]);
        printf("SETFL arg=%#x rc=%d errno=%d\n", modes[i], rc, errno);
        flags(master);
    }
    return 0;
}
