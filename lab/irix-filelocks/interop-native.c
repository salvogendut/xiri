/* Native parent proves both personalities use the same vnode lock table. */
#include <sys/types.h>
#include <sys/wait.h>
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define CHECK(x) do { if (!(x)) { fprintf(stderr,"line %d: %s errno=%d\n",__LINE__,#x,errno); exit(1); } } while (0)
static void receive(int fd, void *data, size_t bytes)
{
    char *p=data;
    while(bytes) { ssize_t n=read(fd,p,bytes);CHECK(n>0);p+=n;bytes-=(size_t)n; }
}
int main(int argc,char **argv)
{
    CHECK(argc==3);
    alarm(10);
    int wide=strcmp(argv[2],"n32")==0;
    int fd=open("tree/file",O_RDWR), down[2],up[2];
    CHECK(fd>=0 && pipe(down)==0 && pipe(up)==0);
    struct flock lock={.l_type=F_WRLCK,.l_whence=SEEK_SET,.l_start=7,.l_len=19};
    CHECK(fcntl(fd,F_SETLK,&lock)==0);
    pid_t child=fork();CHECK(child>=0);
    if(child==0) {
        CHECK(dup2(down[0],0)==0 && dup2(up[1],1)==1);
        close(down[0]);close(down[1]);close(up[0]);close(up[1]);close(fd);
        execl(argv[1],argv[1],(char *)NULL);_exit(127);
    }
    close(down[0]);close(up[1]);
    uint32_t r[24];receive(up[0],r,sizeof(r));
    CHECK(r[0]==0 && r[2]==0 && r[8]==(2U<<16));
    if(wide)CHECK(r[10]==0 && r[11]==7 && r[12]==0 && r[13]==19 && r[14]==0 && r[15]==(uint32_t)getpid());
    else CHECK(r[9]==7 && r[10]==19 && r[11]==0 && r[12]==(uint32_t)getpid());
    receive(up[0],r,12);CHECK(r[0]==13 && r[2]==1);
    lock.l_type=F_UNLCK;CHECK(fcntl(fd,F_SETLK,&lock)==0);
    CHECK(write(down[1],"a",1)==1);
    receive(up[0],r,12);CHECK(r[0]==0 && r[2]==0);
    lock=(struct flock){.l_type=F_WRLCK,.l_whence=SEEK_SET,.l_len=100};
    CHECK(fcntl(fd,F_GETLK,&lock)==0);
    CHECK(lock.l_type==F_WRLCK && lock.l_start==0 && lock.l_len==100 && lock.l_pid==child);
    CHECK(fcntl(fd,F_SETLK,&lock)==-1 && (errno==EAGAIN || errno==EACCES));
    CHECK(write(down[1],"b",1)==1);
    int status;CHECK(waitpid(child,&status,0)==child && WIFEXITED(status) && WEXITSTATUS(status)==0);
    CHECK(fcntl(fd,F_SETLK,&lock)==0);
    puts("native/IRIX lock interoperability passed");
    return 0;
}
