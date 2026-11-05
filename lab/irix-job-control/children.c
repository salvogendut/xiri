/* Independent IRIX child-state observer. Pipes and WNOWAIT establish each
 * state before delivery is observed; no delay stands in for a state barrier. */
typedef unsigned int U;
typedef unsigned char B;
typedef unsigned long long Q;
struct reply { U value, second, error; };
extern void probe_call(U, const U *, struct reply *);
extern void signal_trampoline(void);
Q signal_entry[32];
static U record[640], zero[4], block[4]={1U<<17,0,0,0}, cleanup[32];
static volatile U notices;

static struct reply call(U n,U a,U b,U c,U d,U e,U f)
{ U args[6]={a,b,c,d,e,f};struct reply r;probe_call(n,args,&r);return r; }
#define C(n,a,b,c) call(n,(U)(a),(U)(b),(U)(c),0,0,0)
static void result(U at,struct reply r)
{record[at]=r.value;record[at+1]=r.second;record[at+2]=r.error;}
static U number(const char *s)
{U n=0;while(*s>='0'&&*s<='9')n=n*10+(U)(*s++-'0');return n;}
static void bytes(B *to,const B *from,U count)
{for(U i=0;i<count;i++)to[i]=from[i];}

void signal_body(void)
{
    U n=notices++;
    if(n>=4)return;
    U at=400+36*n;
    record[at]=(U)signal_entry[4];
    if(record[at]&0x80000000U)
        bytes((B *)(record+at+4),(const B *)(U)signal_entry[5],128);
}

static struct reply wait_event(U slot,U type,U id,U flags)
{
    U at=64+36*slot;
    struct reply r;
    for(U i=0;i<32;i++)record[at+4+i]=0xa5a5a5a5;
    do {r=call(1170,type,id,(U)(record+at+4),flags,0,0);}
        while(r.error&&r.value==4);
    result(at,r);record[at+3]=flags;
    return r;
}

static int token(U fd,int write)
{
    B value=42;struct reply r;
    do {r=C(write?1004:1003,fd,&value,1);} while(r.error&&r.value==4);
    return r.error||r.value!=1;
}

int main(int argc,char **argv)
{
    U mode=argc>1?number(argv[1]):0,selector=argc>2?number(argv[2]):0;
    U flags=(mode<2?8:0)|(mode&1?0x20000:0);
    struct reply r;
    if(mode>3||selector>7)return 90;
    if(argc>3) {
        U uid=argv[3][0]=='1'?1234:0;
        if(C(1040,40,0,zero).error||C(1123,uid,uid,0).error||
            C(1124,uid,uid,0).error)return 91;
    }
    record[0]=0x5843484c;record[1]=mode;record[2]=selector;record[3]=flags;
    r=C(1024,0,0,0);record[4]=r.value;record[5]=r.second;
    r=C(1047,0,0,0);record[6]=r.value;record[7]=r.second;
    record[8]=C(1020,0,0,0).value;record[9]=C(1039,0,0,0).value;
    U action[8]={flags,(U)signal_body,0,0,0,0,0,0};
    r=call(1162,18,(U)action,0,(U)signal_trampoline,0,0);
    result(24,r);if(r.error)return 92;
    if(C(1164,3,block,0).error)return 93;
    r=C(1042,0,0,0);if(r.error)return 94;U ready_r=r.value,ready_w=r.second;
    r=C(1042,0,0,0);if(r.error)return 95;U gate_r=r.value,gate_w=r.second;
    r=C(1002,0,0,0);if(r.error)return 96;
    if(r.second) {
        C(1006,ready_r,0,0);C(1006,gate_w,0,0);
        if(token(ready_w,1))return 81;
        if(C(1037,C(1020,0,0,0).value,23,0).error)return 82;
        if(token(ready_w,1)||token(gate_r,0))return 83;
        C(1001,37,0,0);return 84;
    }
    U child=r.value;record[10]=child;
    C(1006,ready_w,0,0);C(1006,gate_r,0,0);
    U type=0,id=child;
    switch(selector) {
    case 1:type=2;id=record[9];break;
    case 2:type=2;id=0;break;
    case 3:type=7;id=0;break;
    case 4:type=7;id=42;break;
    case 5:type=0;id=0;break;
    case 6:type=0;id=0xffffffff;break;
    case 7:type=99;id=child;break;
    }
    record[11]=type;record[12]=id;
    if(token(ready_r,0)){record[13]=1;goto finish;}
    r=wait_event(0,type,id,4|128);
    if(r.error){record[13]=2;goto finish;}
    wait_event(1,type,id,4|64);
    wait_event(2,type,id,4|64);
    result(28,C(1164,2,block,0));record[16]=notices;
    if(C(1164,1,block,0).error){record[13]=3;goto finish;}
    result(32,C(1037,child,25,0));
    if(record[34]||token(ready_r,0)){record[13]=4;goto finish;}
    wait_event(3,type,id,8|64|128);
    wait_event(4,type,id,8|64);
    wait_event(5,type,id,8|64);
    result(36,C(1164,2,block,0));record[17]=notices;
    if(C(1164,1,block,0).error||token(gate_w,1)){record[13]=5;goto finish;}
    wait_event(6,type,id,1|128);
    result(40,C(1164,2,block,0));record[18]=notices;
    r=wait_event(7,type,id,1);
    record[19]=!r.error;
    wait_event(8,type,id,1|64);
finish:
    if(!record[19]) {
        C(1037,child,9,0);
        do {r=call(1170,0,child,(U)cleanup,1,0,0);} while(r.error&&r.value==4);
        result(44,r);
    }
    C(1006,gate_w,0,0);C(1006,ready_r,0,0);
    C(1164,3,zero,0);
    record[20]=notices;
    r=C(1004,1,record,sizeof(record));
    return r.error||r.value!=sizeof(record);
}
