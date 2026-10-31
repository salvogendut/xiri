#!/usr/bin/env python3
"""Build original guarded xstat fixtures, identical on IRIX and NetBSD."""
import importlib.util,json,os,shutil,struct,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
s=importlib.util.spec_from_file_location('base',ROOT/'scripts/build-irix-tcp.py');base=importlib.util.module_from_spec(s);s.loader.exec_module(base)

def main():
    if os.environ.get('XIRI_TCP_TOOLBOX')!='1':
        subprocess.run(['toolbox','run','-c','xiri-iris','env','XIRI_TCP_TOOLBOX=1','PYTHONDONTWRITEBYTECODE=1','python3',str(Path(__file__).resolve())],check=True);return
    out=ROOT/'.work/irix-xstat/probes';out.mkdir(parents=True,exist_ok=True)
    defs=[]
    def case(name,path='tree/file',**symbols):defs.append((name,path,symbols))
    for name in ['file','empty','dir','hard','link','dangling','loop-a','fifo','char','block','large','deny/file','missing','file/child','file/','dir/']:
        case(name.replace('/','-') or 'file',path='tree/'+name)
    case('absolute-shadow',path='/tmp/xiri-xstat-namespace/shadow')
    case('absolute-fallback',path='/tmp/xiri-xstat-namespace/fallback')
    for name,path in [('empty-path',''),('dot-path','tree/./file'),('parent-path','tree/dir/../file'),('long-component','tree/'+'a'*256),('path-1023','./'*507+'tree/file'),('path-1024','./'*507+'tree//file'),('path-1025','./'*508+'tree/file')]:case(name,path)
    for name,symbols in [('null-path',dict(PATHPTR=0)),('high-path',dict(PATHPTR=0x80000000)),('wrap-path',dict(PATHPTR=0xfffffffe)),('null-out',dict(BUFPTR=0)),('high-out',dict(BUFPTR=0x80000000)),('wrap-out',dict(BUFPTR=0xfffffff0)),('readonly-out',dict(READONLY=1)),('align-1',dict(ALIGN=1)),('align-2',dict(ALIGN=2)),('align-4',dict(ALIGN=4)),('align-7',dict(ALIGN=7)),('bad-stack',dict(BAD_STACK=0))]:case(name,**symbols)
    for path in ['missing','file/child','deny/file']:
        case(path.replace('/','-')+'-null-out',path='tree/'+path,BUFPTR=0)
    for tail in [0,1,4,8,64,128,135,136,137,148,151,152,153]:case('tail-'+str(tail),TAIL=tail)
    for version in [0,1,3,4,-1]:
        case('version-'+str(version),VERSION=version)
        case('version-'+str(version)+'-missing',path='tree/missing',VERSION=version)
        case('version-'+str(version)+'-bad-path',VERSION=version,PATHPTR=0)
        case('version-'+str(version)+'-bad-out',VERSION=version,BUFPTR=0)
    for name,path,symbols in [('large','tree/large',{}),('align-1','tree/file',{'ALIGN':1}),('readonly','tree/file',{'READONLY':1}),('tail-1','tree/file',{'TAIL':1}),('tail-151','tree/file',{'TAIL':151}),('tail-152','tree/file',{'TAIL':152}),('file-slash','tree/file/',{}),('deny-null','tree/deny/file',{'BUFPTR':0})]:case('v3-'+name,path,VERSION=3,**symbols)
    result={'schema':1,'sources':{n:base.digest(ROOT/n) for n in ['scripts/build-irix-xstat.py','lab/irix-xstat/probe.S','lab/irix-xstat/probe.ld','lab/irix-xstat/setup.sh']},'files':{},'cases':[]}
    for abi in ['o32','n32']:
      for indirect in [0,1]:
       for suffix,path,extra in defs:
        name=abi+'-'+('indirect-' if indirect else 'direct-')+suffix
        syms=dict(CASE=len(result['cases'])+1,VERSION=2,INDIRECT=indirect,ALIGN=0);syms.update(extra)
        if abi=='n32':syms['N32']=1
        (out/'path.inc').write_text('.asciz '+json.dumps(path)+'\n')
        obj,elf=out/(name+'.o'),out/name
        flags=[x for k,v in syms.items() for x in ['--defsym',f'{k}={v}']]
        base.run('as','-EB','-mabi='+('n32' if abi=='n32' else '32'),'-mips3','-G','0','-I',out,*flags,'-o',obj,ROOT/'lab/irix-xstat/probe.S')
        base.run('ld','-EB','-m','elf32btsmipn32' if abi=='n32' else 'elf32btsmip','--build-id=none','-z','max-page-size=8192','-T',ROOT/'lab/irix-xstat/probe.ld','-o',elf,obj)
        b=bytearray(elf.read_bytes());b[7]=0;struct.pack_into('>I',b,36,0x20000021 if abi=='n32' else 0x20000101);elf.write_bytes(b);elf.chmod(0o755)
        result['files'][name]={'sha256':base.digest(elf),'bytes':len(b)}
        result['cases'].append({'name':name,'path':path,'abi':abi,'symbols':syms,'record_bytes':576})
    shutil.copyfile(ROOT/'lab/irix-xstat/setup.sh',out/'setup.sh')
    result['files']['setup.sh']={'sha256':base.digest(out/'setup.sh'),'bytes':(out/'setup.sh').stat().st_size}
    (out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(len(defs),'variants;',len(result['cases']),'xstat fixtures built')
if __name__=='__main__':main()
