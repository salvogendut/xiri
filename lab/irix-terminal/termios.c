/* Independent terminal ABI observer for the supplied IRIX 6.5.22 system.
 * No host headers or libc: the same bytes run through both syscall ABIs. */
typedef unsigned int U;
typedef unsigned char B;
extern void probe_call(U, const U *, U *);
static U record[256], status[40], packet[20];
static U call(U slot,U n,U a,U b,U c,U d,U e,U f)
{
    U args[6]={a,b,c,d,e,f}; probe_call(n,args,record+slot);
    return record[slot+2]==0;
}
#define C(s,n,a,b,c) call(s,n,(U)(a),(U)(b),(U)(c),0,0,0)
static U number(char *s)
{
    U n=0,base=10;
    if(s[0]=='0' && s[1]=='x'){base=16;s+=2;}
    for(;*s;s++)n=n*base+(*s>='a'?*s-'a'+10:*s-'0');
    return n;
}
static void fill(B *p,U n,B v){for(U i=0;i<n;i++)p[i]=v;}
static void copy(B *d,const B *s,U n){for(U i=0;i<n;i++)d[i]=s[i];}
int main(int argc,char **argv)
{
    U cmd,kind,ptr,variant,master,slave,fd,address,page,base=0;
    U get,offset,size,isnew,isline,isset;
    char path[32]="/dev/ttyq",digits[12]; U n=0,unit;
    B chars[23]={3,28,127,21,4,0,0,0,17,19,26,0,18,15,23,22};
    U unlock[4]={0x5002,0,0,0};
    U normal[12]={0x502,5,0xb0,0x13b,9600,0};
    if(argc!=5)return 2;
    cmd=number(argv[1]);kind=number(argv[2]);ptr=number(argv[3]);variant=number(argv[4]);
    record[0]=0x5854494f;record[1]=cmd;record[2]=kind;record[3]=ptr;record[4]=variant;
    C(5,1024,0,0,0);
    if(!C(8,1039,1,0,0))goto done;
    if(!C(11,1005,"/dev/ptc",2,0))goto done;
    master=record[11];
    if(!C(53,1054,master,0x5308,unlock))goto done;
    if(!C(14,1160,3,master,status))goto done;
    copy((B *)(record+160),(B *)status,sizeof(status));
    unit=status[10]&0x3ffff;
    if(unit>=400)return 3;
    if(unit>=200){path[8]='r';unit-=200;}
    do{digits[n++]='0'+unit%10;unit/=10;}while(unit);
    for(U i=0;i<n;i++)path[9+i]=digits[n-1-i];
    path[9+n]=0;
    copy((B *)(record+204),(B *)path,sizeof(path));
    if(!C(17,1005,path,0x802,0))goto done;
    slave=record[17];fd=kind==1?master:slave;
    copy((B *)normal+24,chars,23);
    C(20,1054,slave,0x54d6,normal); /* establish explicit common settings */
    if(kind==2 || kind==3){if(!C(23,1005,kind==2?"input.txt":"/dev/null",2,0))goto done;fd=record[23];}
    if(kind==4)fd=0xffffffff;
    isnew=(cmd&255)>=200;isline=((cmd&255)%200)<13;
    get=(isnew?0x54c9:0x5401)+(isline?0:12);
    isset=cmd!=get;offset=16+(isnew?8:0)+(isline?1:0);size=isnew?48:40;
    fill((B *)packet,sizeof(packet),0xa5);
    if(isset){
        fill((B *)packet,size,0);copy((B *)packet,(B *)normal,16);
        if(isnew){packet[4]=9600;packet[5]=0;}else packet[2]|=13;
        if(isline)((B *)packet)[offset-1]=1;
        copy((B *)packet+offset,chars,23);
        if(variant==1){packet[0]=0;packet[1]=0;packet[3]=0;((B *)packet)[offset+4]=7;((B *)packet)[offset+5]=2;}
        if(variant==2){packet[0]=0x1dff;packet[1]=0x1d;packet[3]=0x8ebb;}
        if(variant==3){((B *)packet)[offset]=0;((B *)packet)[offset+2]=8;((B *)packet)[offset+10]=0;}
        if(variant==4 && isnew){packet[4]=19200;packet[5]=19200;}
        if(variant==5 && isline)((B *)packet)[offset-1]=17;
    }
    address=(U)packet;
    if(ptr==1)address=0;
    if(ptr==2)address=0x80000000;
    if(ptr==5){copy((B *)(record+64)+1,(B *)packet,sizeof(packet));address=(U)(record+64)+1;}
    if(ptr==3 || ptr==4){
        if(!C(32,1056,14,0,0))goto done;
        page=record[32];
        if(!C(35,1005,"/dev/zero",2,0))goto done;
        if(!call(38,1134,0,2*page,3,0x102,record[35],0))goto done;
        base=record[38];
        address=ptr==3?base+page-8:base;
        copy((B *)address,(B *)packet,sizeof(packet));
        if(!C(41,1136,ptr==3?base+page:base,page,ptr==3?0:1))goto done;
    }
    copy((B *)(record+96),(B *)packet,sizeof(packet));
    C(26,1054,fd,cmd,address);
    if(ptr==0)copy((B *)(record+64),(B *)packet,sizeof(packet));
    if(ptr==3)copy((B *)(record+64),(B *)address,8);
    if(ptr==4)copy((B *)(record+64),(B *)address,sizeof(packet));
    fill((B *)(record+128),80,0xa5);
    C(29,1054,slave,0x54d5,record+128);
    if(fd!=master && fd!=slave && kind!=4)C(44,1006,fd,0,0);
    C(47,1006,slave,0,0);C(50,1006,master,0,0);
done:
    {U args[6]={1,(U)record,sizeof(record),0,0,0},r[3];probe_call(1004,args,r);return r[2] || r[0]!=sizeof(record)?99:0;}
}
