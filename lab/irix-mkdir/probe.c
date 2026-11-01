/* Original mkdir measurements: fixed-width records, no libc or shared state. */
typedef unsigned int U;
struct reply { U value, second, error; };
extern void probe_call(U, const U *, struct reply *);
static struct reply call(U n,U a,U b,U c) {
    U args[6]={a,b,c,0,0,0};struct reply r;probe_call(n,args,&r);return r;
}
#define C(n,a,b,c) call(n,(U)(a),(U)(b),(U)(c))
static U rec[32],st[40],zero[4];
static char component[262],longpath[1025];
struct test { const char *path; U mode; };
static const struct test tests[]={
    {"data/simple",0755},{"data/zero",0},{"data/special",07777},
    {"data/perms",0777},{"data/typebits",0100755},{"data/negative",0xffffffffU},
    {"data/highbit",0x800001edU},{"data/exists",0755},{"data/file",0755},
    {"data/linkdir",0755},{"data/dangling",0755},{"data/linkparent/new",0755},
    {"data/missing/new",0755},{"data/file/new",0755},{"data/nosearch/new",0755},
    {"data/nowrite/new",0755},{"data/group/new",0755},{"data/owner/new",0755},
    {"data/sgid/new",0755},{"data/trailing/",0755},{"data/file/",0755},
    {".",0755},{"",0755},{(void *)0,0755},{(void *)0x80000000U,0755},
    {component,0755},{longpath,0755},{(void *)0x00801ff8U,0755},
    {(void *)0x00801ff6U,0755},{"data/loop-a/new",0755},
    {"/tmp/xiri-mkdir-native/new",0755},{"/tmp/xiri-mkdir-shadow/new",0755}
};
static void reply(U at,struct reply r){rec[at]=r.value;rec[at+1]=r.second;rec[at+2]=r.error;}
static void ids(U at){struct reply r=C(1024,0,0,0);rec[at]=r.value;rec[at+1]=r.second;r=C(1047,0,0,0);rec[at+2]=r.value;rec[at+3]=r.second;}
int main(int argc,char **argv){
    static const U identities[][4]={{0,0,0,0},{1234,1234,1234,1234},{0,1234,0,1234},{1234,0,1234,0},{1234,1234,5678,5678}};
    if(argc>1){
        U i=(U)(argv[1][0]-'0');if(i>=5)return 99;
        const U *id=identities[i];
        if(C(1040,40,0,zero).error || C(1123,id[2],id[3],0).error || C(1124,id[0],id[1],0).error)return 98;
        struct reply r=C(1040,41,0,zero);if(r.error || r.value)return 98;
    }
    for(U i=0;i<5;i++)component[i]="data/"[i];
    for(U i=5;i<261;i++)component[i]='x';
    component[261]=0;
    for(U i=0;i<1024;i++)longpath[i]=(i&1)?'/':'.';
    longpath[1024]=0;
    for(U n=0;n<sizeof(tests)/sizeof(tests[0]);n++){
        for(U i=0;i<32;i++)rec[i]=0;
        for(U i=0;i<40;i++)st[i]=0xa5a5a5a5;
        for(U i=0;i<8;i++)((volatile char *)0x00801ff8U)[i]='x';
        if(n==28)for(U i=0;i<10;i++)((volatile char *)0x00801ff6U)[i]="data/edge"[i];
        rec[0]=0x584d4b44;rec[1]=n;rec[2]=MASK;rec[3]=tests[n].mode;ids(4);
        reply(8,C(1080,tests[n].path,tests[n].mode,0));
        struct reply r=C(1158,3,tests[n].path,st);reply(11,r);
        if(!r.error){rec[14]=st[6];rec[15]=st[8];rec[16]=st[9];}
        ids(17);rec[30]=0xa5a55a5a;rec[31]=0x12345678;
        r=C(1004,1,rec,sizeof(rec));if(r.error || r.value!=sizeof(rec))return 97;
    }
    return 0;
}
