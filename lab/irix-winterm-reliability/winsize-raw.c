/* Original libc-free window-size observations, identical on o32 and n32. */
typedef unsigned int U;
typedef unsigned char B;
struct reply { U value, second, error; };
extern void probe_call(U, const U *, struct reply *);
static struct reply call(U n,U a,U b,U c,U d,U e,U f) {
    U args[6]={a,b,c,d,e,f}; struct reply r; probe_call(n,args,&r); return r;
}
#define C(n,a,b,c) call(n,(U)(a),(U)(b),(U)(c),0,0,0)
static U records[40][8], count;
static U size[4]={0x11223344,0xa5a5a5a5,0xa5a5a5a5,0x55667788};
static B unaligned[12];
static void observe(U fd,U command,U pointer) {
    struct reply r=C(1054,fd,command,pointer);
    U *p=records[count++];p[0]=count;p[1]=r.error;p[2]=r.value;
    for(U i=0;i<4;i++)p[3+i]=size[i];
}
int main(int argc,char **argv) {
    U zero[4]={0};
    if(argc>1 && argv[1][0]=='1') {
        if(C(1040,40,0,zero).error || C(1123,1234,1234,0).error || C(1124,1234,1234,0).error)return 98;
    }
    struct reply r=C(1005,"/dev/ptc",2,0600);if(r.error)return 2;U fd=r.value;
    r=C(1005,"regular",0,0);if(r.error)return 3;U regular=r.value;
    r=C(1005,"/dev/null",2,0);if(r.error)return 4;U nullfd=r.value;
    U get=0x40087468,set=0x80087467,pointer=(U)(size+1);
    observe(fd,get,pointer);
    size[1]=31U<<16|97;size[2]=776U<<16|465;observe(fd,set,pointer);
    size[1]=size[2]=0xa5a5a5a5;observe(fd,get,pointer);
    size[1]=size[2]=0;observe(fd,set,pointer);observe(fd,get,pointer);
    size[1]=size[2]=0xffffffff;observe(fd,set,pointer);observe(fd,get,pointer);
    observe(-1,get,pointer);observe(-1,set,pointer);observe(-1,get,0);observe(-1,set,0);
    observe(regular,get,pointer);observe(regular,set,pointer);
    observe(nullfd,get,pointer);observe(nullfd,set,pointer);
    observe(regular,get,0);observe(regular,set,0);observe(nullfd,get,0);observe(nullfd,set,0);
    observe(fd,get,0);observe(fd,set,0);observe(fd,get,0x80000000);observe(fd,set,0xfffffffc);
    for(U i=0;i<12;i++)unaligned[i]=0xa5;
    for(U i=0;i<8;i++)unaligned[i+1]=((B *)(size+1))[i];
    observe(fd,set,(U)unaligned+1);observe(fd,get,(U)unaligned+1);
    for(U i=0;i<3;i++)records[count-1][3+i]=((U *)unaligned)[i];
    U page=C(1056,14,0,0).value;
    r=C(1005,"/dev/zero",2,0);if(r.error)return 5;U zero_fd=r.value;
    r=call(1134,0,2*page,3,0x102,zero_fd,0);if(r.error)return 6;U base=r.value;
    if(C(1136,base+page,page,0).error)return 7;
    for(U i=0;i<8;i++)((B *)base)[page-8+i]=0xa5;
    observe(fd,get,base+page-4);
    records[count-1][7]=*(U *)(base+page-4);
    observe(fd,set,base+page-4);observe(fd,get,pointer);
    if(C(1136,base,page,1).error)return 8;
    observe(fd,get,base);observe(fd,set,base);observe(fd,get,pointer);
    C(1006,fd,0,0);C(1006,regular,0,0);C(1006,nullfd,0,0);C(1006,zero_fd,0,0);
    r=C(1004,1,records,count*sizeof(records[0]));
    return r.error || r.value!=count*sizeof(records[0]) ? 99 : 0;
}
