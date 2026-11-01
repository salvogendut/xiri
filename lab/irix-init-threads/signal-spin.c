/* A real asynchronous signal must consult a PRDA mask changed without a trap. */
typedef unsigned int U;
struct reply { U value, second, error; };
extern void probe_call(U, const U *, struct reply *);
static struct reply call(U n, U a, U b, U c) {
    U args[6]={a,b,c,0,0,0};struct reply r;probe_call(n,args,&r);return r;
}
#define C(n,a,b,c) call(n,(U)(a),(U)(b),(U)(c))
static volatile U spinning;
int main(void) {
    U mask[4]={0x4000,0,0,0},ready=0x58505453,token=0;
    if(MODE && C(1164,1,mask,0).error)return 90;
    if(C(1130,20,0,0).error)return 91;
    struct reply r=C(1004,1,&ready,4);
    if(r.error || r.value!=4)return 92;
    r=C(1003,0,&token,1);
    if(r.error || r.value!=1)return 93;
    *(volatile U *)0x200e74=MODE?0:0x4000;
    for(;;)spinning++;
}
