/* Native control: repeat on the old and new NetBSD cores. The signal
 * counts are observations; NOCLDSTOP/CONT policy differs between systems. */
#include <sys/types.h>
#include <sys/wait.h>
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

static volatile sig_atomic_t notices;
static volatile sig_atomic_t codes[4], statuses[4];

static void notice(int sig,siginfo_t *si,void *context)
{
    int n=notices++;
    (void)sig;(void)context;
    if(n<4){codes[n]=si->si_code;statuses[n]=si->si_status;}
}

static int token(int fd,int write_token)
{
    char byte=42;ssize_t n;
    do {n=write_token?write(fd,&byte,1):read(fd,&byte,1);} while(n<0&&errno==EINTR);
    return n!=1;
}

int main(int argc,char **argv)
{
    struct sigaction action;
    sigset_t block;
    siginfo_t si;
    int ready[2],gate[2],stopped,continued,exited,status,error=0;
    int suppress=argc>1&&!strcmp(argv[1],"suppress");
    pid_t pid,got;
    memset(&action,0,sizeof(action));action.sa_sigaction=notice;
    action.sa_flags=SA_SIGINFO|(suppress?SA_NOCLDSTOP:0);
    sigemptyset(&action.sa_mask);sigemptyset(&block);sigaddset(&block,SIGCHLD);
    if(sigaction(SIGCHLD,&action,NULL)||sigprocmask(SIG_BLOCK,&block,NULL)||
        pipe(ready)||pipe(gate))return 2;
    pid=fork();if(pid<0)return 3;
    if(!pid) {
        close(ready[0]);close(gate[1]);
        if(token(ready[1],1)||kill(getpid(),SIGSTOP)||token(ready[1],1)||
            token(gate[0],0))_exit(80);
        _exit(37);
    }
    close(ready[1]);close(gate[0]);
    if(token(ready[0],0)||waitid(P_PID,pid,&si,WSTOPPED|WNOWAIT))goto failed;
    if(si.si_pid!=pid||si.si_code!=CLD_STOPPED||si.si_status!=SIGSTOP)goto failed;
    if(waitid(P_PID,pid,&si,WSTOPPED)||sigprocmask(SIG_UNBLOCK,&block,NULL))goto failed;
    stopped=notices;
    if(sigprocmask(SIG_BLOCK,&block,NULL)||kill(pid,SIGCONT)||token(ready[0],0))goto failed;
    if(waitid(P_PID,pid,&si,WCONTINUED|WNOWAIT)||si.si_pid!=pid||
        si.si_code!=CLD_CONTINUED||si.si_status!=SIGCONT)goto failed;
    if(waitid(P_PID,pid,&si,WCONTINUED)||sigprocmask(SIG_UNBLOCK,&block,NULL))goto failed;
    continued=notices;
    if(sigprocmask(SIG_BLOCK,&block,NULL)||token(gate[1],1)||
        waitid(P_PID,pid,&si,WEXITED|WNOWAIT))goto failed;
    if(si.si_pid!=pid||si.si_code!=CLD_EXITED||si.si_status!=37)goto failed;
    if(sigprocmask(SIG_UNBLOCK,&block,NULL))goto failed;
    exited=notices;
    do {got=waitpid(pid,&status,0);} while(got<0&&errno==EINTR);
    if(got!=pid||!WIFEXITED(status)||WEXITSTATUS(status)!=37)goto failed;
    errno=0;if(waitpid(pid,&status,WNOHANG)!=-1||errno!=ECHILD)goto failed;
    printf("CHILD suppress=%d stopped=%d continued=%d exited=%d reaped=1 second=ECHILD",
        suppress,stopped,continued,exited);
    for(int i=0;i<exited&&i<4;i++)printf(" notice%d=%d/%d",i,(int)codes[i],(int)statuses[i]);
    putchar('\n');
    close(ready[0]);close(gate[1]);
    return 0;
failed:
    error=errno;kill(pid,SIGKILL);
    do {got=waitpid(pid,&status,0);} while(got<0&&errno==EINTR);
    fprintf(stderr,"CHILD_FAILED errno=%d reaped=%d\n",error,got==pid);
    return 1;
}
