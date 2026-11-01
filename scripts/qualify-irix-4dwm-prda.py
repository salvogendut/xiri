#!/usr/bin/env python3
"""Bind the initial 4Dwm PRDA/resource observations without claiming success."""
import argparse,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runs',nargs='+',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    report=dict(schema=1,status='observed-boundary',qualifier_sha256=sha(Path(__file__)),graphical_success=False,runs=[])
    expected={'prda':('ci',5),'resources':(None,3)}
    coverage=set()
    for d in a.runs:
        r=json.loads((d/'result.json').read_text());assert r['status']=='observed' and r['clean_shutdown'] and r['native_x11_after']
        assert r['pin']==json.loads((ROOT/'lab/irix-prda/baseline.json').read_text())
        for path,h in r['sources'].items():assert sha(ROOT/path)==h,path
        mode,status=expected[r['stage']];assert mode is None or r['mode']==mode
        coverage.add((r['stage'],r['mode']))
        assert len(r['controls'])==2 and {c['phase'] for c in r['controls']}=={'before','after'}
        for c in r['controls']:assert c['actual']==dict(errno_bytes=0,errno=0,exit=37,signal=0,killed=0,stdout='XIRI_ABI_PROBE\n',stderr='')
        assert len(r['cases'])==1;c=r['cases'][0];x=c['actual']
        assert x['exit']==-1 and x['signal']==9 and x['killed']==x['absent']==x['valid']==1 and x['elapsed_ms']>=30000 and not x['stdout']
        assert c['wmcheck'].startswith('WMCHECK_STATUS='+str(status)+'\n')
        assert sha(d/'wm.xwd')==c['frame_sha256'] and '_MOTIF_WM_INFO' in c['properties']
        assert 'trustedPathManager' in c['tree'] and 'SGI-AccessControl' in x['stderr']
        if r['stage']=='prda':
            assert 'WM_REPARENT ' in c['wmcheck'] and 'matched=0' in c['wmcheck'] and 'Cannot open configuration file' in x['stderr']
        else:
            assert c['wmcheck']=='WMCHECK_STATUS=3\nwindows were not reparented\n'
            assert 'Cannot open configuration file' not in x['stderr']
            assert r['resource_modes'].count('-r--r--r-- 0 0 /emul/irix/usr/lib/X11/')==4
        report['runs'].append(dict(directory=str(d),result_sha256=sha(d/'result.json'),trace_sha256=sha(d/'wm.kdump'),stage=r['stage'],mode=r['mode'],pin=r['pin'],sources=r['sources'],staged=r['staged'],controls=r['controls'],cases=r['cases'],clean_shutdown=True))
    assert coverage=={('prda','ci'),('resources','ci'),('resources','ordinary')}
    a.output.write_text(json.dumps(report,indent=2)+'\n');print('PRDA fault cleared; fallback decorations and resource-enabled startup boundary recorded')
if __name__=='__main__':main()
