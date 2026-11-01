/* Original pipe ABI/lifecycle measurements, independent of libc. */
typedef unsigned int U;
struct reply { U value, second, error; };
extern void probe_call(U, const U *, struct reply *);
static struct reply call(U n,U a,U b,U c,U d,U e,U f) {
    U args[6]={a,b,c,d,e,f};struct reply r;probe_call(n,args,&r);return r;
}
#define C(n,a,b,c) call(n,(U)(a),(U)(b),(U)(c),0,0,0)
static U rec[64]={0x58504950,CASE,KIND,ARG},zero[4],fds[64],info[32];
static U guard[4]={0xa5a55a5a,0x12345678,0x87654321,0x5a5aa5a5};
static char data[16];
static const char text[]="Xiri-pipe!",readonly[]="pipe does not dereference arguments";
static void reply(U at,struct reply r){rec[at]=r.value;rec[at+1]=r.second;rec[at+2]=r.error;}
static void identity(void){struct reply r=C(1024,0,0,0);rec[56]=r.value;rec[57]=r.second;r=C(1047,0,0,0);rec[58]=r.value;rec[59]=r.second;}
static void closefd(U fd){(void)C(1006,fd,0,0);}
static U equal(void){for(U i=0;i<sizeof(text);i++)if(data[i]!=text[i])return 0;return 1;}
int main(int argc,char **argv){
    if(argc>1){U uid=argv[1][0]=='1'?1234:0;
        if(C(1040,40,0,zero).error || C(1123,uid,uid,0).error || C(1124,uid,uid,0).error)return 98;
    }
    identity();struct reply r;
    U arg=ARG==1?0x80000000U:ARG==2?0xfffffffcU:ARG==3?(U)guard:ARG==4?(U)readonly:0;
    if(KIND==4)closefd(0);
    if(KIND==5){
        U n=0;
        while(n<64){r=C(1041,1,0,0);if(r.error)break;fds[n++]=r.value;}
        rec[4]=n;reply(5,r);if(n<2 || n==64)return 94;
        reply(8,C(1042,arg,0x80000000U,0xffffffffU));
        U last=fds[--n];closefd(last);rec[11]=last;
        reply(12,C(1042,arg,0x80000000U,0xffffffffU));
        r=C(1041,1,0,0);reply(15,r);if(r.error)return 93;closefd(r.value);
        U penultimate=fds[--n];closefd(penultimate);rec[18]=penultimate;
        r=C(1042,arg,0x80000000U,0xffffffffU);reply(19,r);
        if(!r.error){closefd(r.value);closefd(r.second);}
        while(n)closefd(fds[--n]);
    }else{
        r=C(1042,arg,0x80000000U,0xffffffffU);reply(4,r);
        if(!r.error){U rd=r.value,wr=r.second;
            reply(7,C(1062,rd,1,0));reply(10,C(1062,wr,1,0));
            reply(13,C(1062,rd,3,0));reply(16,C(1062,wr,3,0));
            if(KIND==0 || KIND==4){
                reply(19,C(1004,wr,text,sizeof(text)));
                reply(22,C(1003,rd,data,4));reply(25,C(1003,rd,data+4,12));rec[28]=equal();
                closefd(wr);reply(29,C(1003,rd,data,1));closefd(rd);reply(32,C(1062,rd,1,0));
            }else if(KIND==1){
                reply(19,C(1062,rd,4,0x80));reply(22,C(1062,wr,4,0x80));
                reply(25,C(1003,rd,data,1));reply(28,C(1004,rd,text,1));
                reply(31,C(1003,wr,data,1));reply(34,C(1004,wr,text,1));
                reply(37,C(1003,rd,data,1));rec[40]=(U)data[0];closefd(wr);closefd(rd);
            }else if(KIND==2){
                r=C(1041,wr,0,0);reply(19,r);if(r.error)return 92;U dup=r.value;
                closefd(wr);reply(22,C(1004,dup,text,sizeof(text)));reply(25,C(1003,rd,data,sizeof(data)));rec[28]=equal();
                closefd(dup);reply(29,C(1003,rd,data,1));closefd(rd);
            }else if(KIND==6){
                r=C(1002,0,0,0);if(r.error)return 91;
                if(r.second){closefd(rd);r=C(1004,wr,text,sizeof(text));closefd(wr);return r.error?90:37;}
                U child=r.value;closefd(wr);reply(19,C(1003,rd,data,sizeof(data)));rec[22]=equal();
                reply(23,C(1003,rd,data,1));closefd(rd);
                r=call(1170,0,child,(U)info,1,0,0);reply(26,r);
                rec[29]=info[0];rec[30]=info[1];rec[31]=info[3]==child;rec[32]=info[5];
            }else if(KIND==7){
                U mask[4]={0x1000,0,0,0};reply(19,C(1164,1,mask,0));
                closefd(rd);reply(22,C(1004,wr,text,1));closefd(wr);
            }
        }
    }
    for(U i=0;i<4;i++)rec[48+i]=guard[i];
    rec[60]=0xa5a55a5a;rec[61]=0x12345678;rec[62]=sizeof(text);rec[63]=0;
    r=C(1004,1,rec,sizeof(rec));return r.error || r.value!=sizeof(rec)?97:0;
}
