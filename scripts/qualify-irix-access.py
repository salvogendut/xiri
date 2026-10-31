#!/usr/bin/env python3
"""Qualify exact access records, preserved IDs, controls and namespace policy."""
import argparse,hashlib,importlib.util,json,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
s=importlib.util.spec_from_file_location('records',ROOT/'scripts/irix-access-records.py');records=importlib.util.module_from_spec(s);s.loader.exec_module(records)

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('runs',nargs='+',type=Path)
    p.add_argument('--reference',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--export-reference',type=Path,help='Save the qualified oracle for later guest comparisons')
    a=p.parse_args();ref=json.loads((a.reference/'result.json').read_text())
    assert ref['status']=='observed' and ref['clean_shutdown']
    assert ref['harness_sha256']==sha(ROOT/'scripts/probe-irix-reference-access.py')
    assert ref['decoder_sha256']==sha(ROOT/'scripts/probe-irix-runtime.py')
    manifest=ref['manifest'];cases={c['name']:c for c in manifest['cases']}
    expected_names={c['name']+'-'+str(i) for c in cases.values() for i in c['identities']}
    oracle={o['name']:o for o in ref['observations']}
    assert len(oracle)==len(ref['observations']) and set(oracle)==expected_names
    for path,h in manifest['sources'].items():assert sha(ROOT/path)==h
    for n,o in oracle.items():
        c=cases[n.rsplit('-',1)[0]];i=int(n.rsplit('-',1)[1]);w=struct.unpack('>16I',bytes.fromhex(o['stdout_hex']))
        assert o['exit']==0 and not o['stderr']
        assert w[:2]==(0x58494143,c['symbols']['CASE']) and w[3]==0xfeedface
        assert w[4] in [0,1] and (w[4] or w[2]==0)
        assert w[5]==c['symbols']['MODE'] & 0xffffffff
        assert w[6:10]==w[10:14]==tuple(manifest['identities'][i])
        assert w[14:]==(0xa5a5a5a5,0x5a5a5a5a)
    summary=dict(schema=1,status='qualified-subset',reference_directory=str(a.reference),reference_result_sha256=sha(a.reference/'result.json'),reference_checks=len(oracle),fixture_files=manifest['files'],identities=manifest['identities'],runs=[],checks=0)
    seen=set()
    for d in a.runs:
        r=json.loads((d/'result.json').read_text());key=(r['kernel_abi'],r['mode']);assert key not in seen;seen.add(key)
        assert r['status'] in ['observed','observed-uncompared'] and r['clean_shutdown'] and not r['failures'] and r['manifest']==manifest
        for path,h in r['sources'].items():assert sha(ROOT/path)==h
        pin=ROOT/'lab/irix-access'/('o32-baseline.json' if key[0]=='o32' else 'baseline.json');assert r['pin']==json.loads(pin.read_text())
        want={n for n in expected_names if key[0]=='lp64' or n.startswith('o32-')}
        assert {o['name'] for o in r['observations']}==want and len(r['observations'])==len(want)
        policies=[]
        for o in r['observations']:
            name=o['name'];case=cases[name.rsplit('-',1)[0]];identity=int(name.rsplit('-',1)[1])
            expected,policy=records.expected(case,identity,bytes.fromhex(oracle[name]['stdout_hex']),manifest['identities'])
            assert o['record_hex']==expected.hex(),(name,o['record_hex'],expected.hex())
            if r['status']=='observed':assert o['expected_hex']==expected.hex() and o['passed'] and o['contract_policy']==policy
            else:assert o['expected_hex'] is None and o['passed'] is None and o['contract_policy'] is None
            if policy:policies.append(dict(name=name,policy=policy,irix=oracle[name]['stdout_hex'],netbsd=expected.hex(),differs=oracle[name]['stdout_hex']!=expected.hex()))
            actual=o['actual'];assert actual==dict(errno_bytes=0,errno=0,exit=0,signal=0,killed=0,stdout=actual['stdout'],stderr='')
        control_names={(phase,uid,name) for phase in ['before','after'] for uid in [0,1234] for name in (['native-o32','vendor-asa','vendor-echo'] if key[0]=='lp64' else ['native-o32','vendor-asa'])}
        assert {(c['phase'],c['uid'],c['name']) for c in r['controls']}==control_names
        for c in r['controls']:
            expected={'native-o32':(37,'XIRI_ABI_PROBE\n'),'vendor-asa':(0,'XIRI_VENDOR_O32\n'),'vendor-echo':(0,'XIRI_VENDOR_N32\n')}[c['name']]
            assert c['actual']==dict(errno_bytes=0,errno=0,exit=expected[0],signal=0,killed=0,stdout=expected[1],stderr='')
        summary['checks']+=len(want)
        differing=sum(x['differs'] for x in policies)
        summary['runs'].append(dict(directory=str(d),kernel_abi=key[0],mode=key[1],checks=len(want),controls=len(control_names),clean_shutdown=True,contract_policy_cases=policies,oracle_identical_records=len(want)-differing,oracle_different_records=differing,result_sha256=sha(d/'result.json')))
    assert seen=={('lp64','ci'),('lp64','ordinary'),('o32','ci')}
    summary['scope']='Standard modes 0..7; native execute authorization and emulation namespace policy; extra IRIX mode bits rejected'
    summary['contract_sha256']=sha(ROOT/'scripts/irix-access-records.py')
    summary['qualifier_sha256']=sha(Path(__file__))
    if a.export_reference:
        exported=dict(schema=1,description='Original IRIX 6.5.22m access records with empty supplementary groups',reference_directory=str(a.reference),reference_result_sha256=sha(a.reference/'result.json'),files=manifest['files'],identities=manifest['identities'],sources=manifest['sources'],observations=ref['observations'])
        a.export_reference.write_text(json.dumps(exported,indent=2)+'\n')
        summary['exported_reference_sha256']=sha(a.export_reference)
    a.output.write_text(json.dumps(summary,indent=2)+'\n');print(summary['checks'],'access checks qualified')
if __name__=='__main__':main()
