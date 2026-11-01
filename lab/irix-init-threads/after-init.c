/* Native exec must retain the real mask and remove the foreign PRDA. */
#include <sys/types.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include <errno.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
int main(void) {
    sigset_t mask;uint32_t words[4],want[4]={
        (1U<<(SIGUSR1-1))|(1U<<(SIGINFO-1)),1,0,0};
    if(sigprocmask(0,NULL,&mask))return 2;
    memcpy(words,&mask,sizeof(words));if(memcmp(words,want,sizeof(words)))return 3;
    char vec;errno=0;
    if(mincore((void *)0x200000,(size_t)getpagesize(),&vec)!=-1 || errno!=ENOMEM)return 4;
    pid_t child=fork();if(child<0)return 5;if(child==0)_exit(37);
    int status;if(waitpid(child,&status,0)!=child || !WIFEXITED(status) || WEXITSTATUS(status)!=37)return 6;
    printf("NATIVE_AFTER_INIT uid=%u mask=%08x,%08x,%08x,%08x prda_absent=1 fork=37\n",
        (unsigned)getuid(),words[0],words[1],words[2],words[3]);
    return 0;
}
