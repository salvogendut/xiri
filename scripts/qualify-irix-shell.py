#!/usr/bin/env python3
"""Compare explicit shell-interface records and validate interactive shell evidence."""
import argparse,hashlib,json,re,struct,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def canonical(data,case,ids,limit=None):
    w=list(struct.unpack('>64I',data))
    assert w[:2]==[0x5853484c,case['symbols']['CASE']]
    assert w[56:60]==ids and w[60]>1 and w[61]>0 and w[62:]==[0,0]
    if case['symbols']['KIND']==0:
        assert w[44]==w[60] and w[50]==w[60] and w[51]==w[61]
        assert w[5]>0
        if limit is not None:assert w[5]==limit
        w[5]=0 # Native descriptor limit is an explicit host policy.
        w[44]=w[50]=w[51]=0
    w[60]=w[61]=0
    return w

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference',type=Path,required=True)
    p.add_argument('runs',nargs='+',type=Path)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--png',type=Path)
    a=p.parse_args();ref=json.loads((a.reference/'result.json').read_text())
    assert ref['status']=='observed' and ref['clean_shutdown'] and ref['scope']=='full'
    assert ref['harness_sha256']==sha(ROOT/'scripts/probe-irix-reference-shell.py')
    manifest=ref['manifest'];cases={c['name']+'-'+str(i):(c,i) for c in manifest['cases'] for i in c['identities']}
    assert len(cases)==152 and len(ref['observations'])==152
    oracle={o['name']:o for o in ref['observations']};assert oracle.keys()==cases.keys()
    exported=json.loads((ROOT/'lab/irix-shell/reference-records.json').read_text())
    assert exported['result_sha256']==sha(a.reference/'result.json')
    assert exported['harness_sha256']==ref['harness_sha256'] and exported['manifest_sources']==manifest['sources']
    expected=[]
    for o in ref['observations']:
        raw=bytes.fromhex(o['stdout_hex']);item=dict(name=o['name'],exit=o['exit'],stderr=o['stderr'])
        if len(raw)==256:
            w=list(struct.unpack('>64I',raw));c,i=cases[o['name']]
            canonical(raw,c,manifest['identities'][i])
            if c['symbols']['KIND']==0:w[44]=w[50]=w[51]=0
            w[60]=w[61]=0;item['record']=w
        else:item['stdout']=raw.decode()
        expected.append(item)
    assert exported['cases']==expected
    result=dict(status='passed',reference=str(a.reference),reference_result_sha256=sha(a.reference/'result.json'),reference_records_sha256=sha(ROOT/'lab/irix-shell/reference-records.json'),qualifier_sha256=sha(Path(__file__)),interface_cases=0,oracle_equal=0,native_policy=0,control_cases=0,native_ctty_cases=0,apps=[],runs=[])
    for directory in a.runs:
        r=json.loads((directory/'result.json').read_text())
        assert r['status']=='observed-uncompared' and r['clean_shutdown'] and not r['smoke']
        assert r['manifest']==manifest
        for path,h in r['sources'].items():
            # Interface captures predate app-only environment/PTY handoff fixes.
            # The independently decoded records and native controls remain
            # bound to the unchanged fixture/helper/kernel hashes.
            if r['scope']=='interfaces' and path in ['scripts/probe-irix-shell.py','lab/irix-shell/handoff.c']:continue
            assert sha(ROOT/path)==h,path
        for path,h in manifest['sources'].items():assert sha(ROOT/path)==h,path
        base='o32-baseline.json' if r['kernel_abi']=='o32' else 'baseline.json'
        assert r['pin']==json.loads((ROOT/'lab/irix-shell'/base).read_text())
        want={n for n,(c,i) in cases.items() if r['kernel_abi']=='lp64' or c['abi']=='o32'} if r['scope']!='apps' else set()
        assert len(r['observations'])==len(want) and {o['name'] for o in r['observations']}==want
        for o in r['observations']:
            c,i=cases[o['name']];obs=o['actual'];original=oracle[o['name']]
            data=bytes.fromhex(obs['stdout_hex']);raw=bytes.fromhex(original['stdout_hex'])
            assert obs['errno_bytes']==obs['errno']==obs['signal']==obs['killed']==0 and not obs['stderr']
            policy=c['symbols']['KIND']==0 or c['symbols']['ARG_MODE']==1
            if c['symbols']['ARG_MODE']==1:
                assert original['exit']==139 and raw==b'' and obs['exit']==0
                w=canonical(data,c,manifest['identities'][i]);assert w[2:5]==[22,0xfeedface,1]
                expected=[0]*64;expected[:5]=[0x5853484c,c['symbols']['CASE'],22,0xfeedface,1]
                expected[28:32]=[1,0,1,0];expected[56:60]=manifest['identities'][i]
                assert w==expected
            elif len(raw)==256:
                assert obs['exit']==original['exit']==0
                native=canonical(data,c,manifest['identities'][i],r['native_fd_limit'])
                reference=canonical(raw,c,manifest['identities'][i])
                assert native==reference,(o['name'],[(k,native[k],reference[k]) for k in range(64) if native[k]!=reference[k]])
            else:assert obs['exit']==original['exit']==37 and data==raw
            result['interface_cases']+=1;result['native_policy' if policy else 'oracle_equal']+=1
        for control in r['controls']:
            if control['name']=='session-descendant-cleanup':
                x=control['actual'];assert x['exit']==x['signal']==0 and x['killed']==x['absent']==x['valid']==1 and x['elapsed_ms']>=2000
                assert not x['stdout'] and not x['stderr']
            else:
                x=control['actual'];assert x['errno_bytes']==x['errno']==x['signal']==x['killed']==0 and not x['stderr']
                assert (x['exit'],x['stdout'])==((37,'XIRI_ABI_PROBE\n') if control['name'].endswith('native-o32') else (0,''))
        for app in r['apps']:
            assert app['output']==app['cookie']+'\n' and app['marker_owner']==1234
            assert app['actual']['absent']==app['actual']['valid']==1 and app['actual']['killed']==1
            assert (app['actual']['exit'],app['actual']['signal'])==((0,0) if app['name']=='winterm' else (-1,9))
            assert app['actual']['elapsed_ms']>=30000 and not app['actual']['stdout']
            assert app['actual']['stderr']==('/emul/irix/usr/sbin/winterm: Cannot execute ELF binary /emul/irix/usr/bin/gettxt\n' if app['name']=='winterm' else '')
            assert 'TYPE_STATUS=0' in app['typing'] and 'GUARD_STATUS=0' in app['typing']
            assert sha(directory/(app['name']+'.xwd'))==app['frame_sha256']
            fields=dict(re.findall(r'(\w+)=(\S+)',app['handoff']))
            assert fields['pid']==fields['sid']==fields['pgid']==fields['tpgid']
            assert all(fields[k]=='1234' for k in ['uid','euid','gid','egid']) and fields['groups']=='0'
            assert fields['rows']=='24' and fields['cols']=='80' and fields['tty'].startswith('/dev/')
            result['apps'].append(dict(mode=r['mode'],name=app['name'],handoff=app['handoff'],frame_sha256=app['frame_sha256'],output=app['output'],cleanup=app['actual']))
        if r['scope']!='interfaces':
            assert len(r['native_ctty_controls'])==8
            assert {(c['phase'],c['uid'],c['mode']) for c in r['native_ctty_controls']}=={(phase,uid,mode) for phase in ['before','after'] for uid in [0,1234] for mode in [0,2]}
            for c in r['native_ctty_controls']:
                x=c['actual'];assert x['errno_bytes']==x['errno']==x['exit']==x['signal']==x['killed']==0 and not x['stderr']
                assert ('NATIVE_CTTY mode='+str(c['mode'])+' exit=-1 signal=1\n') in x['stdout']
        if r['scope']!='interfaces':assert len(r['apps'])==3 and {x['name'] for x in r['apps']}=={'native','xwsh','winterm'} and r['native_x11_after']
        assert len(r['controls'])==10
        assert {(c['phase'],c['name'],c.get('uid')) for c in r['controls']}=={(phase,name,uid) for phase in ['before','after'] for name,uid in [('session-descendant-cleanup',None),*[(name,uid) for name in ['/root/irix-desktop/native-o32','/root/irix-desktop/vendor-asa'] for uid in [0,1234]]]}
        result['control_cases']+=len(r['controls']);result['native_ctty_cases']+=len(r.get('native_ctty_controls',[]))
        result['runs'].append(dict(directory=str(directory),result_sha256=sha(directory/'result.json'),kernel_abi=r['kernel_abi'],mode=r['mode'],scope=r['scope'],clean_shutdown=True,pin=r['pin'],sources=r['sources'],native_fd_limit=r.get('native_fd_limit'),control_cases=len(r['controls']),native_ctty_cases=len(r.get('native_ctty_controls',[]))))
    result['limits']=['Native RLIMIT_NOFILE is retained; original reference limit is 200.','Null argv returns native EINVAL; reference /bin/sh terminates with shell status 139.','Native helper supplies controlling terminal and 80x24 size; foreign termios, resize and caught signals remain unqualified.','Jobs are deliberately killed by the reserved-UID supervisor after the live input check.']
    if a.png:
        assert len(result['runs'])==3
        assert {(r['kernel_abi'],r['mode'],r['scope']) for r in result['runs']}=={('lp64','ci','all'),('lp64','ordinary','all'),('o32','ci','interfaces')}
        directory=next(Path(r['directory']) for r in result['runs'] if r['kernel_abi']=='lp64' and r['mode']=='ci')
        frame=directory/'winterm.xwd';a.png.parent.mkdir(parents=True,exist_ok=True)
        subprocess.run(['magick',str(frame),str(a.png)],check=True)
        pixels=lambda path:subprocess.check_output(['magick',str(path),'-depth','8','rgba:-'])
        original=pixels(frame);assert len(original)==1024*768*4 and pixels(a.png)==original
        result['screenshot']=dict(path=str(a.png),sha256=sha(a.png),width=1024,height=768,pixels_match_xwd=True)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['apps','runs','limits']},indent=2))
if __name__=='__main__':main()
