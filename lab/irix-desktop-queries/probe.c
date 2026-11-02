/* Independent raw readlink and sysconf observations; no vendor headers. */
typedef unsigned int u32;
extern void probe_call(u32, const u32 *, u32 *);
static u32 record[144];
static const unsigned char readonly[256] = { 1 };
static const char path[] = PATHNAME;

static void call(u32 number, u32 a, u32 b, u32 c, u32 *result)
{
    u32 args[6] = {a, b, c, 0, 0, 0};
    probe_call(number, args, result);
}

int main(int argc, char **argv)
{
    u32 r[3], dest, name = (u32)path;
    unsigned char *bytes = (unsigned char *)record;
    (void)argv;
    if (argc > 1) {
        call(1046, 1234, 0, 0, r); if (r[2]) return 91;
        call(1023, 1234, 0, 0, r); if (r[2]) return 92;
    }
    record[0] = 0x58495152; record[1] = CASE;
    call(1024, 0, 0, 0, r); record[6] = r[0]; record[7] = r[1];
    call(1047, 0, 0, 0, r); record[8] = r[0]; record[9] = r[1];
    for (u32 i = 64; i < sizeof(record); i++) bytes[i] = 0xa5;
    call(1135, 0x802000, 8192, 0, r); if (r[2]) return 93;
    for (u32 i = 0; i < 256; i++) ((volatile unsigned char *)0x801f00)[i] = 0xa5;
    dest = (u32)(bytes + 72 + ALIGN);
    if (POINTER == 1) dest = 0;
    if (POINTER == 2) dest = 0x80000000;
    if (POINTER == 3) dest = (u32)readonly;
    if (POINTER == 4) dest = 0x802000 - TAIL;
    if (BADPATH) name = 0;
    if (TRAP == 1040) call(TRAP, 22, COUNT, 0, record + 2);
    else call(TRAP, name, dest, COUNT, record + 2);
    for (u32 i = 0; i < 256; i++) bytes[320+i] = ((volatile unsigned char *)0x801f00)[i];
    call(1004, 1, (u32)record, sizeof(record), r);
    return r[2] || r[0] != sizeof(record) ? 94 : 0;
}
