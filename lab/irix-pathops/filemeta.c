/* Independent symlink/utimets observer; identical bytes on IRIX and NetBSD. */
typedef unsigned int U;
extern void probe_call(U, const U *, U *);
static U record[128], st[40], before[3][4], clock_before[2], clock_after[2];
static int times[4] = {946684800, 123456789, 946684812, 987654321};
static char longpath[1100];
static U mode, timestamp;

static void call(U nr, U a, U b, U c, U *r)
{
    U args[6] = {a, b, c, 0, 0, 0};
    probe_call(nr, args, r);
}

static void snapshot(U which, U after, const char *path)
{
    U r[3], *out = record + 16 + (which + after * 3) * 18;
    call(1159, 3, (U)path, (U)st, r);
    out[0] = r[2] ? r[0] : 0; out[1] = r[2];
    if (r[2]) return;
    out[2] = st[6]; out[3] = st[8]; out[4] = st[9];
    U type = st[6] & 0170000;
    if (type == 0100000 || type == 0120000) out[5] = st[15];
    if (type == 0120000 && !timestamp) {
        call(1116, (U)path, (U)(out + 6), 32, r);
        out[14] = r[2] ? 0 : r[0]; out[15] = r[2] ? r[0] : 0;
    }
    if (!timestamp || type == 0120000) return;
    if (!after) {
        for (U i = 0; i < 4; i++) before[which][i] = st[17+i];
    } else {
        for (U i = 0; i < 4; i++) {
            if (mode == 1) continue;
            if (st[17+i] == before[which][i]) out[16] |= 1U << i;
            else if (mode != 1) out[6+i] = st[17+i];
        }
        /* A null times pointer uses current time. Compare bounds, not clocks. */
        if (mode == 1) {
            for (U i = 0; i < 2; i++)
                if (st[17+i*2] >= clock_before[0] && st[17+i*2] <= clock_after[0] &&
                    st[18+i*2] < 1000000000U) out[17] |= 1U << i;
        }
    }
}

int main(int argc, char **argv)
{
    if (argc != 5) return 2;
    timestamp = argv[1][0] == 't'; mode = argv[2][0] - '0';
    U a = (U)argv[3], b = timestamp ? (U)times : (U)argv[4], r[3];
    record[0] = 0x58464d54; record[1] = timestamp ? 1235 : 1115; record[2] = mode;
    call(1024, 0, 0, 0, record + 3);
    for (U i = 0; i < sizeof(longpath)-1; i++) longpath[i] = 'a';
    const char *watch[3] = {argv[4], "file", "link"};
    for (U i = 0; i < 3; i++) snapshot(i, 0, watch[i]);
    if (timestamp) {
        if (mode == 1) b = 0;
        if (mode == 2) b = 0x80000000;
        if (mode == 3) times[1] = -1;
        if (mode == 4) times[3] = 1000000000;
        if (mode == 5) times[0] = -1;
        if (mode == 6) a = 0;
        if (mode == 7) a = 0x80000000;
        if (mode == 8) a = (U)longpath;
        if (mode == 9) times[1] = times[3] = 0;
    } else {
        if (mode == 1) a = 0;
        if (mode == 2) a = 0x80000000;
        if (mode == 3) b = 0;
        if (mode == 4) b = 0x80000000;
        if (mode == 5) a = (U)longpath;
        if (mode == 6) b = (U)longpath;
    }
    call(1128, (U)clock_before, 0, 0, r);
    call(record[1], a, b, 0, record + 8);
    call(1128, (U)clock_after, 0, 0, r);
    for (U i = 0; i < 3; i++) snapshot(i, 1, watch[i]);
    call(1004, 1, (U)record, sizeof(record), r);
    return r[2] || r[0] != sizeof(record) ? 3 : 0;
}
