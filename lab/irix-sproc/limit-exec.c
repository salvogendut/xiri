/* Native resource ceiling makes leaked automatic sproc stacks observable. */
#include <sys/resource.h>
#include <unistd.h>

int main(int argc, char **argv) {
    struct rlimit limit;
    if(argc!=2)return 98;
    if(getrlimit(RLIMIT_AS,&limit))return 97;
    /* LP64 reserves a 120 MiB main-stack region even with a smaller soft
     * limit. Leave room for one child, but not twelve leaked stacks. */
    limit.rlim_cur=192*1024*1024;
    if(setrlimit(RLIMIT_AS,&limit))return 96;
    if(getrlimit(RLIMIT_STACK,&limit))return 95;
    limit.rlim_cur=16*1024*1024;
    if(setrlimit(RLIMIT_STACK,&limit))return 94;
    execv(argv[1],argv+1);
    return 93;
}
