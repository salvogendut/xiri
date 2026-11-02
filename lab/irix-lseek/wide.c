#include <sys/types.h>
#include <unistd.h>
#include <fcntl.h>
#include <stdio.h>
#include <errno.h>
static void observe(int fd, off_t off, int whence) {
 off_t result; errno=0; result=lseek(fd,off,whence);
 printf("SEEK %lld %d -> %lld errno=%d\n",(long long)off,whence,(long long)result,errno);
}
int main(void) {
 int fd=open("seek-file",O_RDONLY); char c='?';
 if(fd<0)return 1;
 printf("OFF_T %u\n",(unsigned)sizeof(off_t));
 observe(fd,0,SEEK_SET);observe(fd,((off_t)1<<31),SEEK_SET);
 observe(fd,((off_t)1<<32)+7,SEEK_SET);observe(fd,-1,SEEK_CUR);
 observe(fd,0,SEEK_CUR);observe(fd,-((off_t)1<<32),SEEK_CUR);
 observe(fd,3,SEEK_SET);if(read(fd,&c,1)!=1)return 2;
 printf("BYTE %c\n",c);return close(fd)!=0;
}
