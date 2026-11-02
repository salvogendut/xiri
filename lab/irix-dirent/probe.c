/* Independent directory-record and cursor observer, using raw IRIX traps. */
typedef unsigned int u32;
extern void probe_call(u32, const u32 *, u32 *);
static u32 record[1024];
static const unsigned char readonly[1024] = {1};

static void call(u32 n, u32 a, u32 b, u32 c, u32 d, u32 *result)
{
    u32 args[6] = {a,b,c,d,0,0}; probe_call(n,args,result);
}

int main(int argc, char **argv)
{
    u32 r[3], fd, dest, eof;
    unsigned char *bytes=(unsigned char *)record;
    (void)argv;
    if (argc>1) {
        call(1046,1234,0,0,0,r); if(r[2])return 91;
        call(1023,1234,0,0,0,r); if(r[2])return 92;
    }
    record[0]=0x58494452; record[1]=CASE;
    call(1024,0,0,0,0,r); record[6]=r[0]; record[7]=r[1];
    call(1047,0,0,0,0,r); record[8]=r[0]; record[9]=r[1];
    call(1005,(u32)PATHNAME,0,0,0,r); if(r[2])return 93;
    fd=FD_KIND ? 0xffffffff : r[0]; record[10]=fd;
    for(u32 i=64;i<sizeof(record);i++)bytes[i]=0xa5;
    call(1135,0x802000,8192,0,0,r); if(r[2])return 94;
    for(u32 i=0;i<256;i++)((volatile unsigned char *)0x801f00)[i]=0xa5;
    dest=(u32)(bytes+128+ALIGN);
    if(POINTER==1)dest=0;
    if(POINTER==2)dest=0x80000000;
    if(POINTER==3)dest=(u32)readonly;
    if(POINTER==4)dest=0x802000-TAIL;
    eof=EOF_KIND==0 ? 0 : EOF_KIND==1 ? (u32)(record+20) :
        EOF_KIND==2 ? 0x80000000 : (u32)readonly;
    call(TRAP,fd,dest,COUNT,eof,record+2);
    call(TRAP,fd,(u32)(bytes+1408),1024,(u32)(record+24),record+12);
    for(u32 i=0;i<256;i++)bytes[3072+i]=((volatile unsigned char *)0x801f00)[i];
    call(1004,1,(u32)record,sizeof(record),0,r);
    return r[2] || r[0]!=sizeof(record) ? 95 : 0;
}
