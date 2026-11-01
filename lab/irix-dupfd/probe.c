/* Original F_DUPFD observations; explicit foreign ABI, no libc dependency. */
typedef unsigned int U;
struct reply { U value, second, error; };
extern void probe_call(U, const U *, struct reply *);
static struct reply call(U n,U a,U b,U c) {
    U args[6]={a,b,c,0,0,0};struct reply r;probe_call(n,args,&r);return r;
}
#define C(n,a,b,c) call(n,(U)(a),(U)(b),(U)(c))
static U rec[64]={0x58445550,CASE,KIND,ARG},zero[4],fds[64];
static char byte;
static void reply(U at,struct reply r){rec[at]=r.value;rec[at+1]=r.second;rec[at+2]=r.error;}
static void closefd(U fd){(void)C(1006,fd,0,0);}
static void readone(U at,U fd){byte=0;reply(at,C(1003,fd,&byte,1));rec[at+3]=(U)byte;}
static void identity(void){struct reply r=C(1024,0,0,0);rec[56]=r.value;rec[57]=r.second;r=C(1047,0,0,0);rec[58]=r.value;rec[59]=r.second;}
int main(int argc,char **argv){
    int helper=argc>1 && argv[1][0]=='h';
    if(argc>1 && !helper){U uid=argv[1][0]=='1'?1234:0;
        if(C(1040,40,0,zero).error || C(1123,uid,uid,0).error || C(1124,uid,uid,0).error)return 98;
    }
    identity();struct reply r;U output=1;
    if(helper){
        reply(4,C(1062,3,1,0));reply(7,C(1062,8,1,0));
        readone(10,8);reply(14,C(1062,8,3,0));closefd(8);
    }else if(KIND==2){
        reply(4,C(1062,0xffffffffU,0,ARG));
        r=C(1041,1,0,0);reply(7,r);if(!r.error)closefd(r.value);
    }else if(KIND==5){
        /* Preserve the observation channel before closing stdout/stderr. */
        r=C(1041,1,0,0);if(r.error)return 96;output=r.value;
        r=C(1042,0,0,0);reply(4,r);if(r.error)return 95;U rd=r.value,wr=r.second;
        reply(7,C(1062,wr,2,1));closefd(ARG);
        r=C(1062,wr,0,ARG);reply(10,r);if(r.error)return 94;U copy=r.value;
        reply(13,C(1062,copy,1,0));reply(16,C(1062,wr,1,0));
        closefd(wr);reply(19,C(1004,copy,"Q",1));readone(22,rd);
        closefd(copy);readone(26,rd);closefd(rd);
    }else{
        r=C(1005,"data",2,0);reply(4,r);if(r.error)return 93;U source=r.value;
        if(KIND==0){
            reply(7,C(1062,source,2,1));r=C(1062,source,0,ARG);reply(10,r);
            if(!r.error){U copy=r.value;
                reply(13,C(1062,source,1,0));reply(16,C(1062,copy,1,0));
                readone(19,source);readone(23,copy);readone(27,source);
                reply(31,C(1062,copy,4,0x8));reply(34,C(1062,source,3,0));
                reply(37,C(1062,copy,2,1));reply(40,C(1062,source,2,0));
                reply(43,C(1062,copy,1,0));reply(46,C(1062,source,1,0));
                closefd(source);readone(49,copy);closefd(copy);
            }else{
                reply(13,C(1062,source,1,0));readone(19,source);
                r=C(1041,source,0,0);reply(23,r);if(!r.error)closefd(r.value);closefd(source);
            }
        }else if(KIND==1){
            r=C(1041,source,0,0);if(r.error)return 92;U hole=r.value;
            r=C(1041,source,0,0);if(r.error)return 91;U occupied=r.value;
            closefd(hole);r=C(1062,source,0,hole);reply(7,r);if(r.error)return 90;U copy=r.value;
            reply(10,C(1062,occupied,1,0));readone(13,occupied);readone(17,copy);
            closefd(copy);closefd(occupied);closefd(source);
        }else if(KIND==3){
            closefd(source);reply(7,C(1062,source,0,ARG));
            r=C(1041,1,0,0);reply(10,r);if(!r.error)closefd(r.value);
        }else if(KIND==4){
            U n=0;while(n<64){r=C(1062,source,0,0);if(r.error)break;fds[n++]=r.value;}
            rec[7]=n;reply(8,r);if(n==0 || n==64)return 89;
            reply(11,C(1062,source,0,32));reply(14,C(1062,0xffffffffU,0,0));
            U last=fds[--n];rec[17]=last;closefd(last);
            r=C(1062,source,0,0);reply(18,r);if(r.error)return 88;
            closefd(r.value);readone(21,source);
            while(n)closefd(fds[--n]);
            closefd(source);
            r=C(1041,1,0,0);reply(25,r);if(!r.error)closefd(r.value);
        }else if(KIND==6){
            if(C(1062,source,2,1).error)return 87;
            r=C(1062,source,0,8);if(r.error || r.value!=8)return 86;
            char *av[]={HELPER,"helper",(char *)0};char *ev[]={(char *)0};
            (void)C(1059,HELPER,av,ev);return 85;
        }
    }
    rec[60]=0xa5a55a5a;rec[61]=0x12345678;
    r=C(1004,output,rec,sizeof(rec));return r.error || r.value!=sizeof(rec)?97:0;
}
