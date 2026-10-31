/* Native descendant that must be stopped when its launching parent exits. */
#include <sys/types.h>
#include <unistd.h>
int main(void) {
    pid_t child=fork();if(child<0)return 2;
    if(child==0){sleep(60);_exit(3);}
    return write(1,"XIRI_GROUP_CONTROL\n",19)==19?0:4;
}
