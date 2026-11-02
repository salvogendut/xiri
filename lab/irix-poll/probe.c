/* Independent raw poll observer with pipe readiness and guarded arrays. */
typedef unsigned int u32;
typedef unsigned short u16;
extern void probe_call(u32, const u32 *, u32 *);
static u32 record[144];
static const u32 readonly[8] = { 0xffffffff, 0x0001a5a5 };

static void call(u32 number, u32 a, u32 b, u32 c, u32 *result)
{
    u32 args[6] = {a, b, c, 0, 0, 0};
    probe_call(number, args, result);
}

int main(int argc, char **argv)
{
    u32 r[3], rd, wr, dest;
    unsigned char *bytes = (unsigned char *)record;
    u32 *fds = record+18;
    (void)argv;
    if (argc > 1) {
        call(1046, 1234, 0, 0, r); if (r[2]) return 91;
        call(1023, 1234, 0, 0, r); if (r[2]) return 92;
    }
    record[0] = 0x5849504c; record[1] = CASE;
    call(1024, 0, 0, 0, r); record[6] = r[0]; record[7] = r[1];
    call(1047, 0, 0, 0, r); record[8] = r[0]; record[9] = r[1];
    call(1042, 0, 0, 0, r); if (r[2]) return 93;
    rd = r[0]; wr = r[1]; record[10] = rd; record[11] = wr;
    for (u32 i=64; i<sizeof(record); i++) bytes[i]=0xa5;
    call(1135, 0x802000, 8192, 0, r); if (r[2]) return 94;
    for (u32 i=0; i<256; i++) ((volatile unsigned char *)0x801f00)[i]=0xa5;
    if (STATE == 1) {
        call(1004, wr, (u32)"X", 1, r); if (r[2] || r[0]!=1) return 95;
    }
    if (STATE == 2) { call(1006, wr, 0, 0, r); if (r[2]) return 96; }
    if (STATE == 3) { call(1006, rd, 0, 0, r); if (r[2]) return 97; }
    fds[0] = FD_KIND==1 ? wr : FD_KIND==2 ? 0xffffffff : FD_KIND==3 ? 12345 : rd;
    fds[1] = (EVENTS<<16)|0xa5a5;
    fds[2] = wr; fds[3] = (4U<<16)|0xa5a5;
    dest = (u32)fds;
    if (POINTER==1) dest=0;
    if (POINTER==2) dest=0x80000000;
    if (POINTER==3) dest=(u32)readonly;
    if (POINTER==4) {
        dest=0x802000-TAIL;
        for (u32 i=0; i!=TAIL; i++) ((volatile unsigned char *)dest)[i]=bytes[72+i];
    }
    call(1087, dest, NFDS, TIMEOUT, record+2);
    for (u32 i=0; i<256; i++) bytes[320+i]=((volatile unsigned char *)0x801f00)[i];
    call(1004, 1, (u32)record, sizeof(record), r);
    return r[2] || r[0]!=sizeof(record) ? 98 : 0;
}
