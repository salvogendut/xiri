typedef unsigned int U;
struct reply {U value,second,error;};
extern void probe_call(U,const U *,struct reply *);
static U rec[640],info[32],zero[4];
static struct reply call(U n,U a,U b,U c,U d,U e,U f){U v[6]={a,b,c,d,e,f};struct reply r;probe_call(n,v,&r);return r;}
#define C(n,a,b,c) call(n,(U)(a),(U)(b),(U)(c),0,0,0)
int main(int argc,char **argv){
 U sig=argc>1?(argv[1][0]=='1'?24:argv[1][0]=='2'?26:23):23;
 if(argc>2){U uid=argv[2][0]=='1'?1234:0;if(C(1040,40,0,zero).error||C(1123,uid,uid,0).error||C(1124,uid,uid,0).error)return 91;}
 struct reply r=C(1024,0,0,0);rec[2]=r.value;rec[3]=r.second;r=C(1047,0,0,0);rec[4]=r.value;rec[5]=r.second;
 rec[0]=0x58574f50;rec[1]=sig;rec[6]=C(1020,0,0,0).value;
 r=C(1042,0,0,0);if(r.error)return 90;U rd=r.value,wr=r.second;
 r=C(1002,0,0,0);if(r.error)return 92;
 if(r.second){C(1006,wr,0,0);r=C(1040,21,0,0);if(r.error)return 93;C(1037,C(1020,0,0,0).value,sig,0);C(1003,rd,info,1);return 37;}
 U pid=r.value;rec[7]=pid;C(1006,rd,0,0);
 r=call(1170,0,pid,(U)info,4|128,0,0);rec[8]=r.value;rec[9]=r.error;rec[10]=info[1];rec[11]=info[5];
 for(U i=0;i<16;i++){U at=32+i*36;rec[at+3]=i|64|128;r=call(1170,7,0,(U)(rec+at+4),i|64|128,0,0);rec[at]=r.value;rec[at+1]=r.second;rec[at+2]=r.error;}
 C(1037,pid,25,0);C(1006,wr,0,0);r=call(1170,0,pid,(U)info,1,0,0);rec[12]=r.value;rec[13]=r.error;rec[14]=info[1];rec[15]=info[5];
 r=C(1004,1,rec,sizeof(rec));return r.error||r.value!=sizeof(rec);
}
