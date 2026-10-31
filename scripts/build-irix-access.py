#!/usr/bin/env python3
"""Build original access probes shared by IRIX and both NetBSD kernels."""
import importlib.util,json,os,shutil,struct,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
s=importlib.util.spec_from_file_location('base',ROOT/'scripts/build-irix-tcp.py');base=importlib.util.module_from_spec(s);s.loader.exec_module(base)
IDS=[[0,0,0,0],[1234,1234,2345,2345],[1234,0,2345,0],[0,1234,0,2345],[1234,1234,2345,3456],[1234,1234,3456,2345]]

def main():
    if os.environ.get('XIRI_TCP_TOOLBOX')!='1':
        subprocess.run(['toolbox','run','-c','xiri-iris','env','XIRI_TCP_TOOLBOX=1','PYTHONDONTWRITEBYTECODE=1','python3',str(Path(__file__).resolve())],check=True);return
    out=ROOT/'.work/irix-access/probes';out.mkdir(parents=True,exist_ok=True)
    defs=[]
    def case(name,path='tree/file',identities=(0,1),**symbols):defs.append((name,path,list(identities),symbols))
    for name in ['file','owner','owner-read','owner-exec','group','group-exec','other','none','noexec','dir','deny/file','search/file']:
        for mode in [0,1,2,4]:case(name.replace('/','-')+'-'+str(mode),'tree/'+name,range(6),MODE=mode)
    for mode in [3,5,6,7]:case('combined-'+str(mode),'tree/owner',range(6),MODE=mode)
    for name in ['hard','link','dangling','loop-a','fifo','missing','file/child','file/','dir/']:
        case('path-'+name.replace('/','-'),'tree/'+name,MODE=4)
    for mode in [8,12,16,32,256,-1]:
        case('mode-'+str(mode),MODE=mode)
        case('mode-'+str(mode)+'-missing','tree/missing',MODE=mode)
        case('mode-'+str(mode)+'-null',MODE=mode,PATHPTR=0)
    for name,path in [('empty-path',''),('dot-path','tree/./file'),('parent-path','tree/dir/../file'),('root','/'),('long-component','tree/'+'a'*256),('path-1023','./'*507+'tree/file'),('path-1024','./'*507+'tree//file'),('path-1025','./'*508+'tree/file')]:case(name,path,MODE=4)
    for name,pointer in [('null',0),('high',0x80000000),('wrap',0xfffffffe)]:case('pointer-'+name,MODE=4,PATHPTR=pointer)
    case('unaligned','xtree/file',MODE=4,PATHOFF=1)
    case('tail-nul',MODE=4,TAIL=10)
    case('tail-no-nul',MODE=4,TAIL=9)
    case('bad-stack',MODE=4,BAD_STACK=0)
    case('bad-stack-indirect',MODE=4,BAD_STACK=0xfffffff0)
    case('absolute-shadow','/tmp/xiri-access-namespace/shadow',MODE=4)
    case('absolute-fallback','/tmp/xiri-access-namespace/fallback',MODE=4)
    result={'schema':1,'identities':IDS,'sources':{n:base.digest(ROOT/n) for n in ['scripts/build-irix-access.py','lab/irix-access/probe.S','lab/irix-access/probe.ld','lab/irix-access/setup.sh']},'files':{},'cases':[]}
    for abi in ['o32','n32']:
      for indirect in [0,1]:
       for suffix,path,ids,extra in defs:
        name=abi+'-'+('indirect-' if indirect else 'direct-')+suffix
        syms=dict(CASE=len(result['cases'])+1,MODE=0,PATHOFF=0,INDIRECT=indirect);syms.update(extra)
        if abi=='n32':syms['N32']=1
        (out/'path.inc').write_text('.asciz '+json.dumps(path)+'\n')
        obj,elf=out/(name+'.o'),out/name
        flags=[x for k,v in syms.items() for x in ['--defsym',f'{k}={v}']]
        base.run('as','-EB','-mabi='+('n32' if abi=='n32' else '32'),'-mips3','-G','0','-I',out,*flags,'-o',obj,ROOT/'lab/irix-access/probe.S')
        base.run('ld','-EB','-m','elf32btsmipn32' if abi=='n32' else 'elf32btsmip','--build-id=none','-z','max-page-size=8192','-T',ROOT/'lab/irix-access/probe.ld','-o',elf,obj)
        b=bytearray(elf.read_bytes());b[7]=0;struct.pack_into('>I',b,36,0x20000021 if abi=='n32' else 0x20000101);elf.write_bytes(b);elf.chmod(0o755)
        result['files'][name]={'sha256':base.digest(elf),'bytes':len(b)}
        result['cases'].append({'name':name,'path':path,'abi':abi,'symbols':syms,'identities':ids,'record_bytes':64})
    shutil.copyfile(ROOT/'lab/irix-access/setup.sh',out/'setup.sh')
    result['files']['setup.sh']={'sha256':base.digest(out/'setup.sh'),'bytes':(out/'setup.sh').stat().st_size}
    (out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(len(defs),'variants;',len(result['cases']),'fixtures;',sum(len(c['identities']) for c in result['cases']),'executions')
if __name__=='__main__':main()
