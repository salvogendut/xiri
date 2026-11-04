/* Independent IRIX o32/n32 socketpair observations; no vendor source. */
typedef unsigned int u32;
extern void probe_call(u32, const u32 *, u32 *);
static u32 record[256];
static unsigned char pair[16];

static int call(unsigned slot, u32 number, u32 a, u32 b, u32 c, u32 d)
{
    u32 args[6] = {a, b, c, d, 0, 0};
    probe_call(number, args, record + slot);
    return record[slot + 2] == 0;
}

static u32 word(const unsigned char *p)
{
    return (u32)p[0] << 24 | (u32)p[1] << 16 | (u32)p[2] << 8 | p[3];
}

int main(int argc, char **argv)
{
    u32 mode = 0, domain = 1, type = 2, protocol = 0, pointer;
    u32 fd0, fd1, a[6], r[3];
    unsigned offset = 4;
    if (argc > 1)
        for (char *p = argv[1]; *p; p++) mode = mode * 10 + *p - '0';
    record[0] = 0x58535052; record[1] = mode;
    call(2, 1024, 0, 0, 0, 0); call(5, 1047, 0, 0, 0, 0);
    call(8, 1040, 109, 0, 0, 0); /* SGI_FDHI before allocation */
    for (unsigned i = 0; i < sizeof(pair); i++) pair[i] = 0xa5;
    if (mode == 3) offset++;
    pointer = (u32)(pair + offset);
    if (mode == 1 || mode == 6) pointer = 0;
    if (mode == 2) pointer = 1;
    if (mode == 4) pointer = (u32)main;
    if (mode == 5) pointer = 0xfffffffc;
    if (mode == 10) domain = 3;
    if (mode == 11) type = 1; /* datagrams: measured, outside initial subset */
    if (mode == 12) type = 0;
    if (mode == 13) type = 3;
    if (mode == 14) protocol = 6;
    if (mode == 15) protocol = 0xffffffff;
    if (mode == 16) { domain = 2; protocol = 6; }
    if (mode == 17) type |= 0x10000000;
    if (mode == 18) domain = 999;
    if (!call(11, 1155, domain, type, protocol, pointer)) goto failed;
    fd0 = word(pair + offset); fd1 = word(pair + offset + 4);
    record[100] = fd0; record[101] = fd1;
    call(14, 1040, 109, 0, 0, 0);
    record[128] = 16; record[144] = 16;
    for (unsigned i = 129; i < 133; i++) record[i] = 0xa5a5a5a5;
    for (unsigned i = 145; i < 149; i++) record[i] = 0xa5a5a5a5;
    call(17, 1094, fd0, (u32)(record+129), (u32)(record+128), 0);
    call(20, 1093, fd1, (u32)(record+145), (u32)(record+144), 0);
    if (!call(23, 1004, fd0, (u32)"PAIR", 4, 0)) goto close_both;
    if (!call(26, 1003, fd1, (u32)(record+160), 4, 0)) goto close_both;
    if (!call(29, 1004, fd1, (u32)"BACK", 4, 0)) goto close_both;
    call(32, 1003, fd0, (u32)(record+164), 4, 0);
close_both:
    call(35, 1006, fd0, 0, 0, 0);
    if (mode == 7) call(38, 1003, fd1, (u32)(record+168), 4, 0);
    call(41, 1006, fd1, 0, 0, 0);
    goto done;
failed:
    if (mode == 6) {
        for (unsigned i = 0; i < 32; i++) {
            call(44, 1155, 1, 2, 0, 0);
            if (record[44] == 14 && record[46] == 1) record[108]++;
        }
    }
done:
    call(47, 1040, 109, 0, 0, 0);
    for (unsigned i = 0; i < sizeof(pair); i++) ((unsigned char *)(record+112))[i] = pair[i];
    a[0] = 1; a[1] = (u32)record; a[2] = sizeof(record);
    a[3] = a[4] = a[5] = 0;
    probe_call(1004, a, r);
    return r[2] || r[0] != sizeof(record) ? 99 : 0;
}
