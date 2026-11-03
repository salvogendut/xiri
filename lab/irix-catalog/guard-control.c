/* Native control: a detached child outlives its initial parent. */
#include <sys/types.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
int main(int argc, char **argv)
{
    pid_t child=fork();
    if(child<0)return 2;
    if(child)return 37;
    if(setsid()<0)return 3;
    sleep(argc>1 && !strcmp(argv[1],"linger") ? 20 : 1);
    puts("CATALOG_NATIVE_CHILD_FINISHED");
    return 0;
}
