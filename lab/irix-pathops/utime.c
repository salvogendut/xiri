/* Raw IRIX utime observer. Record both timestamps without opening the file. */
typedef unsigned int word;
extern void probe_call(word, const word *, word *);
static word args[6], result[3], statbuf[40], clockbuf[2];
static int times[2] = {946684800, 1234567890};

static void
call(word nr, word a, word b, word c)
{
    args[0] = a;
    args[1] = b;
    args[2] = c;
    probe_call(nr, args, result);
}

static word
now(void)
{
    call(1128, (word)clockbuf, 0, 0);
    return clockbuf[0];
}

int
main(int argc, char **argv)
{
    if (argc != 3)
        return 2;
    char mode = argv[1][0];
    word path = (word)argv[2];
    word input = (word)times;
    static word record[8];
    if (mode == 'n')
        input = 0;
    if (mode == 'b')
        input = 1; /* invalid times address */
    if (mode == 'p')
        times[0] = -2;
    if (mode == 's')
        times[0] = -1;
    if (mode != 'r') {
        word before = now();
        call(1030, path, input, 0);
        record[0] = result[2] ? result[0] : 0;
        record[1] = result[2] ? 0 : result[0];
        record[7] = now();
        record[6] = before;
    }
    call(1158, 3, path, (word)statbuf); /* xstat, following symlinks */
    record[2] = result[2] ? result[0] : 0;
    if (!result[2]) {
        record[3] = statbuf[17];
        record[4] = statbuf[19];
        record[5] = statbuf[18] | statbuf[20];
    }
    /* Compact, endian-independent output, also usable on stock IRIX. */
    char line[8 * 9];
    for (unsigned i = 0; i < 8; i++) {
        for (unsigned j = 0; j < 8; j++)
            line[9*i+j] = "0123456789abcdef"[(record[i] >> (28-4*j)) & 15];
        line[9*i+8] = i == 7 ? '\n' : ' ';
    }
    call(1004, 1, (word)line, sizeof(line));
    return result[2] || result[0] != sizeof(line);
}
