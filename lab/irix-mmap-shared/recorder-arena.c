/* Emit SGI n32 syscall results for Media Recorder's 5,232-byte scratch file. */
typedef unsigned int word;
struct reply { word value, second, error; };
extern void probe_call(word, const word *, struct reply *);

enum {
    WRITE = 1004, OPEN = 1005, SEEK = 1019, MMAP = 1134, SIGPROCMASK = 1164
};

static word
invoke(word number, word a, word b, word c, word d, word e, word f)
{
    word args[6] = { a, b, c, d, e, f };
    struct reply r;

    probe_call(number, args, &r);
    return r.error ? -r.value : r.value;
}

/* Output nine big-endian words, with syscall errors as negative numbers. */
static word record[9] = { 0x4d524543 };

int
main(int argc, char **argv)
{
    word fd, base, stack[4];

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
    return invoke(WRITE, 1, (word)record, sizeof(record), 0, 0, 0) != sizeof(record);
}
