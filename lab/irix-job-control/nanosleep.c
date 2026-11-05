/* Independent o32/n32 observations of IRIX nanosleep (1077). */
typedef unsigned int U;
typedef unsigned char B;
typedef unsigned long long Q;
struct reply { U value, second, error; };
extern void probe_call(U, const U *, struct reply *);
extern void signal_trampoline(void);
Q signal_entry[32];
static volatile U delivered;
static U record[128], zero[4], info[32];
static B request[24], remaining[24];

static struct reply call(U n, U a, U b, U c, U d, U e, U f)
{
    U args[6]={a,b,c,d,e,f}; struct reply r;
    probe_call(n,args,&r); return r;
}
#define C(n,a,b,c) call(n,(U)(a),(U)(b),(U)(c),0,0,0)
static void result(U at,struct reply r)
{ record[at]=r.value;record[at+1]=r.second;record[at+2]=r.error; }
static void put(B *p,U v)
{ p[0]=v>>24;p[1]=v>>16;p[2]=v>>8;p[3]=v; }
static void copy(B *d,const B *s,U n)
{ for(U i=0;i<n;i++)d[i]=s[i]; }
static U number(const char *s)
{ U n=0;while(*s>='0'&&*s<='9')n=n*10+(U)(*s++-'0');return n; }
void signal_body(void) { delivered++; }

/* Pointer kinds: normal, null, high, unaligned, boundary, read-only,
 * request alias and partial request overlap. All layouts are explicit. */
static U pointer(U kind,B *buffer,U base,U page,U req,int output)
{
    switch(kind) {
    case 1:return 0;
    case 2:return 0x80000000U;
    case 3:return (U)(buffer+5);
    case 4:return base+page-4;
    case 5:return base+(output?64:0);
    case 6:return req;
    case 7:return req+4;
    default:return (U)(buffer+4);
    }
}

int main(int argc,char **argv)
{
    U mode=argc>1?number(argv[1]):0, sec=0, nsec=0, in=0, out=0;
    U interrupt=0, flags=0, child=0, pipe_read=0, pipe_write=0;
    struct reply r;
    if(mode>32)return 90;
    if(argc>2) {
        U uid=argv[2][0]=='1'?1234:0;
        if(C(1040,40,0,zero).error || C(1123,uid,uid,0).error ||
           C(1124,uid,uid,0).error)return 91;
    }
    if(C(1164,3,zero,0).error)return 92;
    switch(mode) {
    case 1:nsec=1;break;
    case 2:nsec=1000000;break;
    case 3:nsec=20000000;break;
    case 4:sec=0xffffffff;break;
    case 5:nsec=0xffffffff;break;
    case 6:nsec=1000000000;break;
    case 7:nsec=1000000001;break;
    case 8:in=1;break;
    case 9:in=2;break;
    case 10:in=4;break;
    case 11:in=3;break;
    case 12:in=5;break;
    case 13:out=1;break;
    case 14:out=2;break;
    case 15:out=3;break;
    case 16:out=5;break;
    case 17:out=4;break;
    case 18:out=6;break;
    case 19:nsec=1000000000;out=2;break;
    case 20:interrupt=1;break;
    case 21:interrupt=1;flags=4;break;
    case 22:interrupt=1;out=1;break;
    case 23:interrupt=1;out=2;break;
    case 24:interrupt=1;out=3;break;
    case 25:interrupt=1;out=5;break;
    case 26:interrupt=1;out=4;break;
    case 27:interrupt=1;out=6;break;
    case 28:interrupt=1;out=7;break;
    case 29:interrupt=1;sec=0x7fffffff;break;
    case 30:sec=0x80000000;break;
    case 31:nsec=0x7fffffff;break;
    case 32:in=2;out=2;break;
    }
    if(interrupt && !sec)sec=2;
    record[0]=0x584e4150;record[1]=mode;
    r=C(1024,0,0,0);record[2]=r.value;record[3]=r.second;
    r=C(1047,0,0,0);record[4]=r.value;record[5]=r.second;
    U parent=C(1020,0,0,0).value;
    U page=C(1056,14,0,0).value;
    r=C(1005,"/dev/zero",2,0);if(r.error)return 93;U fd=r.value;
    r=call(1134,0,2*page,3,0x102,fd,0);if(r.error)return 94;U base=r.value;
    C(1006,fd,0,0);
    for(U i=0;i<2*page;i++)((B *)base)[i]=0x5a;
    for(U i=0;i<sizeof(request);i++)request[i]=remaining[i]=0xa5;
    U req=pointer(in,request,base,page,0,0);
    U rem=pointer(out,remaining,base,page,req,1);
    B *prepare=(in==1||in==2)?request+4:(B *)req;
    put(prepare,sec);put(prepare+4,nsec);
    if(C(1136,base+page,page,0).error)return 95;
    if((in==5||out==5)&&C(1136,base,page,1).error)return 96;
    record[6]=sec;record[7]=nsec;record[8]=in;record[9]=out;
    record[10]=interrupt;record[11]=flags;
    if(interrupt) {
        U action[8]={flags,(U)signal_body,0,0,0,0,0,0};
        r=call(1162,16,(U)action,0,(U)signal_trampoline,0,0);
        result(20,r);if(r.error)return 97;
        r=C(1042,0,0,0);if(r.error)return 98;
        pipe_read=r.value;pipe_write=r.second;
        r=C(1002,0,0,0);if(r.error)return 99;
        if(r.second) {
            B token;
            C(1006,pipe_write,0,0);
            r=C(1003,pipe_read,&token,1);
            if(r.error||r.value!=1){C(1001,80,0,0);return 80;}
            r=C(1082,10,0,0);
            if(r.error){C(1001,81,0,0);return 81;}
            r=C(1037,parent,16,0);
            C(1001,r.error?82:0,0,0);return 82;
        }
        child=r.value;C(1006,pipe_read,0,0);
    }
    result(24,C(1128,record+80,0,0));
    if(interrupt) {
        B token=1;
        r=C(1004,pipe_write,&token,1);if(r.error||r.value!=1)return 83;
        C(1006,pipe_write,0,0);
    }
    result(12,C(1077,req,rem,0));
    result(27,C(1128,record+82,0,0));
    record[15]=delivered;
    copy((B *)(record+32),request,sizeof(request));
    copy((B *)(record+40),remaining,sizeof(remaining));
    copy((B *)(record+48),(B *)(base+page-16),16);
    copy((B *)(record+56),(B *)(base+56),24);
    if(child) {
        /* Reap the helper even if a future implementation returns early. */
        if(!delivered)C(1037,child,9,0);
        do {r=call(1170,0,child,(U)info,1,0,0);} while(r.error&&r.value==4);
        result(16,r);record[19]=info[5];
    }
    C(1135,base,2*page,0);
    r=C(1004,1,record,sizeof(record));
    return r.error||r.value!=sizeof(record);
}
