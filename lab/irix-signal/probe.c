/* Original signal registration/delivery observations, explicit 32-bit fields.
 * A 2048-byte record includes entry GPRs, 1024 context bytes and siginfo128.
 * No installed IRIX header, library or trampoline is linked into this probe. */
typedef unsigned int U;
typedef unsigned char B;
typedef unsigned long long Q;
struct reply { U value, second, error; };
extern void probe_call(U, const U *, struct reply *);
extern void signal_trampoline(void);
extern void signal_fpu_set(const Q *,U);
extern void signal_fpu_get(U *);
Q signal_entry[32];
static U rec[512]={0x58534947,CASE,KIND,FLAGS};
static U zero[4], baseline[4]={0x4000,0,0,0}, mask[4];
static B request[40], old[40], query[40];
static U count;
static const Q fp_seed[4]={0x1122334455667788ULL,0x1020304050607080ULL,
    0x89abcdef01234567ULL,0x8877665544332211ULL};
static const Q fp_clobber[4]={0,0,0,0};
static struct reply call(U n,U a,U b,U c,U d,U e,U f) {
    U args[6]={a,b,c,d,e,f};struct reply r;probe_call(n,args,&r);return r;
}
#define C(n,a,b,c) call(n,(U)(a),(U)(b),(U)(c),0,0,0)
static void reply(U at,struct reply r) {rec[at]=r.value;rec[at+1]=r.second;rec[at+2]=r.error;}
static void copy(B *to,const B *from,U n) {for(U i=0;i<n;i++)to[i]=from[i];}
static void put(B *p,U v) {p[0]=v>>24;p[1]=v>>16;p[2]=v>>8;p[3]=v;}
static U address(U kind,U normal,U base,U page) {
    switch(kind) {
    case 1:return 0;
    case 2:return 0x80000000U;
    case 3:return normal+1;
    case 4:return base+page-4;
    case 5:return base+page-28;
    case 6:return base;
    default:return normal;
    }
}
void signal_body(void) {
    count++;
    copy((B *)(rec+128),(const B *)signal_entry,256);
    copy((B *)(rec+192),(const B *)(U)signal_entry[6],1024);
    if((U)signal_entry[4]&0x80000000U)
        copy((B *)(rec+448),(const B *)(U)signal_entry[5],128);
    if(RETURN_TEST) {
        U sc=RETURN_TEST==1 || RETURN_TEST==4?0x80000000U:0;
        U uc=RETURN_TEST==2?0x80000000U:RETURN_TEST==4?(U)signal_entry[6]:0;
        reply(120,C(1088,sc,uc,(U)signal_entry[4]));
    }
    reply(32,C(1164,0,0,mask));for(U i=0;i<4;i++)rec[35+i]=mask[i];
    reply(39,call(1162,SIGNUM,0,(U)query,(U)signal_trampoline,0,0));
    if(REAP) {
        U info[32];for(U i=0;i<32;i++)info[i]=0xa5a5a5a5;
        reply(42,call(1170,7,0,(U)info,0x43,0,0));copy((B *)(rec+80),(B *)info,128);
    }
    /* A real sigreturn must undo this handler-local mask change. */
    U change[4]={0x10000,0,0,0};reply(45,C(1164,1,change,0));
    if(FPU)signal_fpu_set(fp_clobber,3);
}
int main(int argc,char **argv) {
    if(argc>1) {U uid=argv[1][0]=='1'?1234:0;
        if(C(1040,40,0,zero).error || C(1123,uid,uid,0).error || C(1124,uid,uid,0).error)return 98;
    }
    struct reply r=C(1024,0,0,0);rec[4]=r.value;rec[5]=r.second;
    r=C(1047,0,0,0);rec[6]=r.value;rec[7]=r.second;
    r=C(1020,0,0,0);rec[8]=r.value;rec[9]=r.second;
    if(C(1164,3,baseline,0).error)return 97;
    U page=C(1056,14,0,0).value;
    r=C(1005,"/dev/zero",2,0);if(r.error)return 96;U fd=r.value;
    r=call(1134,0,2*page,3,0x102,fd,0);if(r.error)return 95;U base=r.value;
    for(U i=0;i<40;i++)request[i]=old[i]=query[i]=0xa5;
    for(U i=0;i<page;i++)((B *)base)[i]=0x5a;
    B *req=request+4+(SET_KIND==3);
    put(req,FLAGS);put(req+4,HANDLER==3?(U)signal_body:HANDLER);
    put(req+8,MASK0);put(req+12,MASK1);put(req+16,MASK2);put(req+20,MASK3);
    put(req+24,0x12345678);put(req+28,0x87654321);
    if(SET_KIND==4 || SET_KIND==5 || SET_KIND==6) {
        U dest=address(SET_KIND,(U)(request+4),base,page);
        U bytes=SET_KIND==4?4:SET_KIND==5?28:32;
        copy((B *)dest,req,bytes);
    }
    if(C(1136,base+page,page,0).error)return 94;
    if((SET_KIND==6 || OLD_KIND==6) && C(1136,base,page,1).error)return 93;
    rec[10]=SIGNUM;rec[11]=(U)signal_body;rec[12]=(U)signal_trampoline;
    rec[13]=page;rec[14]=base;
    reply(16,call(1162,SIGNUM,address(SET_KIND,(U)(request+4),base,page),
         address(OLD_KIND,(U)(old+4),base,page),TRAMP==1?0:TRAMP==2?0x80000000U:(U)signal_trampoline,0,0));
    copy((B *)(rec+64),old,40);
    copy((B *)(rec+112),(B *)(base+page-32),32);
    reply(19,call(1162,SIGNUM,0,(U)(query+4),(U)signal_trampoline,0,0));
    copy((B *)(rec+480),query,40);
    if(KIND && rec[18]==0) {
        if(FPU) {signal_fpu_set(fp_seed,2);signal_fpu_get(rec+490);}
        if(KIND==1)reply(22,C(1037,rec[8],SIGNUM,0));
        else {
            U block[4]={1U<<((SIGNUM-1)&31),0,0,0};
            if(C(1164,1,block,0).error)return 92;
            r=C(1002,0,0,0);if(r.error)return 91;
            if(r.second) {C(1001,37,0,0);return 90;}
            rec[25]=r.value;U info[32];
            reply(26,call(1170,0,r.value,(U)info,0x81,0,0));
            reply(22,C(1164,2,block,0));
            reply(29,call(1170,0,rec[25],(U)info,1,0,0));
        }
    }
    if(FPU)signal_fpu_get(rec+500);
    rec[509]=FPU;
    rec[510]=RETURN_TEST;
    rec[15]=count;
    reply(48,C(1164,0,0,mask));for(U i=0;i<4;i++)rec[51+i]=mask[i];
    copy((B *)(rec+56),query,32);
    r=C(1004,1,rec,sizeof(rec));return r.error || r.value!=sizeof(rec)?88:0;
}
