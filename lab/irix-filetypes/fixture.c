/* Exercise the supplied desktop's filetype library without X or a GUI. */
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <sys/stat.h>
#include <unistd.h>
#include <fcntl.h>
extern void *imdFtrLoadDB(const char *);
extern void *imdFtrIconTypeFromFileName(void *, const char *);
extern void *imdFtrIconTypeFromFileDescriptor(void *, int, const char *);
extern void *imdFtrIconTypeFromTypeName(void *, const char *);
extern char *imdFtrTypeName(void *);
extern void imdFtrFreeIconType(void *);
extern void imdFtrFreeDB(void *);
int main(int argc, char **argv) {
    void *db, *type; struct stat st; int i;
    alarm(30); setbuf(stdout, NULL);
    db=imdFtrLoadDB("/usr/lib/filetype/desktop.otr");
    printf("DB %s errno=%d\n", db?"loaded":"failed", errno);
    if (!db) return 1;
    type=imdFtrIconTypeFromTypeName(db,"XMahjonggExecutable");
    printf("NAMED %s\n", type?imdFtrTypeName(type):"NULL");
    if(type) imdFtrFreeIconType(type);
    for(i=1;i<argc;i++) {
        if(stat(argv[i],&st)==0) printf("STAT %s mode=%o size=%lld\n",argv[i],(unsigned)st.st_mode,(long long)st.st_size);
        else printf("STAT_ERROR %s %d\n",argv[i],errno);
        type=imdFtrIconTypeFromFileName(db,argv[i]);
        printf("TYPE %s %s errno=%d\n",argv[i],type?imdFtrTypeName(type):"NULL",errno);
        if(type) imdFtrFreeIconType(type);
        { int fd=open(argv[i],O_RDONLY);
          if(fd>=0) { type=imdFtrIconTypeFromFileDescriptor(db,fd,argv[i]);
            printf("FDTYPE %s %s errno=%d\n",argv[i],type?imdFtrTypeName(type):"NULL",errno);
            if(type) imdFtrFreeIconType(type); close(fd); } }
    }
    imdFtrFreeDB(db);return 0;
}
