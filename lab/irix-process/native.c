/* Independent native fork/mask/file/COW control for the supervisor. */
#include <sys/types.h>
#include <sys/wait.h>
#include <fcntl.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
static uint32_t r[64]={0x58505243};
#if FORK_CONTROL
static volatile uint32_t cow=0x12345678;
#endif
static void emit(int role) {
    r[55]=role;r[56]=getuid();r[57]=geteuid();r[58]=getgid();r[59]=getegid();r[60]=getpid();r[61]=getppid();
    if(write(1,r,sizeof(r))!=sizeof(r))_exit(90);
}
static void pause_input(void){char c;if(read(0,&c,1)!=1)_exit(91);}
int main(void) {
    sigset_t s;sigemptyset(&s);sigaddset(&s,SIGUSR1);sigaddset(&s,SIGCHLD);
    if(sigprocmask(SIG_BLOCK,&s,NULL))return 2;
#if !FORK_CONTROL
    emit(0);pause_input();return 0;
#else
    int fd=open("shared",O_RDONLY);if(fd<0)return 3;
    pid_t child=fork();if(child<0)return 4;
    if(child==0){char c=0;cow=0x87654321;r[33]=cow;sigemptyset(&s);sigaddset(&s,SIGUSR1);if(sigprocmask(SIG_UNBLOCK,&s,NULL)||read(fd,&c,1)!=1)_exit(5);r[47]=c;emit(1);pause_input();_exit(37);}
    emit(0);pause_input();int st;if(waitpid(child,&st,0)!=child||!WIFEXITED(st)||WEXITSTATUS(st)!=37)return 6;
    char c=0;if(read(fd,&c,1)!=1||c!='B'||cow!=0x12345678)return 7;
    r[51]=c;r[52]=cow;r[63]=child;emit(2);close(fd);return 0;
#endif
}
