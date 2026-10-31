/* Original libc-free paired probes. Fixed 32-bit records for both IRIX ABIs. */
typedef unsigned int U;
struct reply { U value, second, error; };
static struct reply call(U number, U x, U y, U z) {
    register U v0 __asm__("$2") = INDIRECT ? 1000 : number;
    register U v1 __asm__("$3") = 0xfeedface;
    register U a0 __asm__("$4") = INDIRECT ? number : x;
    register U a1 __asm__("$5") = INDIRECT ? x : y;
    register U a2 __asm__("$6") = INDIRECT ? y : z;
    register U a3 __asm__("$7") = INDIRECT ? z : 0;
    /* Treat all ABI caller-saved registers as clobbered across the trap;
     * IRIX does not promise the stronger preservation seen on NetBSD. */
    __asm__ volatile("syscall\n\tnop" : "+r"(v0), "+r"(v1), "+r"(a3),
        "+r"(a0), "+r"(a1), "+r"(a2) : : "memory", "$1", "$8", "$9",
        "$10", "$11", "$12", "$13", "$14", "$15", "$24", "$25", "hi", "lo");
    return (struct reply){v0,v1,a3};
}
static U record[21] = {0x58505459, CASE};
static U info[40];
static U request[4] = {COMMAND, TIMEOUT, LENGTH, DATA};
static char path[] = PATH;
int main(int argc, char **argv) {
    struct reply r, opened={0,0,1};
    U fd=0xffffffffU, pointer=(U)path;
    int i;
    if (argc > 1) {
        U uid = argv[1][0]=='1' ? 1234 : 0;
        if (call(1040,40,0,(U)info).error || call(1123,uid,uid,0).error ||
            call(1124,uid,uid,0).error) return 98;
        r=call(1040,41,0,(U)info);
        if (r.error || r.value) return 98;
    }
    if (KIND==0 || KIND==1 || KIND==4) {
        opened=call(1005,(U)path,KIND==0 ? MODE : 2,0600);
        if (!opened.error) fd=opened.value;
    }
#ifdef POINTER
    pointer=POINTER;
#endif
    if (KIND==0) {r=opened;if (!r.error) r.value=0;}
    else if (KIND==1) r=call(1062,fd,4,MODE);
    else if (KIND==2) r=call(1015,pointer,MODE,0);
    else if (KIND==3) r=call(1016,pointer,OWNER,GROUP);
    else {
        pointer=(U)request;
#ifdef POINTER
        pointer=POINTER;
#endif
#ifdef BAD_FD
        fd=BAD_FD;
#endif
        r=call(1054,fd,0x5308,pointer);
    }
    record[2]=r.value;record[3]=r.second;record[4]=r.error;
    if (!opened.error) {
        r=call(1062,opened.value,3,0);record[5]=r.value;record[6]=r.error;
    }
    for (i=0;i<40;i++) info[i]=0xa5a5a5a5;
    info[N32 ? 39 : 35]=0x5a5a5a5a;
    r=KIND==4 ? call(1160,VERSION,opened.value,(U)info) :
        call(1158,VERSION,(U)path,(U)info);
    if (!r.error) {
        record[7]=info[N32 ? 6 : 5];record[8]=info[N32 ? 8 : 7];
        record[9]=info[N32 ? 9 : 8];record[10]=info[N32 ? 10 : 9];
    } else {record[7]=r.value;record[8]=r.error;}
    r=call(1024,0,0,0);record[11]=r.value;record[12]=r.second;
    r=call(1047,0,0,0);record[13]=r.value;record[14]=r.second;
    record[15]=info[N32 ? 38 : 34];record[16]=info[N32 ? 39 : 35];
    for(i=0;i<4;i++)record[17+i]=request[i];
    if (!opened.error && call(1006,opened.value,0,0).error) return 97;
    r=call(1004,1,(U)record,sizeof(record));
    return r.error || r.value!=sizeof(record) ? 99 : 0;
}
