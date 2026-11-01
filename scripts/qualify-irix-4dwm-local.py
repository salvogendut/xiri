#!/usr/bin/env python3
"""Bind the original GL mmap capture and the later 4Dwm startup boundary."""
import argparse,hashlib,importlib.util,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
s=importlib.util.spec_from_file_location('tcp',ROOT/'scripts/probe-irix-tcp.py');tcp=importlib.util.module_from_spec(s);s.loader.exec_module(tcp)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(d,checkpoint):
    r=json.loads((d/'result.json').read_text());assert r['status']=='observed' and r['clean_shutdown']
    assert r['pin']==json.loads((ROOT/'lab'/checkpoint/'baseline.json').read_text())
    for p,h in r['sources'].items():assert sha(ROOT/p)==h,p
    return r

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--capture',type=Path,required=True);p.add_argument('--live',type=Path,required=True);p.add_argument('--later-fault',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    report=dict(schema=1,status='observed-boundary',qualifier_sha256=sha(Path(__file__)),graphical_success=False)
    r=read(a.capture,'irix-elfmap-subpage');assert len(r['cases'])==2 and {c['uid'] for c in r['cases']}=={0,1234}
    assert len(r['controls'])==6 and {(c['phase'],c['kind'],c.get('uid')) for c in r['controls']}=={(p,k,u) for p in ['before','after'] for k,u in [('native',0),('native',1234),('fault',None)]}
    for c in r['controls']:
        if c['kind']=='native':assert 'END exit=37 signal=0' in c['raw']
        else:
            pc=re.search(r'phase=fault signal=11 code=1 address=00000000 pc=([0-9a-f]+)',c['raw']);assert pc and int(pc[1],16)==int(c['site'],16) and 'END exit=-1 signal=9' in c['raw']
    for c in r['cases']:
        assert sha(a.capture/(str(c['uid'])+'.trace'))==c['trace_sha256']
        lines='\n'.join(c['records'])
        assert all(('a'+str(i)+'='+format(v,'016x')) in lines for i,v in enumerate([0,4096,3,0x92,3,0]))
        assert 'v0=0000000000000016 a3=0000000000000001' in lines
        assert 'phase=fault signal=11 code=1 address=00001050 pc=000000000d80e118' in lines
    report['before']=dict(directory=str(a.capture),result_sha256=sha(a.capture/'result.json'),pin=r['pin'],sources=r['sources'],controls=r['controls'],cases=[{k:v for k,v in c.items() if k!='records'} for c in r['cases']],mmap_arguments=[0,4096,3,146,3,0],return_errno=22,fault_address=4176,fault_pc=0x0d80e118)
    r=read(a.live,'irix-mmap-local');assert r['native_x11_after'] and len(r['cases'])==1 and r['stage']=='local'
    assert len(r['controls'])==2 and {c['phase'] for c in r['controls']}=={'before','after'}
    for c in r['controls']:assert c['actual']==dict(errno_bytes=0,errno=0,exit=37,signal=0,killed=0,stdout='XIRI_ABI_PROBE\n',stderr='')
    c=r['cases'][0];x=c['actual'];assert x['exit']==-1 and x['signal']==11 and x['killed']==0 and x['absent']==x['valid']==1 and not x['stdout'] and not x['stderr']
    assert c['wmcheck']=='WMCHECK_STATUS=3\nwindows were not reparented\n' and sha(a.live/'wm.xwd')==c['frame_sha256']
    raw=(a.live/'wm.kdump').read_text();calls=tcp.trace_records(raw,'irix_o32',True);returns=tcp.trace_records(raw,'irix_ret',True)
    assert any(v.startswith('syscall=1134 ') and 'a0=0 a1=0x1000 a2=0x3 a3=0x92' in v for v in calls)
    assert 'syscall=1134 v0=0 a3=0' in returns and 'PSIG  SIGSEGV SIG_DFL' in raw
    report['after']=dict(directory=str(a.live),result_sha256=sha(a.live/'result.json'),pin=r['pin'],sources=r['sources'],staged=r['staged'],controls=r['controls'],cases=r['cases'],trace_sha256=sha(a.live/'wm.kdump'),calls=calls,returns=returns,clean_shutdown=True)
    if a.later_fault:
        r=read(a.later_fault,'irix-mmap-local');assert len(r['cases'])==2 and len(r['controls'])==6
        for c in r['cases']:
            assert sha(a.later_fault/(str(c['uid'])+'.trace'))==c['trace_sha256']
            lines='\n'.join(c['records']);assert 'v0=0000000000000000 a3=0000000000000000' in lines and 'STOP phase=fault signal=11' in lines and 'END exit=-1 signal=9' in lines
            assert 'STOP phase=fault signal=11 code=1 address=00200e00 pc=000000000fb0d92c' in lines
        report['later_fault']=dict(directory=str(a.later_fault),result_sha256=sha(a.later_fault/'result.json'),sources=r['sources'],controls=r['controls'],cases=r['cases'],clean_shutdown=True)
    a.output.write_text(json.dumps(report,indent=2)+'\n');print('GL mmap succeeds; later startup fault and unmanaged-window check retained')
if __name__=='__main__':main()
