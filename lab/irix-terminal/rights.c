/* Independent observations of legacy IRIX Unix-stream descriptor passing. */
typedef unsigned int u32;
extern void probe_call(u32, const u32 *, u32 *);
static u32 record[256];
static int call(unsigned slot, u32 number, u32 a, u32 b, u32 c, u32 d)
{
    u32 args[6] = {a, b, c, d, 0, 0};
    probe_call(number, args, record + slot);
    return record[slot + 2] == 0;
}
int main(int argc, char **argv)
{
    u32 mode=0, pair[2], file, message[6]={0}, vector[2], send[2], a[6], r[3];
    if (argc>1) for (char *p=argv[1]; *p; p++) mode=mode*10+*p-'0';
    record[0]=0x58524644;record[1]=mode;
    call(2,1024,0,0,0,0);call(5,1047,0,0,0,0);call(8,1040,109,0,0,0);
    if (!call(11,1155,1,2,0,(u32)pair)) goto done;
    if (!call(14,1005,(u32)"input.txt",0,0,0)) goto close_pair;
    file=record[14];send[0]=file;send[1]=file;
    vector[0]=(u32)"D";vector[1]=1;
    message[2]=(u32)vector;message[3]=1;message[4]=(u32)send;message[5]=4;
    if(mode==1) send[0]=0x7fffffff;
    if(mode==2) message[4]=1;
    if(mode==3) message[5]=3;
    if(mode==4 || mode==10) message[5]=8;
    if(mode==5) message[4]=0;
    if(mode==6) message[5]=0;
    if(mode==14) message[5]=0xffffffff;
    if(!call(17,1102,pair[0],(u32)message,0,0)) goto close_file;
    call(20,1006,file,0,0,0);file=0xffffffff;
    for(unsigned i=0;i<4;i++) record[128+i]=0xa5a5a5a5;
    vector[0]=(u32)(record+144);vector[1]=1;
    message[4]=(u32)(record+128);message[5]=16;
    if(mode==7) message[5]=0;
    if(mode==8) message[5]=1;
    if(mode==9) message[5]=3;
    if(mode==10) message[5]=4;
    if(mode==11) message[4]=1;
    if(mode==12) message[5]=0xffffffff;
    if(mode==13) message[5]=65;
    if(mode==15) vector[0]=1;
    if(mode==16) message[4]=0;
    call(23,1099,pair[1],(u32)message,mode==17?2:0,0);
    record[120]=message[5];call(26,1040,109,0,0,0);
    if (record[128]!=0xa5a5a5a5) {
        call(29,1003,record[128],(u32)(record+152),6,0);
        call(32,1006,record[128],0,0,0);
    }
    if (record[129]!=0xa5a5a5a5) call(35,1006,record[129],0,0,0);
close_file:
    if(file!=0xffffffff) call(38,1006,file,0,0,0);
close_pair:
    call(41,1006,pair[0],0,0,0);call(44,1006,pair[1],0,0,0);
done:
    call(47,1040,109,0,0,0);
    a[0]=1;a[1]=(u32)record;a[2]=sizeof(record);a[3]=a[4]=a[5]=0;
    probe_call(1004,a,r);return r[2] || r[0]!=sizeof(record)?99:0;
}
