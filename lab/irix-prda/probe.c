/* Original PRDA lifecycle fixture. Each atomic record is 96 big-endian words. */
typedef unsigned int U;
typedef unsigned char B;
struct reply { U value,second,error; };
extern void probe_call(U,const U *,struct reply *);
static struct reply call(U n,U a,U b,U c,U d) {
    U args[6]={a,b,c,d,0,0};struct reply r;probe_call(n,args,&r);return r;
}
#define C(n,a,b,c,d) call(n,(U)(a),(U)(b),(U)(c),(U)(d))
static U rec[96],zero[4],mask[4],waitinfo[32];
static volatile B *const area=(volatile B *)0x200000;
static volatile U *const sys=(volatile U *)0x200e00;
static volatile U *const user=(volatile U *)0x200f80;
static U previous,waited,branch;
static int emit(U stage) {
    for(U i=0;i<96;i++)rec[i]=0;
    rec[0]=0x58505244;rec[1]=KIND;rec[2]=stage;
    struct reply r=C(1040,22,11,0,0);if(r.error)return 97;rec[3]=r.value;
    r=C(1020,0,0,0,0);if(r.error)return 96;rec[4]=r.value;rec[5]=r.second;
    r=C(1024,0,0,0,0);rec[6]=r.value;rec[7]=r.second;
    r=C(1047,0,0,0,0);rec[8]=r.value;rec[9]=r.second;
    for(U i=0;i<4096;i++)if((i<0xe00 || (i>=0xe80 && i<0xf80)) && area[i]) {
        if(!rec[10]){rec[11]=i;rec[12]=area[i];}rec[10]++;
    }
    if(rec[3]==8192)for(U i=4096;i<8192;i++)if(area[i])rec[13]++;
    rec[14]=waited;rec[15]=branch;rec[20]=previous;
    r=C(1164,0,0,mask,0);if(r.error)return 95;
    for(U i=0;i<4;i++)rec[16+i]=mask[i];
    for(U i=0;i<32;i++){rec[32+i]=sys[i];rec[64+i]=user[i];}
    r=C(1004,1,rec,sizeof(rec),0);return r.error||r.value!=sizeof(rec)?94:0;
}
int main(int argc,char **argv) {
    struct reply r;
    int resumed=argc>2 && argv[2][0]=='E';
    if(argc>1 && !resumed) {
        U uid=argv[1][0]=='1'?1234:0;
        if(C(1040,40,0,zero,0).error||C(1123,uid,uid,0,0).error||C(1124,uid,uid,0,0).error)return 98;
    }
    if(resumed)return emit(3);
    if(KIND==1)user[0]=0x11223344;
    if(emit(0))return 93;
    if(KIND==0){previous=user[0];user[0]=0x55667788;return emit(1);}
    if(KIND==1) {
        r=C(1002,0,0,0,0);if(r.error)return 92;branch=r.second;
        if(r.second){previous=user[0];user[0]=0x55667788;if(emit(2))return 91;return 37;}
        U child=r.value;r=C(1170,0,child,waitinfo,1);if(r.error)return 90;
        waited=r.second;return emit(1);
    }
    if(KIND==2) {
        user[0]=0x11223344;sys[0]=0xaabbccdd;
        U av[4]={(U)argv[0],(U)(argc>1?argv[1]:"0"),(U)"E",0},ev[1]={0};
        C(1059,argv[0],av,ev,0);return 89;
    }
    U block[4]={0x8000,0,0,0};if(C(1164,3,block,0,0).error)return 88;
    return emit(4);
}
