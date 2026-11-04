/* Foreign half of the native-peer receive and descriptor-cleanup control. */
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
    u32 mode=argc>1?(u32)(argv[1][0]-'0'):0;
    u32 vector[2]={(u32)(record+144),1};
    u32 msg[6]={0,0,(u32)vector,1,(u32)(record+128),16};
    u32 args[6]={1,(u32)record,sizeof(record),0,0,0},r[3];
    record[0]=0x58525043;record[1]=mode;
    for(unsigned i=128;i<132;i++) record[i]=0xa5a5a5a5;
    call(2,1024,0,0,0);call(5,1047,0,0,0);call(8,1040,109,0,0);
    if(mode==2)msg[4]=1;
    if(mode==3)vector[0]=1;
    call(11,1099,0,(u32)msg,0);record[120]=msg[5];
    call(14,1040,109,0,0);
    if(record[128]!=0xa5a5a5a5) {
        call(17,1003,record[128],(u32)(record+152),6);
        call(20,1006,record[128],0,0);
    }
    call(23,1040,109,0,0);
    probe_call(1004,args,r);return r[2] || r[0]!=sizeof(record)?99:0;
}
