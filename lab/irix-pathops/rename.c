/* Independent IRIX rename observer. Same ELF bytes run on both systems. */
typedef unsigned int U;
typedef unsigned char B;
extern void probe_call(U, const U *, U *);
static U rec[256], st[40], ids[10][3];
static char longpath[1100];

static void call(U nr, U a, U b, U c, U *r)
{
    U args[6] = {a, b, c, 0, 0, 0};
    probe_call(nr, args, r);
}

static void snapshot(U index, const char *path)
{
    U r[3], *out = rec + 32 + index * 20;
    call(1159, 3, (U)path, (U)st, r);
    out[0] = r[0]; out[1] = r[2];
    if (r[2]) return;
    ids[index][0] = st[0]; ids[index][1] = st[4]; ids[index][2] = st[5];
    out[2] = st[6]; out[3] = st[8]; out[4] = st[9];
    U type = st[6] & 0170000;
    if (type == 0100000 || type == 0120000) {
        out[5] = st[7]; out[6] = st[15];
        if (type == 0120000) {
            call(1116, (U)path, (U)(out + 10), 32, r);
        } else {
            call(1005, (U)path, 0, 0, r);
            if (r[2]) { out[8] = r[0]; out[9] = r[2]; return; }
            U fd = r[0], close_result[3];
            call(1003, fd, (U)(out + 10), 32, r);
            call(1006, fd, 0, 0, close_result);
            if (close_result[2]) out[18] = close_result[0];
        }
        out[7] = r[2] ? 0 : r[0]; out[8] = r[2] ? r[0] : 0; out[9] = r[2];
    }
}

int main(int argc, char **argv)
{
    const char *paths[5] = {"src", "dst", "alias", "src/item", "dst/item"};
    U mode, from, to, r[3];
    if (argc != 4) return 2;
    mode = argv[1][0] - '0'; from = (U)argv[2]; to = (U)argv[3];
    rec[0] = 0x58524e4d; rec[1] = mode;
    call(1024, 0, 0, 0, rec + 2);
    for (U i = 0; i < 5; i++) snapshot(i, paths[i]);
    if (mode == 1) from = 0;
    if (mode == 2) from = 0x80000000;
    if (mode == 3) to = 0;
    if (mode == 4) to = 0x80000000;
    for (U i = 0; i < sizeof(longpath)-1; i++) longpath[i] = 'a';
    if (mode == 5) from = (U)longpath;
    if (mode == 6) to = (U)longpath;
    call(1114, from, to, 0, rec + 8);
    for (U i = 0; i < 5; i++) snapshot(i + 5, paths[i]);
    /* Compare inode identity without exporting filesystem-specific numbers. */
    for (U i = 0; i < 5; i++) {
        U same = 1;
        for (U j = 0; j < 3; j++) if (ids[0][j] != ids[i + 5][j]) same = 0;
        if (rec[33] == 0 && rec[32 + (i + 5)*20 + 1] == 0 && same)
            rec[11] |= 1U << i;
    }
    call(1004, 1, (U)rec, sizeof(rec), r);
    return r[2] || r[0] != sizeof(rec) ? 3 : 0;
}
