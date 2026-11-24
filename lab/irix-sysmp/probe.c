/* Syscall-only probe for o32 and n32 on IRIX and Xiri.
 * The assembly veneers return negative IRIX errno on failure. */
typedef unsigned int word;
extern int query(int, int, void *, int, int);
extern int inventory(int, int, void *, int);
extern void emit(const char *, unsigned int);

#define PRINT(s) emit(s, sizeof(s) - 1)
#define CANARY 0x55555555
enum { NPROCS = 1, NAPROCS = 2, SASZ = 9, SAGET = 10, PGSIZE = 14,
       SAGET1 = 15, SINFO = 1, RMINFO = 8 };
static word data[1024];

static void
number(int value)
{
    unsigned int u = (unsigned int)value;
    char buf[12];
    char *end = buf + sizeof(buf), *s = end;

    if (value < 0)
        u = 0U - u;
    do {
        *--s = (char)('0' + u % 10);
        u /= 10;
    } while (u);
    if (value < 0)
        *--s = '-';
    emit(s, end - s);
}

static void
record(int op, int selector, int length, int cpu, unsigned int fields)
{
    for (unsigned int i = 0; i < sizeof(data) / sizeof(data[0]); i++)
        data[i] = CANARY;
    int rc = query(op, selector, data, length, cpu);
    number(op); PRINT(" "); number(selector); PRINT(" ");
    number(length); PRINT(" "); number(cpu); PRINT(" = "); number(rc);
    for (unsigned int i = 0; i < fields; i++) {
        PRINT(" ");
        number((int)data[i]);
    }
    PRINT("\n");
}

static void
check_inventory(void)
{
    int stride = inventory(5, 1, 0, 0);
    PRINT("inventory stride "); number(stride); PRINT("\n");
    if (stride != 24)
        return;
    for (int size = 0; size <= stride; size += stride / 2) {
        data[0] = CANARY;
        PRINT("inventory bytes "); number(size); PRINT(" = ");
        number(inventory(5, 2, data, size)); PRINT(" ");
        number(data[0]); PRINT("\n");
    }
    int used = inventory(5, 2, data, sizeof(data));
    PRINT("inventory used "); number(used); PRINT("\n");
    for (int i = 0; i + stride <= used && i + stride <= (int)sizeof(data);
         i += stride) {
        word *row = data + i / sizeof(word);
        if (row[1] == 3 && row[2] == 9) {
            PRINT("main memory MiB "); number(row[5]); PRINT("\n");
        }
    }
}

int
run(void)
{
    int sys = query(SASZ, SINFO, 0, 0, 0);
    int mem = query(SASZ, RMINFO, 0, 0, 0);

    record(NPROCS, 0, 0, 0, 0);
    record(NAPROCS, 0, 0, 0, 0);
    record(PGSIZE, 0, 0, 0, 0);
    record(SASZ, SINFO, 0, 0, 0);
    record(SASZ, RMINFO, 0, 0, 0);
    if (sys <= 0 || sys > 1000 || mem <= 0 || mem > 1000)
        return 1;
    record(SAGET, SINFO, sys, 0, 11);
    record(SAGET1, SINFO, sys, 0, 11);
    record(SAGET, RMINFO, mem, 0, 12);
    record(SAGET, SINFO, 4, 0, 2);
    record(SAGET, RMINFO, mem + 4, 0, mem / 4 + 1);
    record(SAGET, SINFO, 0, 0, 1);
    record(SAGET1, SINFO, sys, 99, 1);
    record(SAGET1, RMINFO, mem, 0, 1);
    record(SAGET1, RMINFO, mem, 99, 1);
    record(SAGET, SINFO, -1, 0, 1);
    check_inventory();
    return 0;
}
