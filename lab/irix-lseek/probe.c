/* Observe legacy lseek width, validation, offset lifetime, and errors. */
typedef unsigned int u32;
extern void probe_call(u32, const u32 *, u32 *);
static u32 record[384], n;
static char byte;
static u32 call(u32 s,u32 a,u32 b,u32 c) {
 u32 args[6]={a,b,c,0,0,0},r[3];
 probe_call(s,args,r);
 record[n++]=s;record[n++]=a;record[n++]=b;record[n++]=c;
 record[n++]=r[0];record[n++]=r[1];record[n++]=r[2];record[n++]=(unsigned char)byte;
 return r[0];
}
int main(int argc,char **argv) {
 u32 fd,du,pipe,r[3],args[6]; (void)argv;
 if(argc>1){call(1046,1234,0,0);call(1023,1234,0,0);n=0;}
 call(1024,0,0,0);call(1047,0,0,0);
 fd=call(1005,(u32)"seek-file",0,0); record[16+1]=0;
 call(1019,fd,0,0);call(1003,fd,(u32)&byte,1); record[n-6]=0;
 call(1019,fd,3,0);call(1003,fd,(u32)&byte,1); record[n-6]=0;
 call(1019,fd,-2,1);call(1003,fd,(u32)&byte,1); record[n-6]=0;
 call(1019,fd,-1,2);call(1003,fd,(u32)&byte,1); record[n-6]=0;
 call(1019,fd,-1,0);call(1019,fd,0,1);

 call(1019,fd,0x7fffffff,0);call(1019,fd,1,1);call(1019,fd,0,1);
 call(1019,fd,0x80000000,1);call(1019,fd,0,1);
 call(1019,fd,0xffffffff,0);call(1019,fd,0,1);
 call(1019,fd,8,0);du=call(1062,fd,0,0);
 call(1019,du,2,1);call(1019,fd,0,1);
 call(1006,du,0,0);call(1019,du,0,0);call(1019,-1,0,0);
 pipe=call(1042,0,0,0);call(1019,pipe,0,0);
 args[0]=1;args[1]=(u32)record;args[2]=sizeof(record);args[3]=args[4]=args[5]=0;
 probe_call(1004,args,r);return r[2]||r[0]!=sizeof(record);
}
