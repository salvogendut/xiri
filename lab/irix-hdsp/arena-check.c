/* Verify the IRIX scratch-file operations used by Sound Editor. */
extern int trap3(int, unsigned long, unsigned long, unsigned long);

enum { IRIX_OPEN = 1005, IRIX_CLOSE = 1006, IRIX_LSEEK = 1019, IRIX_FCNTL = 1062 };
enum { F_ALLOCSP = 10, F_FREESP = 11 };

struct region {
    short type, whence;
#ifdef N32
    long long start, length;
#else
    int start, length;
#endif
    int sysid, pid, pad[4];
};

int
run(int argc, char **argv)
{
    struct region r = {0};
    if (argc != 2)
        return 1;
    /* O_RDWR | O_CREAT | O_EXCL: the pathname must be unused. */
    int fd = trap3(IRIX_OPEN, (unsigned long)argv[1], 0x502, 0600);
    if (fd < 0)
        return 2;
    r.start = 65536;
    if (trap3(IRIX_FCNTL, fd, F_ALLOCSP, (unsigned long)&r) || trap3(IRIX_LSEEK, fd, 0, 2) != 65536)
        return 3;
    r.whence = 1;
    r.start = -1024;
    if (trap3(IRIX_FCNTL, fd, F_FREESP, (unsigned long)&r) || trap3(IRIX_LSEEK, fd, 0, 2) != 64512)
        return 4;
    r.whence = 2;
    r.start = -64511;
    if (trap3(IRIX_FCNTL, fd, F_FREESP, (unsigned long)&r) || trap3(IRIX_LSEEK, fd, 0, 2) != 1)
        return 5;
    if (trap3(IRIX_CLOSE, fd, 0, 0))
        return 6;
    fd = trap3(IRIX_OPEN, (unsigned long)argv[1], 0, 0);
    if (fd < 0 || trap3(IRIX_FCNTL, fd, F_FREESP, (unsigned long)&r) != -9) /* EBADF */
        return 7;
    return 0;
}
