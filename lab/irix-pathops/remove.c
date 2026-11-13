/* Independent unlink/rmdir observer. Identical ELF bytes run on both hosts. */
typedef unsigned int U;
extern void probe_call(U, const U *, U *);
static U record[128], st[40];
static char longpath[1100];

static void call(U nr, U a, U b, U c, U *r)
{
    U args[6] = {a, b, c, 0, 0, 0};
    probe_call(nr, args, r);
}

static void snapshot(U index, const char *path)
{
    U r[3], *out = record + 16 + index * 12;
    call(1159, 3, (U)path, (U)st, r);
    out[0] = r[2] ? r[0] : 0; out[1] = r[2];
    if (r[2]) return;
    out[2] = st[6]; out[3] = st[8]; out[4] = st[9];
    if ((st[6] & 0170000) == 0100000 || (st[6] & 0170000) == 0120000) {
        out[5] = st[7]; out[6] = st[15];
    }
}

int main(int argc, char **argv)
{
    const char *watch[] = {"target", "alias", "target/item", "keep"};
    U r[3], mode, path, nr;
    if (argc != 4) return 2;
    nr = argv[1][0] == 'u' ? 1010 : 1079;
    mode = argv[2][0] - '0'; path = (U)argv[3];
    record[0] = 0x58524d56; record[1] = nr; record[2] = mode;
    call(1024, 0, 0, 0, record + 3);
    for (U i = 0; i < 4; i++) snapshot(i, watch[i]);
    if (mode == 1) path = 0;
    if (mode == 2) path = 0x80000000;
    for (U i = 0; i < sizeof(longpath)-1; i++) longpath[i] = 'a';
    if (mode == 3) path = (U)longpath;
    call(nr, path, 0, 0, record + 8);
    for (U i = 0; i < 4; i++) snapshot(i + 4, watch[i]);
    call(1004, 1, (U)record, sizeof(record), r);
    return r[2] || r[0] != sizeof(record) ? 3 : 0;
}
