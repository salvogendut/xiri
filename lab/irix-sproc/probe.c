/* Original, libc-free IRIX share-process observations. All records are BE32. */
typedef unsigned int U;
struct reply { U value, second, error; };
extern void probe_call(U, const U *, struct reply *);
extern void spawn_call(U, const U *, struct reply *);
extern void child_entry(void);
U entry_regs[12];
void *memset(void *p, int value, U length) {
    volatile unsigned char *q=p;
    for(U i=0;i<length;i++)q[i]=(unsigned char)value;
    return p;
}
static struct reply call(U n, U a, U b, U c, U d, U e, U f) {
    U args[6]={a,b,c,d,e,f}; struct reply r; probe_call(n,args,&r); return r;
}
#define C(n,a,b,c,d,e,f) call(n,(U)(a),(U)(b),(U)(c),(U)(d),(U)(e),(U)(f))
#define PRDA_PID (*(volatile U *)0x200e00)
#define PRDA_USER (*(volatile U *)0x200100)
static volatile U shared_word=0x11223344;
static volatile U new_mapping;
static U zero[4], info[32];
struct argument { U parent, fd; volatile U word; U local; U stack_top; };
static void reply(U *p, struct reply r) { p[0]=r.value;p[1]=r.second;p[2]=r.error; }
static void identity(U *p) {
    struct reply r=C(1024,0,0,0,0,0,0);p[0]=r.value;p[1]=r.second;
    r=C(1047,0,0,0,0,0,0);p[2]=r.value;p[3]=r.second;
}
static int emit(U *rec) {
    struct reply r=C(1004,1,rec,256,0,0,0);
    return r.error || r.value!=256;
}
int child_main(struct argument *arg) {
    U rec[64]={0x58535052,CASE,1,FLAGS,ACTION,TRAP};
    for(U i=0;i<12;i++)rec[8+i]=entry_regs[i];
    rec[6]=C(1020,0,0,0,0,0,0).value;rec[7]=arg->parent;
    rec[20]=PRDA_PID;rec[21]=PRDA_USER;PRDA_USER=0xcacacaca;
    rec[22]=shared_word;shared_word=0x55667788;
    rec[23]=arg->word;arg->word=0xabcdef01;
    reply(rec+24,C(1130,2,arg->parent,0,0,0,0));
    reply(rec+27,C(1130,14,0,0,0,0,0));
    reply(rec+30,C(1130,13,arg->parent,0,0,0,0));
    if(ACTION==6) {
        struct reply r=C(1134,0,8192,3,0x102,arg->fd,0);reply(rec+48,r);
        if(!r.error){*(volatile U *)r.value=0xdecaf123;new_mapping=r.value;}
    }
    reply(rec+33,C(1006,arg->fd,0,0,0,0,0));
    if(arg->local) {
        rec[36]=*(volatile U *)arg->local;
        *(volatile U *)arg->local=0x76543210;
    }
    rec[37]=arg->stack_top;
    if(ACTION==2 || ACTION==3 || ACTION==4)
        reply(rec+38,C(1130,6,arg->parent,0,0,0,0));
    if(ACTION==3) {
        const char *av[]={"missing",0};
        reply(rec+41,C(1059,"./xiri-sproc-missing",av,zero,0,0,0));
        reply(rec+44,C(1130,2,arg->parent,0,0,0,0));
    }
    identity(rec+56);
    /* Keep a complete child record even when exec succeeds or the parent blocks. */
    if(emit(rec))return 88;
    if(ACTION==2 || ACTION==5) {
        const char *av[]={HELPER,"exec",0};
        struct reply r=C(1059,HELPER,av,zero,0,0,0);
        return r.error?87:86;
    }
    if(ACTION==0 || ACTION==3 || ACTION==6) {
        struct reply r=C(1131,1,arg->parent,0,0,0,0);
        if(r.error)return 85;
    }
    return 37;
}
int main(int argc, char **argv) {
    if(argc>1 && argv[1][0]=='e') {
        U rec[64]={0x58535052,0,2};
        rec[6]=C(1020,0,0,0,0,0,0).value;rec[20]=PRDA_PID;
        reply(rec+27,C(1130,14,0,0,0,0,0));identity(rec+56);
        return emit(rec)?84:37;
    }
    if(argc>1) {
        /* Reference-only: the shell watchdog owns this entire new session. */
        if(C(1144,0,0,0,0,0,0).error)return 98;
        U uid=argv[1][0]=='1'?1234:0;
        if(C(1040,40,0,zero,0,0,0).error || C(1123,uid,uid,0,0,0,0).error || C(1124,uid,uid,0,0,0,0).error)return 97;
    }
    U rec[64]={0x58535052,CASE,0,FLAGS,ACTION,TRAP};
    struct argument arg={C(1020,0,0,0,0,0,0).value,0,0x98765432,0,0};
    rec[6]=arg.parent;rec[20]=PRDA_PID;PRDA_USER=0xbabababa;
    struct reply r=C(1005,"/dev/zero",2,0,0,0,0);if(r.error)return 96;
    arg.fd=r.value;
    if(LOCAL) {
        r=C(1134,0,8192,3,0x182,arg.fd,0);reply(rec+38,r);
        if(r.error)return 95;
        arg.local=r.value;*(volatile U *)arg.local=0x12345678;
    }
    if(TRAP==1132 && STACK_LEN>=8192) {
        r=C(1134,0,STACK_LEN,3,0x102,arg.fd,0);if(r.error)return 94;
        arg.stack_top=r.value+STACK_LEN;
    }
    rec[37]=arg.stack_top;rec[47]=(U)&arg;
    reply(rec+30,C(1130,14,0,0,0,0,0));
    U args[6]={BAD_ENTRY?0:(U)child_entry,FLAGS,(U)&arg,arg.stack_top,STACK_LEN,0};
    spawn_call(TRAP,args,&r);
    reply(rec+8,r);
    if(!r.error) {
        struct reply w=C(1170,0,r.value,info,1,0,0);reply(rec+24,w);
        rec[27]=info[1];rec[28]=info[5];rec[29]=info[3];
    }
    rec[21]=PRDA_USER;rec[22]=shared_word;rec[23]=arg.word;
    rec[48]=new_mapping;if(new_mapping)rec[49]=*(volatile U *)new_mapping;
    if(arg.local)rec[36]=*(volatile U *)arg.local;
    reply(rec+33,C(1003,arg.fd,zero,1,0,0,0));
    reply(rec+41,C(1130,14,0,0,0,0,0));
    identity(rec+56);return emit(rec)?89:0;
}
