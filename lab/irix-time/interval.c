/* Exercise the IRIX o32 and n32 interval-timer wire format on both kernels. */
typedef unsigned int word;
struct reply { word value, second, error; };
struct timer { int interval_sec, interval_usec, value_sec, value_usec; };
extern void probe_call(word, const word *, struct reply *);

static int
trap(word number, word a, word b, word c)
{
    word args[6] = {a, b, c, 0, 0, 0};
    struct reply r;

    probe_call(number, args, &r);
    return r.error ? -(int)r.value : (int)r.value;
}

static void
row(const char *name, int value)
{
    char digits[12], *end = digits + sizeof(digits), *p = end;
    unsigned int length = 0, u = value < 0 ? 0U - (word)value : (word)value;

    while (name[length])
        length++;
    trap(1004, 1, (word)name, length);
    do {
        *--p = '0' + u % 10;
        u /= 10;
    } while (u);
    if (value < 0)
        *--p = '-';
    trap(1004, 1, (word)p, end - p);
    trap(1004, 1, (word)"\n", 1);
}

static int
set(int which, const struct timer *value, struct timer *old)
{
    return trap(1126, which, (word)value, (word)old);
}

static int
get(int which, struct timer *value)
{
    return trap(1125, which, (word)value, 0);
}

int
main(int argc, char **argv)
{
    struct timer armed = {3, 40000, 12, 90000}, value = {0}, zero = {0};

    if (argc > 1 && argv[1][0] == 'a') {
        armed = zero;
        armed.value_usec = 100000;
        row("arm-one-shot ", set(0, &armed, 0));
        trap(1082, 200, 0, 0);
        row("survived ", 1);
        return 1;
    }
    for (int which = 0; which <= 3; which++) {
        row("timer ", which);
        row("set ", set(which, &armed, &value));
        row("get ", get(which, &value));
        row("interval-sec ", value.interval_sec);
        row("interval-usec ", value.interval_usec);
        row("active ", value.value_sec >= 10 && value.value_sec <= 12);
        row("disarm ", set(which, &zero, &value));
        row("old-active ", value.value_sec >= 10 && value.value_sec <= 12);
        row("get-disarmed ", get(which, &value));
        row("stopped ", !value.value_sec && !value.value_usec);
    }
    row("get-null ", get(0, 0));
    row("set-null ", set(0, 0, &value));
    row("set-both-null ", set(0, 0, 0));
    row("get-invalid ", get(-1, &value));
    row("set-invalid ", set(-1, &zero, &value));
    row("set-bad-input ", set(0, (void *)1, 0));
    row("set-bad-output ", set(0, &zero, (void *)1));
    armed.value_usec = 1000000;
    row("set-bad-usec ", set(0, &armed, 0));
    value.value_sec = 99;
    row("invalid-time-old ", set(0, &armed, &value));
    row("invalid-time-sentinel ", value.value_sec);
    armed.value_usec = 90000;
    row("bad-old-arming ", set(0, &armed, (void *)1));
    row("get-after-bad-old ", get(0, &value));
    row("active-after-bad-old ", value.value_sec > 0);
    row("clear-after-bad-old ", set(0, &zero, 0));
    row("invalid-get-null ", get(-1, 0));
    row("invalid-set-null ", set(-1, 0, 0));
    return 0;
}
