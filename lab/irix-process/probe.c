/* Original paired process/mask probes. Each atomic record is 64 big-endian words. */
typedef unsigned int U;
typedef unsigned char B;
struct reply { U value, second, error; };
extern void probe_call(U, const U *, struct reply *);
static struct reply call(U n,U a,U b,U c,U d,U e,U f) {
    U args[6]={a,b,c,d,e,f}; struct reply r;
    probe_call(n,args,&r); return r;
}
#define C(n,a,b,c) call(n,(U)(a),(U)(b),(U)(c),0,0,0)
static U rec[64]={0x58505243,CASE};
static B input[28],output[140];
static U baseline[4]={0x28000,0,0,0};
static U mask[4],zero[4];
static volatile U cow=0x12345678;
static const char readonly[32]="immutable request storage";
static void put(B *p,U v) { p[0]=v>>24;p[1]=v>>16;p[2]=v>>8;p[3]=v; }
static U word(const B *p) {return ((U)p[0]<<24)|((U)p[1]<<16)|((U)p[2]<<8)|p[3];}
static void reply(U at,struct reply r) {rec[at]=r.value;rec[at+1]=r.second;rec[at+2]=r.error;}
static U pointer(U kind,B *normal) {
    switch(kind) {
    case 1:return 0;
    case 2:return 0x80000000U;
    case 3:return 0xfffffffeU;
    case 4:return (U)normal+1;
    case 5:return 0x00801ff8;
    case 6:return (U)readonly;
    case 7:return (U)(output+4);
    default:return (U)normal;
    }
}
static int emit(void) {
    struct reply r=C(1004,1,rec,sizeof(rec));
    return r.error || r.value!=sizeof(rec);
}
static void pause_input(void) {
    B byte;
    (void)C(1003,0,&byte,1); /* Native inspector holds each process here. Reference uses /dev/null. */
}
static void identity(void) {
    struct reply r=C(1024,0,0,0);rec[56]=r.value;rec[57]=r.second;
    r=C(1047,0,0,0);rec[58]=r.value;rec[59]=r.second;
    r=C(1020,0,0,0);rec[60]=r.value;rec[61]=r.second;rec[62]=r.error;
}
int main(int argc,char **argv) {
    struct reply r;
    U i;
    if(argc>1) {
        U uid=argv[1][0]=='1'?1234:0;
        if(C(1040,40,0,zero).error || C(1123,uid,uid,0).error || C(1124,uid,uid,0).error) return 98;
        r=C(1040,41,0,zero);if(r.error || r.value)return 98;
    }
    if(C(1164,3,baseline,0).error)return 97;
    for(i=0;i<sizeof(input);i++)input[i]=0xa5;
    for(i=0;i<sizeof(output);i++)output[i]=0x5a;
    *(U *)0x00801ff8=0xa5a5a5a5;*(U *)0x00801ffc=0x5a5a5a5a;
    if(KIND==0) {
        U values[4]={MASK0,MASK1,MASK2,MASK3};
        B *where=SET_KIND==7?output+4:input+4+(SET_KIND==4);
        for(i=0;i<4;i++)put(where+4*i,values[i]);
        r=C(1164,HOW,pointer(SET_KIND,input+4),pointer(OLD_KIND,output+4));
        reply(2,r);
        for(i=0;i<7;i++)rec[5+i]=word(input+4*i);
        for(i=0;i<7;i++)rec[12+i]=word(output+4*i);
        r=C(1164,0,0,mask);reply(23,r);
        for(i=0;i<4;i++)rec[19+i]=mask[i];
        rec[26]=*(U *)0x00801ff8;rec[27]=*(U *)0x00801ffc;
        rec[28]=HOW;rec[29]=SET_KIND;rec[30]=OLD_KIND;
        identity();if(emit())return 96;pause_input();return 0;
    }
    /* Inherited FIFO gives an explicit child-exit barrier, independent of scheduling. */
    r=C(1005,"shared",0,0);if(r.error)return 95;U file=r.value;
    r=C(1005,"gate",2,0);if(r.error)return 94;U gate=r.value;
    r=C(1020,0,0,0);if(r.error)return 93;U parent=r.value;
    r=C(1002,0,0,0);reply(2,r);
    if(r.error){rec[55]=3;identity();return emit()?96:92;}
    if(r.second) {
        rec[55]=1;rec[32]=parent;
        cow=0x87654321;rec[33]=cow;
        U remove[4]={0x8000,0,0,0};reply(34,C(1164,2,remove,0));
        reply(37,C(1164,0,0,mask));for(i=0;i<4;i++)rec[40+i]=mask[i];
        B b=0;reply(44,C(1003,file,&b,1));rec[47]=b;
        identity();if(emit())return 96;pause_input();
        (void)C(1003,gate,&b,1);C(1006,file,0,0);C(1006,gate,0,0);
        return EXIT_CODE;
    }
    U child=r.value;
    rec[55]=0;rec[32]=parent;rec[33]=cow;identity();if(emit())return 96;pause_input();
    /* WNOHANG is tested while the child is provably held by the FIFO. */
    if(WAIT_OPTIONS&0x40) {
        r=call(1170,WAIT_TYPE,child,pointer(INFO_KIND,output+4),WAIT_OPTIONS,RUSAGE,0);
        reply(5,r);for(i=0;i<34;i++)rec[8+i]=word(output+4*i);
    }
    B token=1;reply(48,C(1004,gate,&token,1));
    if(!(WAIT_OPTIONS&0x40)) {
        r=call(1170,WAIT_TYPE,child,pointer(INFO_KIND,output+4),WAIT_OPTIONS,RUSAGE,0);
        reply(5,r);for(i=0;i<34;i++)rec[8+i]=word(output+4*i);
    }
    /* A normal wait both observes error-side consumption and guarantees cleanup. */
    r=call(1170,0,child,(U)(output+4),1,0,0);reply(42,r);
    B b=0;reply(45,C(1003,file,&b,1));rec[51]=b;rec[52]=cow;
    rec[53]=*(U *)0x00801ff8;rec[54]=*(U *)0x00801ffc;
    C(1006,file,0,0);C(1006,gate,0,0);
    rec[55]=2;
    rec[63]=child;identity();if(emit())return 96;
    return 0;
}
