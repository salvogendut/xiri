/* Original cross-process lock observer with pipe barriers and bounded polling. */
typedef unsigned int U;
extern void probe_call(U,const U *,U *);
static U rec[144], lock[12], waitinfo[32];
static U call(U n,U a,U b,U c,U d,U *r)
{
    U args[6]={a,b,c,d,0,0};probe_call(n,args,r);return r[2];
}
static int transfer(U n,U fd,U *data,U bytes)
{
    U r[3];return call(n,fd,(U)data,bytes,0,r)||r[0]!=bytes;
}
static void setlock(U type,U start,U length)
{
    lock[0]=type<<16;
#if N32
    lock[2]=0;lock[3]=start;lock[4]=0;lock[5]=length;
#else
    lock[1]=start;lock[2]=length;
#endif
}
int main(int argc,char **argv)
{
    U r[3],fd,duplicate,down[2],up[2],child,token=1;
    (void)argv;
    if(argc>1) {
        if(call(1046,1234,0,0,0,r)||call(1023,1234,0,0,0,r))return 90;
    }
    rec[0]=0x58494642;rec[1]=CASE;rec[5]=ACTION;
    call(1024,0,0,0,0,r);rec[6]=r[0];rec[7]=r[1];
    call(1047,0,0,0,0,r);rec[8]=r[0];rec[9]=r[1];
    if(call(1005,(U)"tree/file",2,0,0,r))return 91;
    fd=r[0];
    setlock(PTYPE,0,100);
    if(call(1062,fd,PCMD,(U)lock,0,rec+2))return 92;
    if(ACTION==1) {if(call(1062,fd,0,0,0,r))return 93;duplicate=r[0];}
    else {if(call(1005,(U)"tree/file",2,0,0,r))return 94;duplicate=r[0];}
    if(call(1042,0,0,0,0,r))return 95;
    down[0]=r[0];down[1]=r[1];
    if(call(1042,0,0,0,0,r))return 96;
    up[0]=r[0];up[1]=r[1];
    if(call(1002,0,0,0,0,r))return 97;
    child=r[0];
    if(r[1]) {
        call(1006,down[1],0,0,0,r);call(1006,up[0],0,0,0,r);
        setlock(CTYPE,CSTART,20);
        call(1062,fd,NCMD,(U)lock,0,r);
        if(transfer(1004,up[1],r,12)||transfer(1003,down[0],&token,1))return 98;
        if(ACTION==5) {
            call(1006,fd,0,0,0,r);
            if(call(1005,(U)"tree/file",2,0,0,r))return 99;
            fd=r[0];
        }
        if(BLOCK && transfer(1004,up[1],&token,1))return 100;
        call(1062,fd,BLOCK?BCMD:NCMD,(U)lock,0,r);
        if(transfer(1004,up[1],r,12))return 101;
        return 0;
    }
    call(1006,down[0],0,0,0,r);call(1006,up[1],0,0,0,r);
    if(transfer(1003,up[0],rec+12,12))return 102;
    if(BLOCK) {
        if(transfer(1004,down[1],&token,1)||transfer(1003,up[0],&token,1))return 103;
        U fds[2]={up[0],1U<<16};
        call(1087,(U)fds,1,50,0,rec+28);rec[31]=fds[1]&0xffff;
    }
    if(ACTION==1 || ACTION==2)call(1006,duplicate,0,0,0,rec+32);
    else if(ACTION!=5) {
        setlock(3,0,(ACTION==3||ACTION==4)?50:0);
        call(1062,fd,PCMD,(U)lock,0,rec+32);
    }
    if(!BLOCK && transfer(1004,down[1],&token,1))return 104;
    if(transfer(1003,up[0],rec+16,12))return 105;
    if(call(1170,0,child,(U)waitinfo,1,r))return 106;
    rec[24]=r[0];rec[26]=r[2];
    setlock(2,0,100);call(1062,fd,NCMD,(U)lock,0,rec+20);
    return transfer(1004,1,rec,sizeof(rec))?107:0;
}
