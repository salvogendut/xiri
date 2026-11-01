/* Original AUTORESRV and mmap regression fixtures: explicit 32-bit words, no vendor libc or source. */
typedef unsigned int U;
typedef unsigned char B;
struct reply { U value, second, error; };
extern void probe_call(U,const U *,struct reply *);
static struct reply call(U n,U a,U b,U c,U d,U e,U f) {
    U args[6]={a,b,c,d,e,f};struct reply r;probe_call(n,args,&r);return r;
}
#define C(n,a,b,c,d,e,f) call(n,(U)(a),(U)(b),(U)(c),(U)(d),(U)(e),(U)(f))
static U rec[64]={0x584d4c43,CASE},zero[4],waitinfo[32];
static void reply(U at,struct reply r){rec[at]=r.value;rec[at+1]=r.second;rec[at+2]=r.error;}
int main(int argc,char **argv) {
    struct reply r;
    if(argc>1) {
        U uid=argv[1][0]=='1'?1234:0;
        if(C(1040,40,0,zero,0,0,0).error||C(1123,uid,uid,0,0,0,0).error||C(1124,uid,uid,0,0,0,0).error)return 98;
    }
    r=C(1040,22,11,0,0,0,0);if(r.error)return 97;U page=r.value;rec[5]=page;
    r=C(1005,FILE_KIND==1?"mapping":FILE_KIND==3?"writable":FILE_KIND==2?".":"/dev/zero",FD_MODE==2?1:FD_MODE==4?2:0,0,0,0,0);
    if(r.error)return 96;
    U fd=r.value;
    volatile B *occupied=(volatile B *)0x0e100000;
    if(REPLACE) {
        r=C(1005,"/dev/zero",0,0,0,0,0);if(r.error)return 95;U zfd=r.value;
        r=C(1134,occupied,0x4000,3,2,zfd,0);if(r.error||r.value!=(U)occupied)return 94;
        if(C(1006,zfd,0,0,0,0,0).error)return 93;
        occupied[0]=0x2a;occupied[0x2000]=0x77;
    }
    U mapfd=FD_MODE==1?0xffffffff:fd;
    if(FD_MODE==3){if(C(1006,fd,0,0,0,0,0).error)return 92;}
    rec[16]=ADDRESS;rec[17]=LENGTH;rec[18]=PROTECTION;rec[19]=FLAGS;rec[20]=FD_MODE;rec[21]=OFFSET;rec[22]=FILE_KIND;rec[23]=REPLACE;rec[26]=FORK;rec[27]=PROTECT;
    r=C(1134,ADDRESS,LENGTH,PROTECTION,FLAGS,mapfd,OFFSET);reply(2,r);
    if(FD_MODE!=3)reply(8,C(1006,fd,0,0,0,0,0));
    if(r.error) {
        if(REPLACE){rec[24]=occupied[0];rec[25]=occupied[0x2000];if(rec[24]!=0x2a||rec[25]!=0x77)return 91;}
    } else if(LENGTH && LENGTH<=0x200000) {
        volatile B *memory=(volatile B *)r.value;
        U rounded=(LENGTH+page-1)&~(page-1);
        if(PROTECTION&1) {
            for(U i=0;i<rounded;i++)if(memory[i]!=((FILE_KIND==1 || FILE_KIND==3)?0x3c:0))return 90;
            rec[6]|=1;
        }
        if(PROTECTION&2) {
            memory[0]=0x5a;memory[rounded-1]=0xa6;
            if(memory[0]!=0x5a||memory[rounded-1]!=0xa6)return 89;
            rec[6]|=2;
        }
        if(REPLACE){rec[24]=memory[0];rec[25]=occupied[0x2000];if(rec[25]!=0x77)return 88;rec[6]|=4;}
        if(FORK) {
            struct reply child=C(1002,0,0,0,0,0,0);if(child.error)return 86;
            if(child.second) {
                if(memory[0]!=0x5a || memory[rounded-1]!=0xa6)return 85;
                memory[0]=0x8b;memory[rounded-1]=0xc9;
                if(memory[0]!=0x8b || memory[rounded-1]!=0xc9)return 84;
                return 37;
            }
            struct reply waited=C(1170,0,child.value,waitinfo,1,0,0);
            if(waited.error || waitinfo[3]!=child.value || waitinfo[1]!=1 || waitinfo[5]!=37)return 83;
            rec[28]=waitinfo[5];rec[29]=memory[0];rec[30]=memory[rounded-1];
            if(rec[29]!=0x5a || rec[30]!=0xa6)return 82;
            rec[31]=1;
        }
        if(PROTECT) {
            struct reply changed=C(1136,r.value,LENGTH,PROTECT==1?1:0,0,0,0);
            reply(40,changed);if(changed.error)return 81;
            if(PROTECT==2) {
                changed=C(1136,r.value,LENGTH,3,0,0,0);reply(43,changed);if(changed.error)return 80;
                if(memory[0]!=0x5a || memory[rounded-1]!=0xa6)return 79;
                memory[rounded-1]=0x42;if(memory[rounded-1]!=0x42)return 78;
            }
        }
        if(!FAULT)reply(36,C(1135,r.value,LENGTH,0,0,0,0));
    }
    r=C(1024,0,0,0,0,0,0);rec[56]=r.value;rec[57]=r.second;
    r=C(1047,0,0,0,0,0,0);rec[58]=r.value;rec[59]=r.second;
    r=C(1004,1,rec,sizeof(rec),0,0,0);if(r.error||r.value!=sizeof(rec))return 87;
    if(FAULT && !rec[4])*(volatile U *)rec[2]=0x11223344;
    return 0;
}
