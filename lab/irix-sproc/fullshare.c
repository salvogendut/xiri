/* Run as an ordinary user in a writable directory containing child/. */
typedef unsigned int word;
struct reply { word value, second, error; };
extern void probe_call(word, const word *, struct reply *);
extern void spawn_call(word, const word *, struct reply *);
extern void child_entry(void);
word entry_regs[12];
static word fd, parent, status[32];
static volatile word shared, released;
#define PRDA_PID (*(volatile word *)0x200e00)

static struct reply
call(word nr, word a, word b, word c, word d)
{
    word args[6] = { a, b, c, d, 0, 0 };
    struct reply r;
    probe_call(nr, args, &r);
    return r;
}

int
child_main(void *arg)
{
    struct reply r;
    word map[6] = { 0, 32768, 3, 0x102, fd, 0 };
    if (arg == (void *)&parent)
        return call(1130, 13, parent, 0, 0).value == 0x43 ? 0 : 19;
    if (arg != (void *)&shared || PRDA_PID != call(1020, 0, 0, 0, 0).value)
        return 11;
    if (call(1130, 13, parent, 0, 0).value != 0x7f)
        return 12;
    if (call(1012, (word)"child", 0, 0, 0).error || call(1060, 0077, 0, 0, 0).error)
        return 13;
    probe_call(1134, map, &r);
    if (r.error)
        return 14;
    map[0] = r.value;
    if (!call(1135, map[0], 8192, 0, 0).error || !call(1135, 0x200000, 8192, 0, 0).error)
        return 15;
    if (call(1135, map[0], map[1], 0, 0).error)
        return 16;
    released = map[0];
    if (call(1006, fd, 0, 0, 0).error)
        return 18;
    shared = 1;
    return 0;
}

int
main(void)
{
    struct reply r = call(1005, (word)"/dev/zero", 2, 0, 0);
    if (r.error)
        return 1;
    fd = r.value;
    parent = call(1020, 0, 0, 0, 0).value;
    word args[6] = { (word)child_entry, 0x7f, (word)&shared, 0, 0, 0 };
    spawn_call(1129, args, &r);
    if (r.error)
        return 2;
    if (call(1170, 0, r.value, (word)status, 1).error)
        return 3;
    if (status[5] || !shared || PRDA_PID != parent)
        return status[5] ? status[5] : 4;
    r = call(1006, fd, 0, 0, 0);
    if (!r.error || r.value != 9) /* EBADF after the child's close. */
        return 5;
    /* The caller checks child/result exists and has mode 0600. */
    r = call(1008, (word)"result", 0666, 0, 0);
    if (r.error)
        return 6;
    r = call(1004, r.value, released, 1, 0);
    if (!r.error || r.value != 14) /* EFAULT in the parent too. */
        return 7;
    /* Form a new pair with the historical address/FD-only mask. */
    args[1] = 0x02000042;
    args[2] = (word)&parent;
    spawn_call(1129, args, &r);
    if (r.error || call(1170, 0, r.value, (word)status, 1).error || status[5])
        return 8;
    return call(1130, 13, 0, 0, 0).value == 0x43 ? 0 : 9;
}
