/* Original descriptor/session/exec probes; no vendor source or libc. */
typedef unsigned int U;
typedef unsigned char B;
struct reply { U value, second, error; };
extern void probe_call(U, const U *, struct reply *);
static struct reply call(U n,U a,U b,U c) {
    U args[6]={a,b,c,0,0,0};struct reply r;probe_call(n,args,&r);return r;
}
#define C(n,a,b,c) call(n,(U)(a),(U)(b),(U)(c))
static U rec[64]={0x5853484c,CASE},zero[4];
static B unaligned[64];
static void reply(U at,struct reply r){rec[at]=r.value;rec[at+1]=r.second;rec[at+2]=r.error;}
static void identity(void) {
    struct reply r=C(1024,0,0,0);rec[56]=r.value;rec[57]=r.second;
    r=C(1047,0,0,0);rec[58]=r.value;rec[59]=r.second;
    r=C(1020,0,0,0);rec[60]=r.value;rec[61]=r.second;rec[62]=r.error;
}
static void put(B *p,U v){p[0]=v>>24;p[1]=v>>16;p[2]=v>>8;p[3]=v;}
int main(int argc,char **argv) {
    struct reply r;
    if(argc>1) {
        U uid=argv[1][0]=='1'?1234:0;
        if(C(1040,40,0,zero).error||C(1123,uid,uid,0).error||C(1124,uid,uid,0).error)return 98;
        r=C(1040,41,0,zero);if(r.error||r.value)return 98;
    }
    if(KIND==0) {
        reply(2,C(1040,109,0,0));reply(5,C(1063,4,0,0));
        r=C(1005,"shared",0,0);reply(8,r);if(r.error)return 94;U fd=r.value;
        r=C(1041,fd,0,0);reply(11,r);if(r.error)return 94;U a=r.value;
        r=C(1041,fd,0,0);reply(14,r);if(r.error)return 94;U b=r.value;
        reply(17,C(1040,109,0,0));reply(20,C(1006,a,0,0));
        reply(23,C(1040,109,0,0));reply(26,C(1006,b,0,0));
        reply(29,C(1040,109,0,0));reply(32,C(1006,fd,0,0));
        reply(35,C(1040,109,0,0));reply(38,C(1041,0xffffffff,0,0));
        reply(41,C(1063,0,0,0));reply(44,C(1040,20,0,0));
        reply(47,C(1040,20,0,0));reply(50,C(1020,0,0,0));
    } else {
        static char command[]="printf 'XIRI_EXEC|%s|%s|%s|%s\\n' \"$0\" \"$1\" \"$2\" \"$XIRI_EXEC_ENV\"; exit 37";
        U av[7]={(U)"xiri-sh",(U)"-c",(U)command,(U)"xiri argv0",(U)"two words",(U)"",0};
        U ev[2]={(U)"XIRI_EXEC_ENV=alpha beta",0};
        U path=(U)"/bin/sh",argp=(U)av,envp=(U)ev;
        if(PATH_MODE==1)path=(U)"/xiri-no-such-executable";
        if(PATH_MODE==2)path=(U)"shared";
        if(PATH_MODE==3)path=(U)".";
        if(PATH_MODE==4)path=0;
        if(PATH_MODE==5)path=0x80000000;
        if(PATH_MODE==6)path=0xfffffffe;
        if(PATH_MODE==7){path=0x801ff8;*(U *)path=0x78787878;*(U *)(path+4)=0x78787878;}
        if(ARG_MODE==1)argp=0;
        if(ARG_MODE==2)argp=0x80000000;
        if(ARG_MODE==3)av[1]=0x80000000;
        if(ARG_MODE==4){for(U i=0;i<7;i++)put(unaligned+1+4*i,av[i]);argp=(U)(unaligned+1);}
        if(ARG_MODE==5){argp=0x801ffc;*(U *)argp=av[0];}
        if(ENV_MODE==1)envp=0;
        if(ENV_MODE==2)envp=0x80000000;
        if(ENV_MODE==3)ev[0]=0x80000000;
        if(ENV_MODE==4){for(U i=0;i<2;i++)put(unaligned+1+4*i,ev[i]);envp=(U)(unaligned+1);}
        if(ENV_MODE==5){envp=0x801ffc;*(U *)envp=ev[0];}
        reply(2,C(1059,path,argp,envp));
        rec[28]=KIND;rec[29]=PATH_MODE;rec[30]=ARG_MODE;rec[31]=ENV_MODE;
    }
    identity();r=C(1004,1,rec,sizeof(rec));return r.error||r.value!=sizeof(rec)?96:0;
}
