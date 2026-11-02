#include "emul-path.h"
#include <assert.h>
#include <stdio.h>

static void dirs(const std::string& path)
{
    for (std::string::size_type i=1; i<path.size(); ++i)
        if (path[i]=='/') mkdir(path.substr(0,i).c_str(),0755);
    mkdir(path.c_str(),0755);
}
static void file(const std::string& path)
{
    dirs(path.substr(0,path.rfind('/')));
    FILE *f=fopen(path.c_str(),"w"); assert(f); fputs("test\n",f); fclose(f);
}
int main(int argc,char **argv)
{
    assert(argc==2);
    const std::string base(argv[1]), root=base+"/root";
    const std::string app="/usr/freeware/bin/xmahjongg";
    file(root+app);
    assert(xiri_fam_path(NULL,app.c_str(),false)==app);
    assert(xiri_fam_path("/",app.c_str(),false)==app);
    assert(xiri_fam_path(root.c_str(),app.c_str(),false)==root+app);
    assert(xiri_fam_path((root+"/").c_str(),app.c_str(),false)==root+app);
    assert(xiri_fam_path(root.c_str(),(root+app).c_str(),false)==root+app);
    assert(xiri_fam_path(root.c_str(),"/usr/freeware/bin/new",false)==root+"/usr/freeware/bin/new");
    assert(symlink("/usr/freeware",(root+"/absolute").c_str())==0);
    assert(symlink("usr/freeware",(root+"/relative").c_str())==0);
    assert(xiri_fam_path(root.c_str(),"/absolute/bin/xmahjongg",false)==root+app);
    assert(xiri_fam_path(root.c_str(),"/relative/bin/xmahjongg",false)==root+app);
    assert(xiri_fam_path(root.c_str(),"/absolute",true)==root+"/usr/freeware");
    assert(xiri_fam_path(root.c_str(),"/absolute",false)==root+"/absolute");
    assert(xiri_fam_path(root.c_str(),"/relative/../freeware/bin/xmahjongg",false)==root+app);
    const std::string native=base+"/home/file";
    file(native);
    assert(xiri_fam_path(root.c_str(),native.c_str(),false)==native);
    file(root+native);
    assert(xiri_fam_path(root.c_str(),native.c_str(),false)==root+native);
    assert(unlink((root+native).c_str())==0);
    assert(xiri_fam_path(root.c_str(),native.c_str(),false)==native);
    assert(xiri_fam_path(root.c_str(),(base+"/native-only/new").c_str(),false)==base+"/native-only/new");
    puts("FAM_EMUL_PATH_PASS 15");
    return 0;
}
