/* Original libc-level SIGCHLD stop/exit notification control. */
#include <sys/types.h>
#include <sys/wait.h>
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
static volatile sig_atomic_t notices;
static void notice(int sig) { (void)sig; notices++; }
int main(int argc,char **argv)
{
    struct sigaction action, query;
    int suppress=argc>1 && !strcmp(argv[1],"suppress");
    int status=0, i, fds[2], before; char byte;
    pid_t pid, got;
    if(argc>2 && !strcmp(argv[2],"user") && (setgid(1234)||setuid(1234)))return 2;
    memset(&action,0,sizeof(action)); action.sa_handler=notice;
    action.sa_flags=SA_RESTART|(suppress?SA_NOCLDSTOP:0);
    sigemptyset(&action.sa_mask);
    if(sigaction(SIGCHLD,&action,NULL)||sigaction(SIGCHLD,NULL,&query)||pipe(fds))return 3;
    pid=fork();if(pid<0)return 4;
    if(!pid) {close(fds[0]);if(write(fds[1],"S",1)!=1)_exit(7);kill(getpid(),SIGSTOP);_exit(37);}
    close(fds[1]);
    do {got=read(fds[0],&byte,1);} while(got<0 && errno==EINTR);
    if(got!=1 || byte!='S')return 5;
    /* Yield repeatedly after the child's ready byte to let its self-stop run. */
    for(i=0;i<100;i++) {
        if(usleep(10000) && errno!=EINTR) {
            /* A missing delay must fail, not race SIGCONT against SIGSTOP. */
            int error=errno;
            kill(pid,SIGKILL);
            do {got=waitpid(pid,&status,0);} while(got<0 && errno==EINTR);
            fprintf(stderr,"DELAY_UNSUPPORTED errno=%d\n",error);
            return 8;
        }
    }
    before=notices;
    if(kill(pid,SIGCONT))return 6;
    do {got=waitpid(pid,&status,0);} while(got<0 && errno==EINTR);
    printf("STOP suppress=%d flags=%#x stopped_notices=%d exit_notices=%d reaped=%d exited=%d status=%d\n",
        suppress,query.sa_flags,before,(int)notices-before,got==pid,WIFEXITED(status),WEXITSTATUS(status));
    return before!=(suppress?0:1) || notices<=before || got!=pid || !WIFEXITED(status) || WEXITSTATUS(status)!=37;
}
