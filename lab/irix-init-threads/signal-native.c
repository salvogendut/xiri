/* Native counterpart for the asynchronous-signal supervisor. */
#include <signal.h>
#include <stdint.h>
#include <unistd.h>
static volatile unsigned spinning;
int main(void) {
    sigset_t mask;sigemptyset(&mask);sigaddset(&mask,SIGTERM);
    uint32_t ready=0x58505453;char token;
    if(MODE && sigprocmask(SIG_BLOCK,&mask,NULL))return 90;
    if(write(1,&ready,4)!=4 || read(0,&token,1)!=1)return 91;
    if(sigprocmask(MODE?SIG_UNBLOCK:SIG_BLOCK,&mask,NULL))return 92;
    for(;;)spinning++;
}
