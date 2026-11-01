/* Native parent: leave 8 MiB above the pinned kernel's reserved stack span,
 * enough for the fixture and sentinel but less than the 16 MiB ELF map. */
#include <sys/resource.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
int main(int argc,char **argv) {
    if(argc<3)return 2;
    unsigned long mib=strtoul(argv[1],NULL,10);
    if(mib!=40 && mib!=128)return 2;
    struct rlimit r={(rlim_t)mib*1024*1024,(rlim_t)mib*1024*1024};
    if(setrlimit(RLIMIT_AS,&r)){perror("setrlimit");return 2;}
    execv(argv[2],argv+2);perror("limit exec");return 2;
}
