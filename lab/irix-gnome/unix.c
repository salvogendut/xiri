/* Independent o32/n32 observer for pathname stream sockets. No vendor code. */
typedef unsigned int u32;
extern void probe_call(u32, const u32 *, u32 *);
static u32 record[512];
static unsigned char address[112];

static int call(unsigned slot, u32 number, u32 a, u32 b, u32 c)
{
    u32 args[6] = {a, b, c, 0, 0, 0};
    probe_call(number, args, record + slot);
    return record[slot + 2] == 0;
}

int main(int argc, char **argv)
{
    u32 mode = 0, server, client, accepted, length = 12, pointer;
    unsigned char *bytes = (unsigned char *)record;
    const char path[] = "xiri.sock";
    u32 message[6], vector[2], r[3], args[6] = {1, (u32)record, sizeof(record), 0, 0, 0};
    if (argc > 1)
        for (char *p = argv[1]; *p; p++) mode = mode * 10 + *p - '0';
    record[0] = 0x58554e58; record[1] = mode;
    call(2, 1024, 0, 0, 0); call(5, 1047, 0, 0, 0);
    for (u32 i = 512; i < sizeof(record); i++) bytes[i] = 0xa5;
    address[1] = 1;
    for (u32 i = 0; i < sizeof(path); i++) address[2+i] = path[i];
    if (!call(8, 1107, mode == 10 ? 3 : 1, mode == 11 ? 1 : 2, mode == 12 ? 6 : 0)) goto done;
    server = record[8];
    if (mode >= 10 && mode <= 12) goto close_server;
    pointer = (u32)address;
    if (mode >= 20) {
        if (mode <= 22) length = mode - 20;
        if (mode == 23) length = 110;
        if (mode == 24) length = 111;
        if (mode == 25) pointer = 0;
        if (mode == 26) address[1] = 3;
        if (mode == 27) address[2] = 0;
        if (mode == 28) { length = 110; for (u32 i = 2; i < 110; i++) address[i] = 'x'; }
        call(11, 1090, server, pointer, length);
        goto close_server;
    }
    if (!call(11, 1090, server, pointer, length)) goto close_server;
    call(14, 1090, server, pointer, length);
    if (!call(17, 1096, server, 2, 0)) goto close_server;
    record[128] = mode == 2 ? 2 : mode == 3 ? 0 : mode == 4 ? 0xffffffff : 112;
    call(20, 1094, server, (u32)(record+132), (u32)(record+128));
    if (!call(23, 1107, 1, 2, 0)) goto close_server;
    client = record[23];
    if (!call(26, 1091, client, pointer, length)) goto close_client;
    record[164] = 112;
    if (!call(29, 1089, server, mode == 0 ? 0 : (u32)(record+168), mode == 0 ? 0 : (u32)(record+164))) goto close_client;
    accepted = record[29];
    record[200] = 112; record[236] = 112;
    call(32, 1093, client, (u32)(record+204), (u32)(record+200));
    call(35, 1094, client, (u32)(record+240), (u32)(record+236));
    if (!call(38, 1004, client, (u32)"UNIX", 4)) goto close_accepted;
    if (!call(41, 1003, accepted, (u32)(record+272), 4)) goto close_accepted;
    vector[0] = (u32)"REPLY"; vector[1] = 5;
    for (u32 i = 0; i < 6; i++) message[i] = 0;
    message[2] = (u32)vector; message[3] = 1;
    if (!call(44, 1102, accepted, (u32)message, 0)) goto close_accepted;
    vector[0] = (u32)(record+280);
    call(47, 1099, client, (u32)message, 0);
close_accepted:
    call(50, 1006, accepted, 0, 0);
close_client:
    call(53, 1006, client, 0, 0);
close_server:
    call(56, 1006, server, 0, 0);
done:
    probe_call(1004, args, r);
    return r[2] || r[0] != sizeof(record) ? 99 : 0;
}
