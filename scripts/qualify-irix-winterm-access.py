#!/usr/bin/env python3
"""Validate xwsh's progression from locale/font initialization to PTY setup."""
import argparse,collections,hashlib,importlib.util,json,re,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
s=importlib.util.spec_from_file_location('tcp',ROOT/'scripts/probe-irix-tcp.py');tcp=importlib.util.module_from_spec(s);s.loader.exec_module(tcp)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def events(text):
    result=[]
    for block in re.split(r'(?=^\s*\d+\s+\d+\s+\S+\s+MISC\s+irix_o32:)',text,flags=re.M):
        calls=tcp.trace_records(block,'irix_o32',True)
        if not calls:continue
        assert len(calls)==1
        call={k:int(v,0) for k,v in re.findall(r'(syscall|pc|a[0-3])=(0x[0-9a-f]+|\d+)',calls[0])}
        ret=tcp.trace_records(block,'irix_ret',True);assert len(ret)<=1
        value={k:int(v,0) for k,v in re.findall(r'(syscall|v0|a3)=(0x[0-9a-f]+|\d+)',ret[0])} if ret else None
        result.append(dict(call=call,ret=value,paths=re.findall(r' NAMI\s+"([^\n"]+)"',block)))
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runs',nargs=2,type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    pin=json.loads((ROOT/'lab/irix-access/baseline.json').read_text())
    manifest=json.loads((ROOT/'lab/irix-winterm/manifest.json').read_text());libc=ROOT/'.work/irix-winterm/root/usr/lib32/libc.so.1'
    assert sha(libc)==manifest['files']['/usr/lib32/libc.so.1']['sha256']
    b=libc.read_bytes();base=struct.unpack_from('>I',b,28)[0];n=struct.unpack_from('>H',b,44)[0];literal=0xfb488a8;resolved=None
    for i in range(n):
        h=struct.unpack_from('>8I',b,base+i*32)
        if h[0]==1 and h[2]<=literal<h[2]+h[4]:
            off=h[1]+literal-h[2];resolved=b[off:off+64].split(b'\0')[0].decode()
    assert resolved=='/dev/ptc'
    report=dict(schema=1,status='locale-font-boundary-cleared-pty-setup-blocked',kernel_pin=pin,runs=[],terminal_window_qualified=False,pty_open=dict(path=resolved,path_evidence='constant in the pinned original libc PT_LOAD, referenced by traced open argument',address=hex(literal),flags=6,irix_errno=22),next_priority='Measure PTY allocation and terminal control; qualify native shell/input before 4Dwm evaluation')
    seen=set()
    for d in a.runs:
        r=json.loads((d/'result.json').read_text());assert r['status']=='observed' and r['clean_shutdown'] and r['native_x11_after'] and r['pin']==pin
        for path,h in r['sources'].items():assert sha(ROOT/path)==h
        assert r['mode'] not in seen;seen.add(r['mode'])
        assert len(r['controls'])==2 and len(r['native_font_controls'])==2
        assert {c['phase'] for c in r['controls']}=={c['phase'] for c in r['native_font_controls']}=={'before','after'}
        for c in r['controls']:assert c['guards_intact'] and c['entry_exit']==37 and 'Map State: IsViewable' in c['window'] and not c['stderr']
        for c in r['native_font_controls']:assert 'Map State: IsViewable' in c['window'] and not c['stderr']
        assert len(r['cases'])==4 and {(c['uid'],c['font']) for c in r['cases']}=={(uid,font) for uid in [0,1234] for font in [None,'fixed']}
        cases=[]
        for c in r['cases']:
            assert c['actual']==dict(errno_bytes=0,errno=0,exit=255,signal=0,killed=0,stdout='',stderr="/emul/irix/usr/sbin/xwsh: Invalid argument: can't start command\n")
            assert '0 children.' in c['tree'] and 'fault' not in c
            f=d/(c['name']+'.kdump');ev=events(f.read_text());assert ev
            access=[];unsupported=collections.Counter();fds={};reads=collections.Counter();ptys=[]
            for e in ev:
                call,ret=e['call'],e['ret'];number=call['syscall']
                if ret and ret['a3'] and ret['v0']==89:unsupported[str(ret['syscall'])]+=1
                if number==1033:
                    assert ret and ret['v0']!=89
                    access.append(dict(paths=e['paths'],mode=call['a1'],v0=ret['v0'],a3=ret['a3']))
                if number==1005 and ret:
                    if call['a0']==literal:
                        assert call['a1']==6 and ret['v0']==22 and ret['a3']==1 and not e['paths'];ptys.append(e)
                    if not ret['a3'] and e['paths']:fds[ret['v0']]=e['paths'][0]
                if number==1003 and ret and not ret['a3'] and call['a0'] in fds:
                    reads[fds[call['a0']]]+=ret['v0']
                if number==1006:fds.pop(call['a0'],None)
            for path,size in [('/emul/irix/usr/lib/X11/locale/C/XLC_LOCALE',763),('/emul/irix/usr/lib/X11/app-defaults/XWsh',12699)]:
                assert any(path in x['paths'] and x['v0']==0 and x['a3']==0 for x in access)
                assert reads[path]==size,(c['name'],path,reads)
            assert len(ptys)==1 and unsupported['1019']>0
            assert sha(d/(c['name']+'.xwd'))==c['frame_sha256']
            cases.append(dict(name=c['name'],uid=c['uid'],font=c['font'],actual=c['actual'],window_children=0,access=access,resource_read_bytes=dict(reads),unsupported_syscalls=dict(unsupported),trace_sha256=sha(f),frame_sha256=c['frame_sha256']))
        report['runs'].append(dict(directory=str(d),mode=r['mode'],clean_shutdown=True,result_sha256=sha(d/'result.json'),controls=r['controls'],native_font_controls=r['native_font_controls'],cases=cases,sources=r['sources']))
    assert seen=={'ci','ordinary'}
    report['qualifier_sha256']=sha(Path(__file__));a.output.write_text(json.dumps(report,indent=2)+'\n');print('Eight xwsh starts passed locale/font initialization and stopped at PTY setup')
if __name__=='__main__':main()
