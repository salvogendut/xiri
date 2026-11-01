/* Check native mkdir, read-only media and native namespace isolation. */
#include <sys/types.h>
#include <sys/stat.h>
#include <errno.h>
#include <stdio.h>
#include <unistd.h>
int main(void) {
    char path[128];struct stat st;
    snprintf(path,sizeof(path),"/tmp/xiri-mkdir-shadow/native-%u",(unsigned)getuid());
    umask(022);
    if(mkdir(path,0777)||stat(path,&st)||!S_ISDIR(st.st_mode)||
        (st.st_mode&0777)!=0755||st.st_uid!=geteuid())return 2;
    errno=0;if(mkdir(path,0777)!=-1||errno!=EEXIST)return 3;
    if(rmdir(path))return 4;
    errno=0;if(mkdir("/cdrom/xiri-mkdir-native-test",0755)!=-1||(errno!=EROFS && !(geteuid() && errno==EACCES)))return 5;
    printf("NATIVE_MKDIR uid=%u mode=755 exists=17 readonly=%d removed=1\n",(unsigned)getuid(),errno);
    return 0;
}
