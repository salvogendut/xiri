/* Independent observer for the I_STR master check used by IRIX ptsname. */
typedef unsigned int u32;
extern void probe_call(u32, const u32 *, u32 *);
static u32 record[256];
static int call(unsigned slot,u32 nr,u32 a,u32 b,u32 c)
{
    u32 args[6]={a,b,c,0,0,0};probe_call(nr,args,record+slot);
    return record[slot+2]==0;
}
int main(int argc,char **argv)
{
    u32 mode=0,fd,request[4]={0x5064,0,0,0},pointer=(u32)request;
    u32 args[6]={1,(u32)record,sizeof(record),0,0,0},r[3];
    if(argc>1) for(char *p=argv[1];*p;p++) mode=mode*10+*p-'0';
    record[0]=0x5850544d;record[1]=mode;
    call(2,1024,0,0,0);call(5,1047,0,0,0);
    if(!call(8,1005,(u32)(mode==1?"/dev/ptc":mode==2?"input.txt":"/dev/ptmx"),2,0)) goto done;
    fd=record[8];
    if(mode==4)pointer=0;
    if(mode==5)request[1]=1;
    if(mode==6)request[0]=0x5065;
    if(mode==7)request[2]=1;
    if(mode==8)request[3]=1;
    if(mode==9)request[1]=0xffffffff;
    call(11,1054,mode==3?0xffffffff:fd,0x5308,pointer);
    call(14,1006,fd,0,0);
done:
    probe_call(1004,args,r);return r[2] || r[0]!=sizeof(record)?99:0;
}
