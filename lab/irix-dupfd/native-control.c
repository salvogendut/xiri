/* Native F_DUPFD and pipe controls; run before/after foreign fixtures under both UIDs. */
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
    int source=open("input.txt",O_RDONLY);CHECK(source>=0);
    char expect[4],actual[4];CHECK(pread(source,expect,4,0)==4);
    CHECK(fcntl(source,F_SETFD,FD_CLOEXEC|FD_CLOFORK)==0);
    int copy=fcntl(source,F_DUPFD,16);CHECK(copy==16 && fcntl(copy,F_GETFD)==0);
    CHECK(fcntl(source,F_GETFD)==(FD_CLOEXEC|FD_CLOFORK));
    CHECK(read(source,actual,1)==1 && read(copy,actual+1,1)==1 && read(source,actual+2,1)==1);
    CHECK(!memcmp(expect,actual,3));
    CHECK(fcntl(copy,F_SETFL,O_APPEND)==0 && (fcntl(source,F_GETFL)&O_APPEND));
    close(source);CHECK(read(copy,actual+3,1)==1 && actual[3]==expect[3]);close(copy);
    CHECK(pipe(fd)==0 && fcntl(fd[0],F_GETFD)==0 && fcntl(fd[1],F_GETFD)==0);
    CHECK((fcntl(fd[0],F_GETFL)&O_ACCMODE)==O_RDONLY && (fcntl(fd[1],F_GETFL)&O_ACCMODE)==O_WRONLY);
    CHECK(fcntl(fd[0],F_SETFL,O_NONBLOCK)==0);
    CHECK(read(fd[0],data,1)==-1 && errno==EAGAIN);
    CHECK(fcntl(fd[0],F_SETFL,0)==0);
    pid_t child=fork();CHECK(child>=0);
    if (!child) {
        close(fd[0]);
        int duplicate=fcntl(fd[1],F_DUPFD,8);close(fd[1]);
        if (duplicate!=8 || write(duplicate,"native",6)!=6) _exit(2);
        close(duplicate);_exit(37);
    }
    close(fd[1]);CHECK(read(fd[0],data,8)==6 && !memcmp(data,"native",6));
    CHECK(read(fd[0],data,1)==0);close(fd[0]);
    CHECK(waitpid(child,&status,0)==child && WIFEXITED(status) && WEXITSTATUS(status)==37);
    child=fork();CHECK(child>=0);
    if (!child) {
        struct rlimit limit={32,32};CHECK(setrlimit(RLIMIT_NOFILE,&limit)==0);
        int held[64],n=0,x;
        while (n<64 && (x=fcntl(1,F_DUPFD,0))>=0) held[n++]=x;
        CHECK(n>=2 && n<64 && errno==EMFILE);
        CHECK(fcntl(1,F_DUPFD,0)==-1 && errno==EMFILE);
        CHECK(fcntl(1,F_DUPFD,32)==-1 && errno==EINVAL);
        CHECK(fcntl(-1,F_DUPFD,-1)==-1 && errno==EBADF);
        CHECK(pipe(fd)==-1 && errno==EMFILE);
        int last=held[--n];close(last);
        CHECK(pipe(fd)==-1 && errno==EMFILE);
        CHECK((x=fcntl(1,F_DUPFD,0))==last);close(x);close(held[--n]);
        CHECK(pipe(fd)==0);close(fd[0]);close(fd[1]);
        while(n)close(held[--n]);
        _exit(0);
    }
    CHECK(waitpid(child,&status,0)==child && WIFEXITED(status) && WEXITSTATUS(status)==0);
    printf("NATIVE_DUPFD uid=%u allocation=1 flags=1 offset=1 fork=1 eof=1 rollback=1\n",(unsigned)getuid());
    return 0;
}
