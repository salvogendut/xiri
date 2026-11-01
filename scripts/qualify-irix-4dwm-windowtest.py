#!/usr/bin/env python3
"""Qualify original 4Dwm window interaction and a combined winterm shell."""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runs',nargs='+',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--png',type=Path,required=True);a=p.parse_args()
    history=ROOT/'docs/results/2026-11-01-irix-4dwm-attempts.json'
    previous=json.loads(history.read_text());assert previous['status']=='bring-up-history' and len(previous['runs'])==8
    report=dict(schema=1,status='passed',scope='Bounded successful interaction runs; startup repeatability is not qualified',diagnostic_history_sha256=sha(history),qualifier_sha256=sha(Path(__file__)),runs=[])
    coverage=set();frame=None
    for d in a.runs:
        r=json.loads((d/'result.json').read_text());assert r['status']=='observed' and r['clean_shutdown'] and r['native_x11_after']
        assert r['stage'] in ['windowready','session']
        coverage.add((r['stage'],r['mode']))
        assert r['pin']==json.loads((ROOT/'lab/irix-prda/baseline.json').read_text())
        for path,h in r['sources'].items():assert sha(ROOT/path)==h,path
        manifest=json.loads((ROOT/'lab/irix-desktop/manifest.json').read_text())
        for path,h in r['staged'].items():
            original=path.removeprefix('/emul/irix')
            entry=manifest['files'].get(original) or manifest['resource_candidates'].get(original)
            assert entry and entry['sha256']==h,path
        assert len(r['controls'])==2 and {c['phase'] for c in r['controls']}=={'before','after'}
        for c in r['controls']:assert c['actual']==dict(errno_bytes=0,errno=0,exit=37,signal=0,killed=0,stdout='XIRI_ABI_PROBE\n',stderr='')
        assert r['resource_modes'].count('-r--r--r-- 0 0 /emul/irix/usr/lib/X11/')==4
        assert len(r['cases'])==1;c=r['cases'][0];x=c['actual'];desktop=r['stage']=='session'
        assert x['exit']==-1 and x['signal']==9 and x['killed']==x['absent']==x['valid']==1
        assert 'WM_VIEWABLE clients=2\n' in c['wmcheck']
        assert x['elapsed_ms']>=(90000 if desktop else 30000) and not x['stdout']
        check=c['wmcheck'];assert check.startswith('WMCHECK_STATUS=0\n') and check.endswith('WM_CHECK passed\n')
        assert re.search(r'^WM_REPARENT client=\d+ frame=\d+ x=-?\d+ y=-?\d+ frame_x=-?\d+ frame_y=-?\d+$',check,re.M)
        assert re.search(r'^WM_FOCUS client=\d+ focus=\d+ matched=1$',check,re.M) and 'WM_KEY delivered=1\n' in check
        drag=re.search(r'^WM_DRAG dx=(-?\d+) dy=(-?\d+)$',check,re.M);assert drag and abs(int(drag[1])-50)<=3 and abs(int(drag[2])-30)<=3
        assert '_MOTIF_WM_INFO' in c['properties'] and '_SGI_DESKS_MANAGER' in c['properties']
        f=d/('desktop.xwd' if desktop else 'wm.xwd');assert sha(f)==c['frame_sha256']
        if desktop:
            geometry=re.fullmatch(r'TYPE_WINDOW width=(\d+) height=(\d+) viewable=1\n',c['type_output'])
            assert geometry and int(geometry[1])>200 and int(geometry[2])>120
            assert not x['stderr'] and 'TYPE_STATUS=0' in c['typing'] and 'GUARD_STATUS=0' in c['typing']
            assert c['cookie']=='XIRI_4DWM_SHELL_OK' and c['output']==c['cookie']+'\n' and c['marker_owner']==1234
            assert r['resources']==json.loads((ROOT/'lab/irix-toolchest-input/resources.json').read_text())
            fields=dict(re.findall(r'(\w+)=(\S+)',c['handoff']));assert fields['pid']==fields['sid']==fields['pgid']==fields['tpgid']
            assert all(fields[k]=='1234' for k in ['uid','euid','gid','egid']) and fields['groups']=='0'
            assert fields['rows']=='24' and fields['cols']=='80' and fields['tty'].startswith('/dev/pts/')
            assert not c['logs']['toolchest']
            assert c['logs']['winterm']=='/emul/irix/usr/sbin/winterm: Cannot execute ELF binary /emul/irix/usr/bin/gettxt\n'
            for name in ['"winterm":','"Toolchest":']:assert name in c['tree']
            expected={(phase,uid,mode) for phase in ['before','after'] for uid in [0,1234] for mode in [0,2]}
            assert len(r['native_ctty_controls'])==8 and {(c['phase'],c['uid'],c['mode']) for c in r['native_ctty_controls']}==expected
            for n in r['native_ctty_controls']:
                z=n['actual'];assert z['errno_bytes']==z['errno']==z['exit']==z['signal']==z['killed']==0 and not z['stderr']
                assert 'NATIVE_CTTY mode='+str(n['mode'])+' exit=-1 signal=1\n' in z['stdout']
            if r['mode']=='ordinary':frame=f
        report['runs'].append(dict(directory=str(d),result_sha256=sha(d/'result.json'),stage=r['stage'],mode=r['mode'],pin=r['pin'],sources=r['sources'],staged=r['staged'],controls=r['controls'],native_ctty_controls=r.get('native_ctty_controls',[]),cases=r['cases'],clean_shutdown=True))
    assert len(report['runs'])==4 and coverage=={('windowready','ci'),('windowready','ordinary'),('session','ci'),('session','ordinary')} and frame
    a.png.parent.mkdir(parents=True,exist_ok=True);subprocess.run(['magick',str(frame),str(a.png)],check=True)
    pixels=lambda path:subprocess.check_output(['magick',str(path),'-depth','8','rgba:-'])
    original=pixels(frame);assert len(original)==1024*768*4 and pixels(a.png)==original
    report['screenshot']=dict(path=str(a.png),sha256=sha(a.png),width=1024,height=768,pixels_match_xwd=True)
    report['limits']=['An earlier run of the final CI session passed window checks but xwsh did not map or reach its native handoff. The failed run is bound in diagnostic history; startup repeatability remains unresolved.','SG_manageSession and SG_autoSave explicitly disabled; session saving/restoration remains unsupported.','SGI-AccessControl and the unexpected Trusted Path Manager panel require further feature-query investigation.','Window focus, key delivery and titlebar dragging are covered; menus, minimize/maximize, resize, desks and logout remain separate checks.','The winterm command uses the established native shell handoff; foreign signal handlers, terminal resize, gettxt and normal application exit remain open.','This uses native Xvfb in an emulated R4400 Indy; no physical hardware or complete desktop certification.']
    a.output.write_text(json.dumps(report,indent=2)+'\n');print('4Dwm focus/key/drag and combined winterm shell passed; PNG matches captured framebuffer')
if __name__=='__main__':main()
