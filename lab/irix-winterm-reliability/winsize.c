/* Original observation program, built with the supplied IRIX headers/libc. */
#include <sys/types.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <termios.h>
#include <unistd.h>

extern char *_getpty(int *, int, mode_t, int);
static struct {
    unsigned before;
    struct winsize size;
    unsigned after;
} guard;

static void observe(const char *name, int fd, int command, void *data)
{
    int rc, error;
    errno = 0;
    rc = ioctl(fd, command, data);
    error = errno;
    printf("CASE %s command=%#x rc=%d errno=%d guard=%08x,%08x size=%u,%u,%u,%u\n",
        name, command, rc, error, guard.before, guard.after,
        guard.size.ws_row, guard.size.ws_col,
        guard.size.ws_xpixel, guard.size.ws_ypixel);
}

int main(int argc, char **argv)
{
    int master = -1, slave, regular, nullfd, zerofd;
    char *path;
    unsigned char unaligned[12];
    unsigned char *pages;
    long page_size = sysconf(_SC_PAGESIZE);
    if (argc == 2 && !strcmp(argv[1], "user") &&
        (setgid(1234) || setuid(1234))) return 2;
    printf("IDENTITY uid=%lu gid=%lu abi=%d bytes=%lu get=%#x set=%#x\n",
        (unsigned long)getuid(), (unsigned long)getgid(), _MIPS_SIM,
        (unsigned long)sizeof(struct winsize), TIOCGWINSZ, TIOCSWINSZ);
    if (sizeof(struct winsize) != 8) return 3;
    path = _getpty(&master, O_RDWR, 0600, 0);
    if (!path || (slave = open(path, O_RDWR | O_NOCTTY)) < 0) return 4;
    regular = open("regular", O_RDONLY);
    nullfd = open("/dev/null", O_RDWR);
    if (regular < 0 || nullfd < 0) return 5;
    guard.before = 0x11223344;
    guard.after = 0x55667788;
    memset(&guard.size, 0xa5, sizeof(guard.size));
    observe("initial-master", master, TIOCGWINSZ, &guard.size);
    observe("initial-slave", slave, TIOCGWINSZ, &guard.size);
    guard.size.ws_row = 31; guard.size.ws_col = 97;
    guard.size.ws_xpixel = 776; guard.size.ws_ypixel = 465;
    observe("set-master", master, TIOCSWINSZ, &guard.size);
    memset(&guard.size, 0xa5, sizeof(guard.size));
    observe("get-slave", slave, TIOCGWINSZ, &guard.size);
    guard.size.ws_row = 40; guard.size.ws_col = 120;
    guard.size.ws_xpixel = 960; guard.size.ws_ypixel = 600;
    observe("set-slave", slave, TIOCSWINSZ, &guard.size);
    observe("get-master", master, TIOCGWINSZ, &guard.size);
    memset(&guard.size, 0, sizeof(guard.size));
    observe("set-zero", master, TIOCSWINSZ, &guard.size);
    observe("get-zero", slave, TIOCGWINSZ, &guard.size);
    memset(&guard.size, 0xff, sizeof(guard.size));
    observe("set-max", master, TIOCSWINSZ, &guard.size);
    observe("get-max", slave, TIOCGWINSZ, &guard.size);
    observe("get-bad-fd", -1, TIOCGWINSZ, &guard.size);
    observe("set-bad-fd", -1, TIOCSWINSZ, &guard.size);
    observe("get-bad-fd-null", -1, TIOCGWINSZ, NULL);
    observe("set-bad-fd-null", -1, TIOCSWINSZ, NULL);
    observe("get-file", regular, TIOCGWINSZ, &guard.size);
    observe("set-file", regular, TIOCSWINSZ, &guard.size);
    observe("get-null-device", nullfd, TIOCGWINSZ, &guard.size);
    observe("set-null-device", nullfd, TIOCSWINSZ, &guard.size);
    observe("get-null-pointer", master, TIOCGWINSZ, NULL);
    observe("set-null-pointer", master, TIOCSWINSZ, NULL);
    memset(unaligned, 0xa5, sizeof(unaligned));
    memcpy(unaligned + 1, &guard.size, 8);
    observe("set-unaligned", master, TIOCSWINSZ, unaligned + 1);
    observe("get-unaligned", master, TIOCGWINSZ, unaligned + 1);
    printf("UNALIGNED ");
    { unsigned i; for (i = 0; i < sizeof(unaligned); i++) printf("%02x", unaligned[i]); }
    putchar('\n');
    zerofd = open("/dev/zero", O_RDWR);
    if (zerofd < 0) return 6;
    pages = mmap(NULL, page_size * 2, PROT_READ | PROT_WRITE,
        MAP_PRIVATE, zerofd, 0);
    close(zerofd);
    if (pages == MAP_FAILED || mprotect(pages + page_size, page_size, PROT_NONE)) return 6;
    memset(pages + page_size - 8, 0xa5, 8);
    observe("get-cross-page", master, TIOCGWINSZ, pages + page_size - 4);
    printf("CROSS ");
    { unsigned i; for (i = 0; i < 8; i++) printf("%02x", pages[page_size - 8 + i]); }
    putchar('\n');
    observe("set-cross-page", master, TIOCSWINSZ, pages + page_size - 4);
    observe("after-failed-set", master, TIOCGWINSZ, &guard.size);
    if (mprotect(pages, page_size, PROT_READ)) return 7;
    observe("get-readonly", master, TIOCGWINSZ, pages);
    observe("set-readonly", master, TIOCSWINSZ, pages);
    observe("after-readonly-set", master, TIOCGWINSZ, &guard.size);
    close(nullfd); close(regular); close(slave); close(master);
    return 0;
}
