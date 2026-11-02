/* Foreign peer for native/IRIX lock ownership and F_GETLK interoperability. */
typedef unsigned int U;
extern void probe_call(U,const U *,U *);
static U lock[12], reply[24];
static U seek_data[16];
static int call(U n,U a,U b,U c,U *r)
{
    U args[6]={a,b,c,0,0,0};probe_call(n,args,r);return r[2];
}
static void range(void)
{
    for(U i=0;i<12;i++)lock[i]=0;
    lock[0]=2U<<16;
    lock[N32?5:2]=100;
}
static int send(U bytes)
{
    U r[3];return call(1004,1,(U)reply,bytes,r)||r[0]!=bytes;
}
int main(void)
{
    U fd,r[3],token;
    if(call(1005,(U)"tree/file",2,0,r))return 91;
    fd=r[0];
    if(call(1003,fd,(U)seek_data,64,r)||r[0]!=64)return 95;
    range();lock[0]|=1; /* SEEK_CUR, with a nonzero file offset. */
    if(N32){lock[2]=0xffffffff;lock[3]=0xffffffc0;}
    else lock[1]=0xffffffc0;
    call(1062,fd,14,(U)lock,reply);
    for(U i=0;i<12;i++)reply[8+i]=lock[i];
    if(send(sizeof(reply)))return 92;
    range();call(1062,fd,12,(U)lock,reply);
    if(send(12)||call(1003,0,(U)&token,1,r)||r[0]!=1)return 93;
    call(1062,fd,13,(U)lock,reply);
    if(send(12)||call(1003,0,(U)&token,1,r)||r[0]!=1)return 94;
    return 0;
}
