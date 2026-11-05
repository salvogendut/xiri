/* libc-free process-group observations; children exit when the owning pipe
 * closes, including when the parent is killed while they own another group. */
typedef unsigned int U;
struct reply { U value,second,error; };
extern void probe_call(U,const U *,struct reply *);
static U rec[256],zero[4],info[32];
static struct reply call(U n,U a,U b,U c,U d,U e,U f)
{U args[6]={a,b,c,d,e,f};struct reply r;probe_call(n,args,&r);return r;}
#define C(n,a,b,c) call(n,(U)(a),(U)(b),(U)(c),0,0,0)
static U number(const char *s)
{U n=0;while(*s>='0'&&*s<='9')n=n*10+(U)(*s++-'0');return n;}
static void decimal(char *s,U value)
{char t[12];U n=0;do{t[n++]=(char)('0'+value%10);value/=10;}while(value);for(U i=0;i<n;i++)s[i]=t[n-i-1];s[n]=0;}
static int transfer(U fd,void *data,U count,int write)
{struct reply r;do{r=C(write?1004:1003,fd,data,count);}while(r.error&&r.value==4);return r.error||r.value!=count;}
static int child(U output,U input,U mode)
{
    U ready[8]={0x58504743,0,0,0,0,0,0,0},token;
    struct reply r;
    if(mode==2){r=C(1040,20,0,0);ready[5]=r.value;ready[6]=r.error;}
    ready[1]=C(1020,0,0,0).value;ready[2]=C(1039,0,0,0).value;
    ready[3]=C(1040,65,0,0).value;ready[4]=C(1024,0,0,0).value;
    if(transfer(output,ready,sizeof(ready),1))return 81;
    /* EOF is also a release. Only the owning parent holds the write end. */
    do{r=C(1003,input,&token,1);}while(r.error&&r.value==4);
    return r.error?82:37;
}
static struct reply observe(U slot,U request,U first,U second)
{
    struct reply r=C(1040,request,first,second);U at=32+slot*4;
    rec[at]=r.value;rec[at+1]=r.second;rec[at+2]=r.error;rec[at+3]=request;
    return r;
}
int main(int argc,char **argv)
{
    if(argc==4&&argv[1][0]=='e')return child(number(argv[2]),number(argv[3]),1);
    U mode=argc>1?number(argv[1]):0;
    if(mode>2)return 90;
    if(argc>2){U uid=argv[2][0]=='1'?1234:0;if(C(1040,40,0,zero).error||C(1123,uid,uid,0).error||C(1124,uid,uid,0).error)return 91;}
    struct reply r=C(1024,0,0,0);rec[2]=r.value;rec[3]=r.second;
    r=C(1047,0,0,0);rec[4]=r.value;rec[5]=r.second;
    rec[0]=0x58504752;rec[1]=mode;
    r=C(1020,0,0,0);rec[6]=r.value;rec[7]=r.second;
    rec[8]=C(1039,0,0,0).value;rec[9]=C(1040,65,0,0).value;
    r=C(1042,0,0,0);if(r.error)return 92;U ready_r=r.value,ready_w=r.second;
    r=C(1042,0,0,0);if(r.error)return 93;U gate_r=r.value,gate_w=r.second;
    r=C(1002,0,0,0);if(r.error)return 94;
    if(r.second){
        C(1006,ready_r,0,0);C(1006,gate_w,0,0);
        if(mode==1){
            char a[12],b[12];decimal(a,ready_w);decimal(b,gate_r);
            const char *av[]={argv[0],"exec",a,b,0};
            C(1059,argv[0],av,zero);return 83;
        }
        return child(ready_w,gate_r,mode);
    }
    U pid=r.value;rec[10]=pid;
    C(1006,ready_w,0,0);C(1006,gate_r,0,0);
    if(transfer(ready_r,rec+16,32,0)){rec[11]=1;goto finish;}
    observe(0,64,0,0);observe(1,64,rec[6],0);observe(2,64,pid,0);
    r=observe(3,64,rec[7],0);U parent_group=r.value;
    observe(4,64,0x7ffffffe,0);observe(5,64,0xffffffff,0);
    observe(6,21,0,0);observe(7,21,rec[6],rec[6]);
    observe(8,21,0xffffffff,0);observe(9,21,0,0xffffffff);
    observe(10,21,0x7ffffffe,0);observe(11,21,rec[7],parent_group);
    observe(12,21,pid,pid);observe(13,64,pid,0);
    observe(14,21,pid,rec[8]);observe(15,64,pid,0);
    observe(16,21,pid,0);observe(17,64,pid,0);
    observe(18,21,pid,0x7ffffffe);observe(19,21,pid,0xffffffff);
    observe(20,64,0x80000000,0);observe(21,21,0x80000000,0);
    observe(22,21,0,0x80000000);observe(23,64,pid,0);
    observe(24,65,pid,0);observe(25,22,6,0);
    /* The original getpgid range excludes MAXPID; setpgid accepts it. */
    observe(26,64,0x7fffffef,0);observe(27,64,0x7ffffff0,0);
    observe(28,64,0x7ffffff1,0);
    observe(29,21,pid,0x7fffffef);observe(30,21,pid,0x7ffffff0);
    observe(31,21,pid,0x7ffffff1);
    observe(32,21,0x7ffffffe,0x7ffffff0);
    observe(33,21,0x7ffffffe,0x7ffffff1);
    observe(34,64,1000000,0);observe(35,21,pid,1000000);
    observe(36,21,1000000,0);
finish:
    C(1006,gate_w,0,0);C(1006,ready_r,0,0);
    do{r=call(1170,0,pid,(U)info,1,0,0);}while(r.error&&r.value==4);
    rec[24]=r.value;rec[25]=r.second;rec[26]=r.error;
    rec[27]=info[1];rec[28]=info[3];rec[29]=info[5];
    r=C(1004,1,rec,sizeof(rec));return r.error||r.value!=sizeof(rec);
}
