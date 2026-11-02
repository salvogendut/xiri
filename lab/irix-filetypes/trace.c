/* Temporary observer: original vendor APIs and data remain unchanged. */
#include <dlfcn.h>
#include <stdio.h>
typedef void *(*byname)(void *, const char *);
typedef void *(*byfd)(void *, int, const char *);
typedef char *(*typename_fn)(void *);
static void *original(void) { static void *h; if(!h)h=dlopen("/usr/lib32/internal/libimdFtrDB.so",RTLD_LAZY); return h; }
static void report(const char *entry,const char *path,void *type) {
 typename_fn name=(typename_fn)dlsym(original(),"imdFtrTypeName");
 fprintf(stderr,"XIRI_FTR %s path=%s type=%s\n",entry,path?path:"NULL",type&&name?name(type):"NULL");
}
void *imdFtrIconTypeFromFileName(void *db,const char *path) {
 byname fn=(byname)dlsym(original(),"imdFtrIconTypeFromFileName");
 void *r=fn(db,path);report("filename",path,r);return r;
}
void *imdFtrIconTypeFromTypeName(void *db,const char *path) {
 byname fn=(byname)dlsym(original(),"imdFtrIconTypeFromTypeName");
 void *r=fn(db,path);report("typename",path,r);return r;
}
void *imdFtrIconTypeFromFileDescriptor(void *db,int fd,const char *path) {
 byfd fn=(byfd)dlsym(original(),"imdFtrIconTypeFromFileDescriptor");
 void *r=fn(db,fd,path);report("descriptor",path,r);return r;
}
