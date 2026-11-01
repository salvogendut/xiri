#!/usr/bin/env python3
"""Validate the observed 4Dwm loader boundary before and after subpage support."""
import argparse,hashlib,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
s=importlib.util.spec_from_file_location('tcp',ROOT/'scripts/probe-irix-tcp.py');tcp=importlib.util.module_from_spec(s);s.loader.exec_module(tcp)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('baseline',type=Path);p.add_argument('subpage',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    report=dict(schema=1,status='observed-boundary',qualifier_sha256=sha(Path(__file__)),runs=[])
    for stage,d in [('shell',a.baseline),('subpage',a.subpage)]:
        r=json.loads((d/'result.json').read_text());assert r['status']=='observed' and r['clean_shutdown'] and r['stage']==stage
        assert r['pin']==json.loads((ROOT/'lab'/('irix-shell' if stage=='shell' else 'irix-elfmap-subpage')/'baseline.json').read_text())
        for path,h in r['sources'].items():assert sha(ROOT/path)==h,path
        assert len(r['controls'])==2
        for c in r['controls']:assert c['actual']==dict(errno_bytes=0,errno=0,exit=37,signal=0,killed=0,stdout='XIRI_ABI_PROBE\n',stderr='')
        x=dict(directory=str(d),result_sha256=sha(d/'result.json'),stage=stage,pin=r['pin'],sources=r['sources'],staged=r['staged'],controls=r['controls'],cases=r['cases'],clean_shutdown=True)
        if stage=='shell':
            assert len(r['cases'])==2 and r['cases'][0]['name']=='native'
            records=r['cases'][1]['records'];assert records[-1]=='END exit=1 signal=0'
            assert 'PHDR index=1 type=1 offset=00011000 vaddr=09851000 paddr=09851000 filesz=00002000 memsz=00002000 flags=6 align=00001000' in records
            assert records[-4]=='RETURN stub=rld request=68 v0=0000000000000008 a3=0000000000000001'
            for c in r['cases']:assert sha(d/(c['name']+'.trace'))==c['trace_sha256']
        else:
            assert r['native_x11_after'] and len(r['cases'])==1
            c=r['cases'][0];assert c['actual']['exit']==-1 and c['actual']['signal']==11 and c['actual']['killed']==0 and c['actual']['absent']==c['actual']['valid']==1
            assert not c['actual']['stdout'] and c['actual']['stderr']=='gl: warning, mmap failed, got 0xffffffff.\n'
            raw=(d/'wm.kdump').read_text();assert 'PSIG  SIGSEGV SIG_DFL' in raw and '/emul/irix/usr/lib32/libXpm.so.1' in raw and '/emul/irix/usr/lib32/libGLcore.so' in raw
            x['calls']=tcp.trace_records(raw,'irix_o32',True);x['returns']=tcp.trace_records(raw,'irix_ret',True)
            assert 'syscall=1134 v0=0x16 a3=1' in x['returns']
            assert any(v.startswith('syscall=1134 ') and 'a0=0 a1=0x1000 a2=0x3 a3=0x92' in v for v in x['calls'])
            assert sha(d/'wm.xwd')==c['frame_sha256'];x['trace_sha256']=sha(d/'wm.kdump')
        report['runs'].append(x)
    a.output.write_text(json.dumps(report,indent=2)+'\n');print('Original 4Dwm loader failure removed; subsequent mmap/fault boundary confirmed')
if __name__=='__main__':main()
