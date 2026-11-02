/* Raw, guarded record-lock observer; the same ELF runs on both kernels. */
typedef unsigned int u32;
extern void probe_call(u32, const u32 *, u32 *);
static u32 record[144];
static unsigned char buffer[96];
static unsigned char seek_data[64];
static const u32 readonly_lock[16] = {0x00010000};

static void call(u32 number, u32 a, u32 b, u32 c, u32 *result)
{
    u32 args[6] = {a,b,c,0,0,0};
    probe_call(number,args,result);
}

static void put32(unsigned char *p, u32 value)
{
    p[0]=value>>24; p[1]=value>>16; p[2]=value>>8; p[3]=value;
}

int main(int argc, char **argv)
{
    u32 r[3], fd, dest;
    unsigned char *bytes=(unsigned char *)record;
    unsigned char *lock=buffer+8+ALIGN;
    (void)argv;
    if(argc>1) {
        call(1046,1234,0,0,r); if(r[2])return 91;
        call(1023,1234,0,0,r); if(r[2])return 92;
    }
    record[0]=0x5849464c; record[1]=CASE; record[5]=COMMAND;
    call(1024,0,0,0,r);record[6]=r[0];record[7]=r[1];
    call(1047,0,0,0,r);record[8]=r[0];record[9]=r[1];
    call(1005,(u32)(KIND==2 ? "tree" : "tree/file"),OPEN_MODE,0,r);
    if(r[2])return 93;
    fd=r[0]; record[10]=fd;record[11]=OPEN_MODE;
    /* Advance the open description without depending on a separate lseek
     * adapter. Write-only/directory setup errors are retained in the record. */
    call(1003,fd,(u32)seek_data,sizeof(seek_data),record+12);
    if(KIND==1) {
        call(1042,0,0,0,r); if(r[2])return 94;
        fd=r[0];
    }
    if(KIND==3)fd=0xffffffff;
    if(KIND==4){call(1006,fd,0,0,r);if(r[2])return 95;}
    for(u32 i=64;i<sizeof(record);i++)bytes[i]=0xa5;
    for(u32 i=0;i<sizeof(buffer);i++)buffer[i]=0xa5;
    call(1135,0x802000,8192,0,r);if(r[2])return 96;
    for(u32 i=0;i<256;i++)((volatile unsigned char *)0x801f00)[i]=0xa5;
    put32(lock,(TYPE<<16)|(WHENCE&0xffff));
#if N32
    put32(lock+8,START_HIGH);put32(lock+12,START);
    put32(lock+16,LENGTH_HIGH);put32(lock+20,LENGTH);
#else
    put32(lock+4,START);put32(lock+8,LENGTH);
#endif
    dest=(u32)lock;
    if(POINTER==1)dest=0;
    if(POINTER==2)dest=0x80000000;
    if(POINTER==3)dest=(u32)readonly_lock;
    if(POINTER==4) {
        dest=0x802000-TAIL;
        for(u32 i=0;i!=TAIL;i++)((volatile unsigned char *)dest)[i]=lock[i];
    }
    call(1062,fd,COMMAND,dest,record+2);
    for(u32 i=0;i<sizeof(buffer);i++)bytes[96+i]=buffer[i];
    for(u32 i=0;i<256;i++)bytes[320+i]=((volatile unsigned char *)0x801f00)[i];
    call(1004,1,(u32)record,sizeof(record),r);
    return r[2] || r[0]!=sizeof(record) ? 97 : 0;
}
