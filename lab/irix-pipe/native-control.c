/* Native pipe controls; run before/after foreign fixtures under both UIDs. */
#include <sys/types.h>
#include <sys/resource.h>
#include <sys/wait.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"line %d errno %d\n",__LINE__,errno); return 1; } } while (0)
int main(void) {
    int fd[2],status; char data[8]={0};
    CHECK(pipe(fd)==0 && fcntl(fd[0],F_GETFD)==0 && fcntl(fd[1],F_GETFD)==0);
    CHECK((fcntl(fd[0],F_GETFL)&O_ACCMODE)==O_RDONLY && (fcntl(fd[1],F_GETFL)&O_ACCMODE)==O_WRONLY);
    CHECK(fcntl(fd[0],F_SETFL,O_NONBLOCK)==0);
    CHECK(read(fd[0],data,1)==-1 && errno==EAGAIN);
    CHECK(fcntl(fd[0],F_SETFL,0)==0);
    pid_t child=fork();CHECK(child>=0);
    if (!child) {
        close(fd[0]);
        int duplicate=dup(fd[1]);close(fd[1]);
        if (duplicate<0 || write(duplicate,"native",6)!=6) _exit(2);
        close(duplicate);_exit(37);
    }
    close(fd[1]);CHECK(read(fd[0],data,8)==6 && !memcmp(data,"native",6));
    CHECK(read(fd[0],data,1)==0);close(fd[0]);
    CHECK(waitpid(child,&status,0)==child && WIFEXITED(status) && WEXITSTATUS(status)==37);
    child=fork();CHECK(child>=0);
    if (!child) {
        struct rlimit limit={32,32};CHECK(setrlimit(RLIMIT_NOFILE,&limit)==0);
        int held[64],n=0,x;
        while (n<64 && (x=dup(1))>=0) held[n++]=x;
        CHECK(n>=2 && n<64 && errno==EMFILE);
        CHECK(pipe(fd)==-1 && errno==EMFILE);
        int last=held[--n];close(last);
        CHECK(pipe(fd)==-1 && errno==EMFILE);
        CHECK((x=dup(1))==last);close(x);close(held[--n]);
        CHECK(pipe(fd)==0);close(fd[0]);close(fd[1]);
        while(n)close(held[--n]);
        _exit(0);
    }
    CHECK(waitpid(child,&status,0)==child && WIFEXITED(status) && WEXITSTATUS(status)==0);
    printf("NATIVE_PIPE uid=%u io=1 fork=1 eof=1 nonblock=1 rollback=1\n",(unsigned)getuid());
    return 0;
}
