/* Original native-policy probe: invalid PRDA must fail before creating a child. */
typedef unsigned int U;
struct reply { U value,second,error; };
extern void probe_call(U,const U *,struct reply *);
static struct reply call(U n,U a,U b,U c,U d) {
    U args[6]={a,b,c,d,0,0};struct reply r;probe_call(n,args,&r);return r;
}
int main(void)
{
    U rec[8]={0x58504645,MODE},info[32];struct reply r;
    r=call(MODE?1136:1135,0x200000,4096,1,0);
    rec[2]=r.value;rec[3]=r.second;rec[4]=r.error;if(r.error)return 2;
    r=call(1002,0,0,0,0);rec[5]=r.value;rec[6]=r.second;rec[7]=r.error;
    if(!r.error){if(r.second)return 3;call(1170,0,r.value,(U)info,1);}
    r=call(1004,1,(U)rec,sizeof(rec),0);return r.error||r.value!=sizeof(rec)?4:0;
}
