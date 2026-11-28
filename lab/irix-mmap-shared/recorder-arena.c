/* Emit SGI n32 syscall results for Media Recorder's 5,232-byte scratch file. */
typedef unsigned int word;
struct reply { word value, second, error; };
extern void probe_call(word, const word *, struct reply *);

enum {
    FORK = 1002, WRITE = 1004, OPEN = 1005, SEEK = 1019, IOCTL = 1054,
    POLL = 1087, MMAP = 1134, MSYNC = 1137, FCHMOD = 1153,
    SIGPROCMASK = 1164, WAITSYS = 1170
};

static word
invoke(word number, word a, word b, word c, word d, word e, word f)
{
    word args[6] = { a, b, c, d, e, f };
    struct reply r;

    probe_call(number, args, &r);
    return r.error ? -r.value : r.value;
}

/* Keep the first nine words comparable with the original IRIX measurements. */
static word record[16] = { 0x4d524543 };

static int
readable(word fd, int timeout)
{
    struct { int fd; short events, revents; } p = { fd, 1, 0 };
    int n = (int)invoke(POLL, (word)&p, 1, timeout, 0, 0, 0);

    return n == 1 && p.revents == 1 ? 1 : n == 0 && p.revents == 0 ? 0 : -1;
}

/* Return the failing step. A forked child must be able to wake just the
 * waiting parent through their shared descriptor. Readiness is level-triggered. */
static int
check_semaphore(void)
{
    enum { BLOCK = 0x75730c, UNBLOCK = 0x75730d, IDADDR = 0x75730e, COUNT = 0x757310 };
    word fd, owner = -1U, id[2] = { 0, (word)&owner }, info[32], args[6] = { 0 };
    struct reply child, count;

    fd = invoke(OPEN, (word)"/dev/usemaclone", 2, 0, 0, 0, 0);
    if ((int)fd < 0 || invoke(FCHMOD, fd, 0600, 0, 0, 0, 0))
        return 10;
    if (invoke(IOCTL, fd, IDADDR, (word)id, 0, 0, 0) || readable(fd, 0) != 0)
        return 11;
    if (invoke(IOCTL, fd, BLOCK, 0, 0, 0, 0) || readable(fd, 0) != 0)
        return 12;
    args[0] = fd;
    args[1] = COUNT;
    probe_call(IOCTL, args, &count);
    if (count.error || (int)count.value != -1 ||
        (int)invoke(IOCTL, fd, BLOCK, 0, 0, 0, 0) != -34)
        return 13;
    args[0] = args[1] = 0;
    probe_call(FORK, args, &child);
    if (child.error)
        return 14;
    if (child.second) {
        if (readable(fd, 0) != 0 || invoke(IOCTL, fd, UNBLOCK, 0, 0, 0, 0))
            return 15;
        return readable(fd, 0) != 0 ? 16 : 0;
    }
    if (readable(fd, 5000) != 1 || readable(fd, 0) != 1)
        return 17;
    if (invoke(WAITSYS, 0, child.value, (word)info, 1, 0, 0) ||
        info[1] != 1 || info[5] != 0)
        return 18;
    if (invoke(IOCTL, fd, COUNT, 0, 0, 0, 0))
        return 19;
    for (word i = 1; i <= 2; i++)
        if ((int)invoke(IOCTL, fd, UNBLOCK, 0, 0, 0, 0) != -11 ||
            invoke(IOCTL, fd, COUNT, 0, 0, 0, 0) != i)
            return 19;
    for (word i = 2; i > 0; i--)
        if ((int)invoke(IOCTL, fd, BLOCK, 0, 0, 0, 0) != -11 ||
            invoke(IOCTL, fd, COUNT, 0, 0, 0, 0) != i - 1)
            return 19;
    if (invoke(IOCTL, fd, BLOCK, 0, 0, 0, 0) || readable(fd, 0) != 0)
        return 20;
    return 0;
}

int
main(int argc, char **argv)
{
    word fd, base, ordinary, stack[4];

    if (argc == 1)
        return check_semaphore();
    if (argc != 2)
        return 1;
    fd = invoke(OPEN, (word)argv[1], 2, 0, 0, 0, 0);
    if ((int)fd < 0)
        return 2;
    base = invoke(MMAP, 0, 66672, 3, 0x41, fd, 0);  /* shared + AUTOGROW */
    if ((int)base < 0)
        return 3;

    record[1] = invoke(SIGPROCMASK, 0, 0, (word)stack, 0, 0, 0);
    record[2] = invoke(SIGPROCMASK, 0, 0, base + 64, 0, 0, 0);
    record[3] = invoke(SEEK, fd, 0, 2, 0, 0, 0);
    record[4] = invoke(SIGPROCMASK, 0, 0, base + 0x2540, 0, 0, 0);
    record[5] = invoke(SEEK, fd, 0, 2, 0, 0, 0);

    /* Repeat at the identical address after an ordinary user-mode store. */
    *(volatile char *)(base + 0x2540) = 0;
    record[6] = invoke(SIGPROCMASK, 0, 0, base + 0x2540, 0, 0, 0);
    record[7] = invoke(SEEK, fd, 0, 2, 0, 0, 0);
    record[8] = invoke(OPEN, (word)"/dev/usemaclone", 2, 0, 0, 0, 0);
    record[9] = invoke(MSYNC, base, 1136, 2, 0, 0, 0); /* MS_INVALIDATE */
    record[10] = invoke(MSYNC, base, 1136, 8, 0, 0, 0); /* unknown flag */
    /* The 16-byte result straddles two untouched pages at either page size. */
    record[11] = invoke(SIGPROCMASK, 0, 0, base + 24576 - 8, 0, 0, 0);
    record[12] = invoke(SEEK, fd, 0, 2, 0, 0, 0);
    ordinary = invoke(MMAP, 0, 66672, 3, 1, fd, 0); /* shared, no AUTOGROW */
    if ((int)ordinary < 0)
        return 4;
    record[13] = invoke(SIGPROCMASK, 0, 0, ordinary + 62528, 0, 0, 0);
    record[14] = invoke(SEEK, fd, 0, 2, 0, 0, 0);
    record[15] = invoke(SIGPROCMASK, 0, 0, 1, 0, 0, 0);
    return invoke(WRITE, 1, (word)record, sizeof(record), 0, 0, 0) != sizeof(record);
}
