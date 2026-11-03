#!/usr/bin/env python3
"""Qualify the bounded wheel update while retaining the parent desktop evidence."""
import argparse
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from xiri_lab import sha256


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--png',type=Path,required=True)
    parser.add_argument('--promote',action='store_true')
    args=parser.parse_args()
    check=json.loads((args.run/'wheel-result.json').read_text())
    bundle=ROOT/check['bundle'];m=json.loads((bundle/'manifest.json').read_text())
    seed=json.loads((bundle/'seed-result.json').read_text());prep=seed['account_update']
    parent=ROOT/prep['bundle'];old=json.loads((parent/'manifest.json').read_text())
    assert check['scope']=='xdm-wheel-chd' and prep['scope']=='xdm-wheel-prepare'
    assert m['status']=='chd-roundtrip-verified'
    assert sha256(bundle/'manifest.json')==check['input_manifest_sha256']
    assert sha256(bundle/'netbsd-xiri.chd')==m['chd_sha256']==check['source_disk_sha256']
    assert m['source_raw_sha256']==m['decoded_raw_sha256']
    assert m['source_raw_sha256']!=old['source_raw_sha256'], 'account update missing from CHD'
    assert sha256(bundle/'seed-result.json')==m['source_result_sha256']
    assert prep['source_disk_sha256']==old['source_raw_sha256']
    assert prep['inherited_seed_result_sha256']==old['source_result_sha256']
    full=ROOT/old['qualification']
    assert sha256(full)==old['qualification_sha256']
    assert json.loads(full.read_text())['status']=='disk-boot-and-xdm-desktops-verified'
    for field in ('pin','emulator_files','copy_ledger_sha256','permission_manifest_sha256',
                  'runtime_sources','qualification_nvram_sha256'):
        assert m[field]==old[field],field
    for path,key in [('copy-ledger.json','copy_ledger_sha256'),('permissions.json','permission_manifest_sha256'),
                     ('iris.toml','config_sha256'),(m['qualification_nvram'],'qualification_nvram_sha256')]:
        assert sha256(bundle/path)==m[key],path
    for path,digest in m['emulator_files'].items():assert sha256(bundle/path)==digest,path
    old_seed=json.loads((parent/'seed-result.json').read_text())
    assert seed['installed_files']==dict(old_seed['installed_files'],**{'/etc/group':prep['group_sha256']})
    assert check['group_sha256']==prep['group_sha256']
    assert check['group_before']==check['group_after']==prep['group_after']
    assert check['passwd_sha256']==prep['passwd_sha256']
    for r in (prep,check):
        assert r['status']=='passed' and r['clean_shutdown'] and r['source_disk_unchanged']
        assert r['login_proof'][:2]==['netbsdtest','1236']
        assert 'wheel' in r['login_proof'][2].split() and r['login_proof'][3]=='/home/netbsdtest'
        assert r['su_login_proof']==['root','0','/root','/root']
        assert '1280x1024 pixels' in r['dimensions']
        assert r['services_before']==r['services_after'] and r['securelevel']==1
        assert 'unmounting done' in r['shutdown_log'][-2048:] and 'halting...' in r['shutdown_log'][-256:]
        for path,digest in r['sources'].items():assert sha256(ROOT/path)==digest,path
    frame=args.run/'wheel-su.png';assert sha256(frame)==check['png_sha256']
    args.png.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(frame,args.png)
    report=dict(status='xdm-wheel-update-verified',scope='netbsdtest supplementary wheel group',
        bundle=check['bundle'],chd_sha256=m['chd_sha256'],raw_sha256=m['source_raw_sha256'],
        chd_bytes=m['chd_bytes'],full_desktop_suite_rerun=False,
        inherited_full_desktop_qualification=dict(path=str(full.relative_to(ROOT)),sha256=sha256(full)),
        preparation=prep,check=check,check_directory=str(args.run),
        check_result_sha256=sha256(args.run/'wheel-result.json'),
        qualifier_sha256=sha256(__file__),png=str(args.png),png_sha256=sha256(args.png))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    if args.promote:
        pointer_path=ROOT/'lab/irix-installed-desktop/image.json'
        pointer=json.loads(pointer_path.read_text())
        assert pointer['chd_sha256']==old['chd_sha256'], 'selected parent changed'
        shutil.copyfile(bundle/'manifest.json',bundle/'verification/build-manifest.json')
        m.update(direct_chd_boot='verified',qualification=str(args.output),qualification_sha256=sha256(args.output),
                 qualification_scope='wheel update; full desktop behavior inherited',qualification_run=str(args.run))
        m['xdm']['image_login_qualification']='wheel account verified; full desktop behavior inherited'
        m['xdm']['accounts']['netbsdtest']['supplementary_groups']=['wheel']
        (bundle/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
        for field in ('chd_sha256','chd_bytes','logical_bytes','nvram_sha256','config_sha256',
                      'copy_ledger_sha256','permission_manifest_sha256','manual_nvram_sha256',
                      'manual_console','emulator_files','xdm'):
            pointer[field]=m[field]
        pointer.update(bundle=check['bundle'],image=check['bundle']+'/netbsd-xiri.chd',
                       raw_sha256=m['source_raw_sha256'],qualification=str(args.output),
                       qualification_sha256=sha256(args.output),qualification_scope=m['qualification_scope'])
        pointer_path.write_text(json.dumps(pointer,indent=2)+'\n')
    print('Verified fresh xdm login, wheel membership, interactive root su, logout and clean halt')


if __name__=='__main__':main()
