/* Original pathname and process-group measurements for both IRIX ABIs. */
typedef unsigned int U;
struct reply { U value, second, error; };
extern void probe_call(U,const U *,struct reply *);
static U rec[128]={0x58534850,KIND},used=8;
static struct reply call(U n,U a,U b,U c) {
    U args[6]={a,b,c,0,0,0};struct reply r;probe_call(n,args,&r);return r;
}
#define C(n,a,b,c) call(n,(U)(a),(U)(b),(U)(c))
static void record(struct reply r){rec[used++]=r.value;rec[used++]=r.second;rec[used++]=r.error;}
static void token(void) {
    U data=0;struct reply r=C(1005,"token",0,0);record(r);
    if(!r.error){U fd=r.value;record(C(1003,fd,&data,4));record(C(1006,fd,0,0));}
    else{record((struct reply){0,0,0});record((struct reply){0,0,0});}
    rec[used++]=data;
}
int main(int argc,char **argv) {
    struct reply r;U zero=0;
    if(argc>1 && argv[1][0]!='n') {
        U uid=argv[1][0]=='1'?1234:0;
        if(C(1040,40,0,&zero).error || C(1123,uid,uid,0).error ||
            C(1124,uid,uid,0).error)return 98;
    }
    r=C(1020,0,0,0);rec[2]=r.value;rec[3]=r.second;
    r=C(1024,0,0,0);rec[4]=r.value;rec[5]=r.second;
    if(KIND==0) {
        record(C(1012,"/tmp/xiri-vendor-shell/cwd",0,0));token();
        record(C(1012,"missing",0,0));token();
        record(C(1012,"token",0,0));token();
        record(C(1012,0,0,0));record(C(1012,0x80000000,0,0));
        record(C(1012,0xfffffffe,0,0));token();
        record(C(1012,"sub",0,0));record(C(1012,"..",0,0));token();
        record(C(1012,"link",0,0));record(C(1012,"..",0,0));token();
        record(C(1012,"denied",0,0));
        record(C(1012,"/tmp/xiri-vendor-shell/cwd",0,0));token();
    } else {
        record(C(1040,65,0,0));
        record(C(1039,0,0,0));record(C(1039,2,0,0));record(C(1039,4,0,0));
        if(KIND==1) {
            record(C(1039,1,0,0));record(C(1039,0,0,0));
            record(C(1039,2,0,0));record(C(1039,4,0,0));
            record(C(1039,1,0,0));record(C(1039,3,0,0));
            record(C(1039,5,0,0));
        } else if(KIND==2) {
            record(C(1039,5,0,0));record(C(1039,0,0,0));
            record(C(1039,2,0,0));record(C(1039,1,0,0));
            record(C(1039,2,0,0));record(C(1039,4,0,0));
        } else if(KIND==3) {
            record(C(1039,3,0,0));record(C(1039,0,0,0));
            record(C(1039,2,0,0));record(C(1039,1,0,0));
            record(C(1039,3,0,0));
        } else {
            record(C(1039,6,0,0));record(C(1039,0xffffffff,0,0));
            record(C(1039,2,0x7fffffff,0));record(C(1039,4,0x7fffffff,0));
            record(C(1039,5,0xffffffff,0));record(C(1039,5,0,0xffffffff));
            record(C(1039,5,0x7fffffff,0));
        }
    }
    if(KIND!=0)record(C(1040,65,0,0));
    rec[6]=used;
    r=C(1004,1,rec,sizeof(rec));return r.error || r.value!=sizeof(rec)?97:0;
}
