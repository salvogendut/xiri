/* Original shared-mapping fixtures. Explicit IRIX ABI words, no vendor libc. */
typedef unsigned int U;
typedef unsigned char B;
struct reply { U value, second, error; };
extern void probe_call(U, const U *, struct reply *);
static struct reply call(U n, U a, U b, U c, U d, U e, U f) {
    U args[6] = {a,b,c,d,e,f}; struct reply r; probe_call(n,args,&r); return r;
}
#define C(n,a,b,c,d,e,f) call(n,(U)(a),(U)(b),(U)(c),(U)(d),(U)(e),(U)(f))
static U rec[64] = {0x584d5348, CASE}, zero[4], info[32];
static void reply(U at, struct reply r) { rec[at]=r.value;rec[at+1]=r.second;rec[at+2]=r.error; }
static struct reply size(U fd) { return C(1019,fd,0,2,0,0,0); }
int main(int argc, char **argv) {
    if (argc > 1) {
        U uid=argv[1][0]=='1'?1234:0;
        if(C(1040,40,0,zero,0,0,0).error || C(1123,uid,uid,0,0,0,0).error || C(1124,uid,uid,0,0,0,0).error)return 98;
    }
    struct reply r=C(1040,22,11,0,0,0,0);if(r.error)return 97;rec[5]=r.value;
    const char *path=FILE_KIND==1?"data":FILE_KIND==2?".":FILE_KIND==3?"zero-link":FILE_KIND==4?"zero":"/dev/zero";
    r=C(1005,path,OPEN_MODE,0,0,0,0);if(r.error)return 96;U fd=r.value;
    reply(11,size(fd));
    if(BADFD==2 && C(1006,fd,0,0,0,0,0).error)return 95;
    rec[16]=ADDRESS;rec[17]=LENGTH;rec[18]=PROTECTION;rec[19]=FLAGS;
    rec[20]=OPEN_MODE;rec[21]=OFFSET;rec[22]=FILE_KIND;rec[23]=ACTION;
    rec[24]=BADFD;rec[25]=FILE_SIZE;rec[27]=TARGET;
    r=C(1134,ADDRESS,LENGTH,PROTECTION,FLAGS,BADFD==1?0xffffffff:fd,OFFSET);reply(2,r);
    struct reply mapped_size=size(fd);rec[26]=mapped_size.value;rec[52]=mapped_size.second;rec[53]=mapped_size.error;
    rec[54]=CLOSE_EARLY;
    if(CLOSE_EARLY && BADFD!=2)reply(8,C(1006,fd,0,0,0,0,0));
    if(!r.error && LENGTH && LENGTH<=0x200000) {
        volatile B *p=(volatile B *)r.value;
        if(ACTION<=2) {
            if(PROTECTION&1) {
                U expected=(FILE_KIND==1 || FILE_KIND==4)?0x3c:0;
#if LENGTH > 0
                for(U i=0;i<LENGTH;i+=4096){rec[6]++;if(p[i]!=expected)rec[7]++;}
#endif
                if(p[LENGTH-1]!=expected)rec[7]++;
            }
            if(PROTECTION&2){p[0]=0x5a;p[LENGTH-1]=0xa6;rec[55]|=1;}
            if(ACTION==1 || ACTION==2) {
                if(ACTION==1) {
                    struct reply child=C(1002,0,0,0,0,0,0);if(child.error)return 94;
                    if(child.second) {
                        if(p[0]!=0x5a || p[LENGTH-1]!=0xa6)return 93;
                        p[0]=0x8b;p[LENGTH-1]=0xc9;return 37;
                    }
                    struct reply w=C(1170,0,child.value,info,1,0,0);reply(48,w);
                    if(w.error)return 92;
                    rec[28]=info[1];rec[29]=info[5];rec[30]=info[3]==child.value;
                } else {
                    struct reply second=C(1134,0,LENGTH,PROTECTION,FLAGS&~0x10U,fd,OFFSET);reply(32,second);
                    if(!second.error) {
                        volatile B *q=(volatile B *)second.value;
                        rec[40]=q[0];q[0]=0x9b;rec[41]=q[0];rec[39]=p[0];
                        reply(42,C(1135,q,LENGTH,0,0,0,0));
                    }
                }
            }
            if(PROTECTION&1){rec[31]=p[0];rec[35]=p[LENGTH-1];}
        } else {
            struct reply child=C(1002,0,0,0,0,0,0);if(child.error)return 91;
            if(child.second) {
                if(ACTION==3){p[TARGET]=0x73;return 37;}
                return 37+(p[TARGET]!=0);
            }
            struct reply w=C(1170,0,child.value,info,1,0,0);reply(48,w);
            if(w.error)return 90;
            rec[28]=info[1];rec[29]=info[5];rec[30]=info[3]==child.value;
        }
        reply(36,C(1135,p,LENGTH,0,0,0,0));
    }
    reply(45,size(fd));
    if(BADFD!=2 && !CLOSE_EARLY)reply(8,C(1006,fd,0,0,0,0,0));
    r=C(1024,0,0,0,0,0,0);rec[56]=r.value;rec[57]=r.second;
    r=C(1047,0,0,0,0,0,0);rec[58]=r.value;rec[59]=r.second;
    r=C(1004,1,rec,sizeof(rec),0,0,0);if(r.error || r.value!=sizeof(rec))return 89;
    return 0;
}
