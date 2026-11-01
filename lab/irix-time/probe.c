/* Original time/gettimeofday observations using explicit 32-bit ABI slots. */
typedef unsigned int U;
struct reply { U value, second, error; };
extern void probe_call(U,const U *,struct reply *);
static struct reply call(U n,U a,U b,U c,U d,U e,U f){
    U args[6]={a,b,c,d,e,f};struct reply r;probe_call(n,args,&r);return r;
}
#define C(n,a,b,c) call(n,(U)(a),(U)(b),(U)(c),0,0,0)
static U rec[64]={0x5854494d,CASE,TRAP,MODE},zero[4],early[8],late[8];
static void reply(U at,struct reply r){rec[at]=r.value;rec[at+1]=r.second;rec[at+2]=r.error;}
int main(int argc,char **argv){
    if(argc>1){U uid=argv[1][0]=='1'?1234:0;
        if(C(1040,40,0,zero).error || C(1123,uid,uid,0).error || C(1124,uid,uid,0).error)return 98;
    }
    struct reply r=C(1024,0,0,0);rec[28]=r.value;rec[29]=r.second;
    r=C(1047,0,0,0);rec[30]=r.value;rec[31]=r.second;
    r=C(1056,14,0,0);if(r.error)return 97;U page=r.value;rec[4]=page;
    r=C(1005,"/dev/zero",2,0);if(r.error)return 96;U fd=r.value;
    r=call(1134,0,2*page,3,0x102,fd,0);if(r.error)return 95;U base=r.value;
    unsigned char *buf=(unsigned char *)(base+page-32);
    for(U i=0;i<32;i++)buf[i]=0xa5;
    for(U i=0;i<8;i++)early[i]=late[i]=0xa5a5a5a5;
    if(C(1136,base+page,page,0).error)return 94;
    U offset=8;
    if(MODE>=2 && MODE<=4)offset+=MODE-1;
    if(MODE==9)offset=28;
    if(MODE==10)offset=31;
    U pointer=(U)buf+offset;
    if(MODE==1)pointer=0;
    if(MODE==5)pointer=1;
    if(MODE==6)pointer=0x80000000U;
    if(MODE==7)pointer=0xffffffffU;
    rec[5]=(MODE==1 || (MODE>=5 && MODE<=7))?0xffffffffU:offset;
    if(MODE==8 && C(1136,base,page,1).error)return 93;
    rec[25]=C(1128,early,0,0).error;
    reply(6,C(1013,0,0,0));
    reply(9,C(TRAP,pointer,SECOND,0));
    reply(12,C(1013,0,0,0));
    for(U i=0;i<4;i++)rec[15+i]=early[i];
    rec[23]=C(1082,10,0,0).error;
    rec[26]=C(1128,late,0,0).error;
    for(U i=0;i<4;i++)rec[19+i]=late[i];
    rec[24]=SECOND;
    for(U i=0;i<32;i++)rec[32+i]=buf[i];
    r=C(1004,1,rec,sizeof(rec));return r.error || r.value!=sizeof(rec)?92:0;
}
