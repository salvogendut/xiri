/* Session/foreground queries in a child which opens a newly allocated PTY. */
typedef unsigned int U;
typedef unsigned char B;
extern void probe_call(U,const U *,U *);
static U rec[256],st[40];
static U call(U s,U nr,U a,U b,U c,U d)
{
    U args[6]={a,b,c,d,0,0};probe_call(nr,args,rec+s);return rec[s+2]==0;
}
#define C(s,n,a,b,c) call(s,n,(U)(a),(U)(b),(U)(c),0)
int main(int argc,char **argv)
{
    U mode=argc>1?argv[1][0]-'0':0,master,slave,pid,unit,n=0;
    U unlock[4]={0x5002,0,0,0},info[32];char path[32]="/dev/ttyq",digits[10];
    rec[0]=0x58545345;rec[1]=mode;C(2,1024,0,0,0);
    if(!C(5,1005,"/dev/ptc",2,0))return 3;
    master=rec[5];
    if(!C(8,1054,master,0x5308,unlock) || !C(11,1160,3,master,st))return 4;
    unit=st[10]&0x3ffff;if(unit>=400)return 5;
    if(unit>=200){path[8]='r';unit-=200;}
    do{digits[n++]='0'+unit%10;unit/=10;}while(unit);
    for(U i=0;i<n;i++)path[9+i]=digits[n-1-i];
    path[9+n]=0;
    if(!C(14,1002,0,0,0))return 6;
    if(rec[15]==0){
        if(!call(17,1170,0,rec[14],(U)info,1))return 7;
        C(20,1006,master,0,0);return info[1]!=1 || info[5]!=0?8:0;
    }
    C(17,1020,0,0,0);pid=rec[17];
    if(mode!=2)C(20,1040,20,0,0);
    if(!C(23,1005,path,mode==1?0x802:2,0))goto done;
    slave=rec[23];
    if(mode==3)slave=master;
    if(mode==4)slave=0xffffffff;
    if(mode==5){C(26,1005,"input.txt",0,0);slave=rec[26];}
    for(U i=0;i<7;i++)rec[64+i]=0xa5a5a5a5;
    C(29,1054,slave,0x7416,mode==6?0:rec+64);
    C(32,1054,slave,0x7414,rec+65);
    C(35,1054,slave,0x40047477,rec+66);
    rec[67]=mode==7?0x7fffffff:pid;
    C(38,1054,slave,0x7415,rec+67);
    C(41,1054,slave,0x80047476,rec+67);
    C(44,1054,slave,0x7416,rec+68);
    C(47,1054,slave,0x7414,rec+69);
    C(50,1054,slave,0x40047477,rec+70);
    C(53,1040,65,0,0);C(56,1039,0,0,0);
done:
    {U args[6]={1,(U)rec,sizeof(rec),0,0,0},r[3];probe_call(1004,args,r);return r[2] || r[0]!=sizeof(rec)?9:0;}
}
