#!/usr/bin/env python3
"""Retain successful and failed 4Dwm bring-up attempts outside the final matrix."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runs',nargs='+',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    expected={('desktop','ci'):('error',3,False),('sessionless','ci'):('observed',1,False),('windowtest','ci'):('observed',5,False),('windowtest','ordinary'):('observed',5,False),('desktop-sessionless','ci'):('observed',0,True),('desktop-windowtest','ci'):('observed',0,True),('desktop-windowtest','ordinary'):('error',0,False),('session','ci'):('error',0,False)}
    report=dict(schema=1,status='bring-up-history',qualifier_sha256=sha(Path(__file__)),scope='Diagnostic history; not the final accepted interaction matrix',runs=[])
    coverage=set()
    for d in a.runs:
        r=json.loads((d/'result.json').read_text());key=(r['stage'],r['mode']);status,wmstatus,command=expected[key];coverage.add(key)
        assert r['status']==status and r['clean_shutdown']
        assert r['pin']==json.loads((ROOT/'lab/irix-prda/baseline.json').read_text())
        for path,h in r['sources'].items():assert sha(ROOT/path)==h,path
        assert len(r['cases'])==1;c=r['cases'][0];x=c['actual']
        assert x['exit']==-1 and x['signal']==9 and x['killed']==x['absent']==x['valid']==1
        assert c['wmcheck'].startswith('WMCHECK_STATUS='+str(wmstatus)+'\n')
        if wmstatus==0:assert 'WM_KEY delivered=1\n' in c['wmcheck'] and 'WM_DRAG dx=50 dy=30\n' in c['wmcheck'] and c['wmcheck'].endswith('WM_CHECK passed\n')
        if key[0]=='sessionless':assert 'BadWindow' in c['wmcheck']
        if key[0]=='windowtest':assert 'pointer_root=1 pointer_leaf=841' in c['wmcheck'] and 'matched=0' in c['wmcheck']
        if key[0].startswith('desktop') or key[0]=='session':
            assert c['output']==('XIRI_4DWM_SHELL_OK\n' if command else '')
            if command:assert c['marker_owner']==1234 and 'TYPE_STATUS=0' in c['typing'] and r['native_x11_after'] and len(r['native_ctty_controls'])==8
            if key==('session','ci'):assert not c['handoff'] and 'TYPE_STATUS=3' in c['typing'] and '"winterm":' not in c['tree']
        f=d/('wm.xwd' if key[0] in ['sessionless','windowtest'] else 'desktop.xwd');assert sha(f)==c['frame_sha256']
        report['runs'].append(dict(directory=str(d),result_sha256=sha(d/'result.json'),stage=key[0],mode=key[1],status=status,window_check_status=wmstatus,shell_command_proved=command,sources=r['sources'],controls=r['controls'],native_ctty_controls=r.get('native_ctty_controls',[]),cases=r['cases'],clean_shutdown=True))
    assert len(a.runs)==len(expected) and coverage==expected.keys()
    a.output.write_text(json.dumps(report,indent=2)+'\n');print('Eight bring-up attempts retained, including failed startup/input observations')
if __name__=='__main__':main()
