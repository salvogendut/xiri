/* Original read-only rlimit ABI/lifecycle probe; 32 big-endian words/record. */
typedef unsigned int U;
struct reply { U value, second, error; };
extern void probe_call(U, const U *, struct reply *);
static struct reply call(U n, U a, U b, U c, U d) {
    U args[6] = {a,b,c,d,0,0}; struct reply r;
    probe_call(n,args,&r); return r;
}
#define C(n,a,b,c,d) call(n,(U)(a),(U)(b),(U)(c),(U)(d))
static U rec[32], buffer[8], zero[4], waitinfo[32];
static U identity[4], page;
static int query(U stage, U wide, U resource, U pointer) {
    for(U i=0;i<32;i++) rec[i]=0;
    for(U i=0;i<8;i++) buffer[i]=0xa5a5a5a5;
    U address=(U)&buffer[2];
    if(pointer==1) address=0;
    if(pointer==2) address=0x80000000;
    if(pointer==3) address=0xfffffff8;
    if(pointer==4) address=(U)probe_call;
    if(pointer==5) address++;
    struct reply r=C(wide?1075:1148,resource,address,0,0);
    rec[0]=0x58524c4d; rec[1]=KIND; rec[2]=stage; rec[3]=wide;
    rec[4]=resource; rec[5]=pointer; rec[6]=r.value; rec[7]=r.second; rec[8]=r.error;
    for(U i=0;i<4;i++) rec[9+i]=identity[i];
    r=C(1020,0,0,0,0); rec[13]=r.value; rec[14]=r.second; rec[15]=page;
    for(U i=0;i<8;i++) rec[16+i]=buffer[i];
    r=C(1004,1,rec,sizeof(rec),0);
    return r.error || r.value!=sizeof(rec);
}
static int queries(U stage) {
    for(U wide=0;wide<2;wide++)
        for(U resource=0;resource<9;resource++)
            if(query(stage,wide,resource,0)) return 90;
    return 0;
}
int main(int argc,char **argv) {
    int resumed=argc>2 && argv[2][0]=='E';
    if(argc>1 && !resumed) {
        U uid=argv[1][0]=='1'?1234:0;
        if(C(1040,40,0,zero,0).error || C(1123,uid,uid,0,0).error ||
           C(1124,uid,uid,0,0).error) return 98;
    }
    struct reply r=C(1024,0,0,0,0); identity[0]=r.value; identity[1]=r.second;
    r=C(1047,0,0,0,0); identity[2]=r.value; identity[3]=r.second;
    r=C(1040,22,11,0,0); if(r.error) return 97; page=r.value;
    if(resumed) { if(queries(2)) return 96; return 37; }
    if(KIND==3 || KIND==4) {
        U limits[4]={KIND==3?1:0,KIND==3?0x23456789:0x80000001,
                     KIND==3?2:0,KIND==3?0x3456789a:0xf1234567};
        if(C(1076,1,limits,0,0).error) return 86;
        return queries(0);
    }
    if(KIND==1) {
        const U invalid[4]={9,0xffffffff,0x80000000,0x7fffffff};
        for(U wide=0;wide<2;wide++) {
            for(U i=0;i<4;i++) if(query(0,wide,invalid[i],0)) return 95;
            for(U p=1;p<=5;p++) if(query(0,wide,8,p)) return 94;
            if(query(0,wide,9,1)) return 93;
        }
        return 0;
    }
    if(queries(0)) return 92;
    if(KIND==0) return 0;
    r=C(1002,0,0,0,0); if(r.error) return 91;
    if(r.second) {
        if(queries(1)) return 89;
        U av[4]={(U)argv[0],(U)(argc>1?argv[1]:"0"),(U)"E",0},env[1]={0};
        C(1059,argv[0],av,env,0); return 88;
    }
    U child=r.value; r=C(1170,0,child,waitinfo,1);
    if(r.error || waitinfo[3]!=child || waitinfo[1]!=1 || waitinfo[5]!=37) return 87;
    return queries(3);
}
