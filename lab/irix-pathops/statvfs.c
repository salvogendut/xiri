/* Independent filesystem-information observer for identical IRIX/NetBSD ELFs.
 * Each 512-byte record contains trap, case, v0/v1/a3, open status, then a
 * guarded 256-byte output area. Filesystem-dependent values are not oracles. */
typedef unsigned int U;
typedef unsigned char B;
extern void probe_call(U, const U *, U *);
static U record[128];
static char longpath[1100];

static void call(U nr, U a, U b, U c, U *r)
{
    U args[6] = {a, b, c, 0, 0, 0};
    probe_call(nr, args, r);
}

int main(void)
{
    const char *paths[] = {".", "file", "link", "missing", "", 0,
        (const char *)0x80000000, "file/child", "file/", longpath,
        ".", ".", ".", "denied/file", ".", "missing"};
    U traps[] = {1174, 1175, 1201, 1202};
    U r[3], close_result[3];
    for (U i = 0; i < sizeof(longpath)-1; i++) longpath[i] = 'a';
    for (U t = 0; t < 4; t++) {
        U fdcall = t & 1, count = fdcall ? 8 : 16;
        for (U mode = 0; mode < count; mode++) {
            U *out = record, first, buffer;
            B *bytes = (B *)(out + 16);
            for (U i = 0; i < 128; i++) out[i] = 0;
            for (U i = 0; i < 256; i++) bytes[i] = 0xa5;
            buffer = (U)(bytes + 16);
            out[0] = traps[t]; out[1] = mode;
            if (fdcall) {
                call(1005, (U)(mode == 0 ? "." : "file"), 0, 0, r);
                out[5] = r[2] ? r[0] : 0;
                if (r[2]) return 2;
                first = r[0];
                if (mode == 2 || mode == 3) {
                    call(1006, first, 0, 0, close_result);
                    if (mode == 3) first = (U)-1;
                }
                if (mode == 4) buffer = 0;
                if (mode == 5) buffer = 0x80000000;
                if (mode == 6) buffer++;
                if (mode == 7) buffer = 0xfffffff8;
            } else {
                first = (U)paths[mode];
                if (mode == 10 || mode == 15) buffer = 0;
                if (mode == 11) buffer = 0x80000000;
                if (mode == 12) buffer++;
                if (mode == 14) buffer = 0xfffffff8;
            }
            call(traps[t], first, buffer, 0, out + 2);
            if (fdcall && mode != 2 && mode != 3)
                call(1006, first, 0, 0, close_result);
            call(1004, 1, (U)record, sizeof(record), r);
            if (r[2] || r[0] != sizeof(record)) return 3;
        }
    }
    return 0;
}
