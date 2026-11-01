/* Original PR_INIT_THREADS measurements; explicit 32-bit records, no libc. */
typedef unsigned int U;
struct reply { U value, second, error; };
extern void probe_call(U, const U *, struct reply *);
static struct reply call(U n, U a, U b, U c, U d) {
    U args[6] = {a,b,c,d,0,0}; struct reply r;
    probe_call(n,args,&r); return r;
}
#define C(n,a,b,c,d) call(n,(U)(a),(U)(b),(U)(c),(U)(d))
static U rec[96], zero[4], mask[4], waitinfo[32];
static volatile U *const sys = (volatile U *)0x200e00;
static volatile U *const user = (volatile U *)0x200f80;
static struct reply init, again;
static U parent, child, waited;
static void reply(U at, struct reply r) {
    rec[at]=r.value; rec[at+1]=r.second; rec[at+2]=r.error;
}
static int emit(U stage) {
    for(U i=0;i<96;i++)rec[i]=0;
    rec[0]=0x58505449; rec[1]=KIND; rec[2]=stage;
    struct reply r=C(1020,0,0,0,0); rec[3]=r.value; rec[4]=r.second;
    r=C(1024,0,0,0,0); rec[5]=r.value; rec[6]=r.second;
    r=C(1047,0,0,0,0); rec[7]=r.value; rec[8]=r.second;
    reply(9,init); reply(12,again);
    /* Snapshot PRDA before the explicit mask query can alter it. */
    for(U i=0;i<32;i++) { rec[32+i]=sys[i]; rec[64+i]=user[i]; }
    r=C(1164,0,0,mask,0); reply(15,r);
    for(U i=0;i<4;i++)rec[18+i]=mask[i];
    rec[22]=parent; rec[23]=child; rec[24]=waited;
    reply(25,C(1130,14,0,0,0));
    reply(28,C(1130,13,0,0,0));
    r=C(1004,1,rec,sizeof(rec),0);
    return r.error || r.value!=sizeof(rec) ? 97 : 0;
}
int main(int argc, char **argv) {
    int resumed=argc>2 && argv[2][0]=='E';
    if(argc>1 && !resumed) {
        U uid=argv[1][0]=='1'?1234:0;
        if(C(1040,40,0,zero,0).error || C(1123,uid,uid,0,0).error ||
           C(1124,uid,uid,0,0).error)return 98;
    }
    if(resumed) {
        if(emit(5))return 96;
        init=C(1130,20,0,0,0);
        return emit(6);
    }
    if(KIND==2 || KIND==3 || KIND==4 || KIND>=7) {
        U block[4]={0x8000,0,0,0};
        if(C(1164,3,block,0,0).error)return 95;
    }
    if(KIND==5) { sys[16]=0x12345678; user[0]=0x55667788; }
    if(KIND==7) { sys[27]=0x80000004;sys[28]=0x11223344;sys[29]=0x55667788; }
    if(KIND==8) { sys[27]=1;sys[28]=0;sys[29]=0x4000; }
    if(emit(0))return 94;
    if(KIND==9 || KIND==10) {
        struct reply r=C(1136,0x200000,4096,KIND==9?1:0,0);
        if(r.error)return 87;
        init=C(1130,20,0,0,0);
        /* Restore read/write before observing the result. */
        if(C(1136,0x200000,4096,3,0).error)return 86;
        return emit(1);
    }
    init=C(1130,20,KIND==1?0xffffffff:0,KIND==1?0x80000001:0,KIND==1?0x12345678:0);
    if(emit(1))return 93;
    if(KIND==3) {
        parent=C(1020,0,0,0,0).value;
        struct reply r=C(1002,0,0,0,0);
        if(r.error){again=r; return emit(7);}
        if(r.second) {
            if(emit(3))return 92;
            again=C(1130,20,0,0,0);
            if(emit(4))return 91;
            return 37;
        }
        child=r.value;
        r=C(1170,0,child,waitinfo,1);
        if(r.error || waitinfo[3]!=child || waitinfo[1]!=1 || waitinfo[5]!=37)return 90;
        waited=waitinfo[5];
    }
    if(KIND==4) {
        user[0]=0xaabbccdd;
        U av[4]={(U)argv[0],(U)(argc>1?argv[1]:"0"),(U)"E",0},ev[1]={0};
        C(1059,argv[0],av,ev,0);return 89;
    }
    if(KIND==6) {
        /* Both ABIs on this reference kernel use the low second word. */
        sys[28]=0;sys[29]=0x4000;
        if(emit(8))return 88;
    }
    if(KIND==11) {
        sys[27]=0;sys[28]=0;sys[29]=0x4000;
        if(emit(8))return 85;
    }
    if(KIND==12) {
        U block[4]={0x4000,0,0,0};
        if(C(1164,3,block,0,0).error)return 84;
        if(emit(8))return 83;
    }
    again=C(1130,20,0,0,0);
    return emit(2);
}
