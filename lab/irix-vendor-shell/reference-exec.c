/* Original reference-only credential/exec bridge; no libc or vendor code. */
typedef unsigned int U;
struct reply { U value, second, error; };
extern void probe_call(U, const U *, struct reply *);
static struct reply call(U n,U a,U b,U c) {
    U args[6]={a,b,c,0,0,0};struct reply r;probe_call(n,args,&r);return r;
}
int main(int argc,char **argv) {
    U empty=0,uid;
    if(argc<3)return 98;
    uid=argv[1][0]=='1'?1234:0;
    if(call(1040,40,0,(U)&empty).error || call(1123,uid,uid,0).error ||
        call(1124,uid,uid,0).error)return 98;
    call(1059,(U)argv[2],(U)(argv+2),(U)(argv+argc+1));
    return 99;
}
