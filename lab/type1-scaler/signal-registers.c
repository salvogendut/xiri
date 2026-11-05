/* Compare every native o32 FPR and FCSR across a real signal return. */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <signal.h>
#include <unistd.h>

extern int native_fpu_roundtrip(const uint32_t *, uint32_t *, int, unsigned, int);
static volatile sig_atomic_t delivered, clobber;

static void handler(int signo)
{
    delivered += signo == SIGUSR1;
    if (clobber) {
        unsigned csr = 3;
        __asm volatile("mtc1 $zero,$f0\n\tmtc1 $zero,$f2\n\t"
                       "ctc1 %0,$31\n\tnop\n\tnop"
                       : : "r"(csr) : "$f0", "$f2");
    }
}

static void info_handler(int signo, siginfo_t *info, void *context)
{
    (void)info; (void)context;
    handler(signo);
}

int main(void)
{
    uint32_t seed[32], actual[33];
    unsigned failures=0, cases=0;
    int pid=getpid();
    for(unsigned i=0;i<32;i++)seed[i]=0x3f800000U+i*0x101U;
    alarm(30);
    for(int kind=-1;kind<2;kind++)for(int touch=0;touch<2;touch++)
        for(unsigned mode=0;mode<4;mode++) {
            struct sigaction sa={0};
            sigemptyset(&sa.sa_mask);
            if(kind==1) {sa.sa_flags=SA_SIGINFO;sa.sa_sigaction=info_handler;}
            else sa.sa_handler=handler;
            if(sigaction(SIGUSR1,&sa,NULL))return 2;
            delivered=0;clobber=touch;
            memset(actual,0xcc,sizeof(actual));
            unsigned csr=mode|4U;
            int rc=native_fpu_roundtrip(seed,actual,kind<0?-1:pid,csr,SIGUSR1);
            unsigned bad=0;
            for(unsigned i=0;i<32;i++)if(actual[i]!=seed[i])bad++;
            if(actual[32]!=csr)bad++;
            int ok=rc==0 && !bad && delivered==(kind<0?0:1);
            printf("REGISTERS kind=%d touch=%d mode=%u delivered=%d bad=%u csr=%08x expected=%08x rc=%d pass=%d\n",
                kind,touch,mode,(int)delivered,bad,actual[32],csr,rc,ok);
            failures+=!ok;cases++;
        }
    printf("REGISTERS_RESULT cases=%u failures=%u\n",cases,failures);
    return failures?1:0;
}
