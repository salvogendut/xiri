#!/usr/bin/env python3
"""Independently check subpage payloads, padding policy and mapper regressions."""
import argparse,hashlib,importlib.util,json,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
s=importlib.util.spec_from_file_location('old',ROOT/'scripts/qualify-irix-elfmap-relocation.py');old=importlib.util.module_from_spec(s);s.loader.exec_module(old)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def check(case,record,layout,page):
    if not case['name'].startswith('elfmap-subpage-'):
        old.expected(case,record,layout);return
    ph=layout;start=ph[0][2];data=ph[1][2];align=max(ph[0][7],ph[1][7]);span=(data+ph[1][5]+page-1)//page*page-start
    want=dict(magic=0x58494531,case=case['number'],v0=case['netbsd']['v0'],v1=0xfeedface,a3=case['netbsd']['a3'],checks=case['netbsd']['checks'],second_v0=0,second_a3=0,third_v0=0,third_a3=0,preserved_word=0,reserved=0)
    if page==4096 and case['name'] in ['elfmap-subpage-native-incongruent','elfmap-subpage-native-overlap']:
        want.update(v0=start,a3=0,checks=0)
    def reloc(value):
        assert 0x04000000<=value<=0x40000000-span and value!=start
        assert (value-start)%align==0
        return value
    if not want['a3']:
        collision=case['block'] and not(page==4096 and case['name']=='elfmap-subpage-prefix-collision')
        want['v0']=reloc(record['v0']) if collision else start
        if case['action'] in [8,9]:want.update(checks=3 if page==8192 else 1,second_v0=page)
        if case['action']==7:
            want.update(second_v0=reloc(record['second_v0']),third_v0=reloc(record['third_v0']),checks=3,preserved_word=0x12345678)
            values=sorted([want['v0'],want['second_v0'],want['third_v0']]);assert len(set(values))==3 and all(b>=a+span for a,b in zip(values,values[1:]))
    assert record==want,(case['name'],record,want)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--reference',required=True,type=Path);p.add_argument('runs',nargs='+',type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--partial',action='store_true');a=p.parse_args()
    ref=json.loads((a.reference/'result.json').read_text());assert ref['status']=='observed' and ref['clean_shutdown']
    assert ref['harness_sha256']==sha(ROOT/'scripts/probe-irix-reference-elfmap-subpage.py')
    manifest=ref['manifest'];cases={c['name']:c for c in manifest['cases']};assert len(cases)==74 and len(ref['observations'])==296
    for path,h in manifest['sources'].items():assert sha(ROOT/path)==h
    layouts={}
    for n,c in cases.items():
        f=ROOT/'.work/irix-elfmap-subpage/probes'/c['input'];assert sha(f)==manifest['files'][c['input']]['sha256']
        layouts[n]=[struct.unpack_from('>8I',f.read_bytes(),52+32*i) for i in range(2)]
    oracle={o['name']:o for o in ref['observations']};assert len(oracle)==296
    exported=json.loads((ROOT/'lab/irix-elfmap-subpage/reference.json').read_text())
    assert exported['manifest']==manifest and exported['harness_sha256']==ref['harness_sha256'] and exported['result_sha256']==sha(a.reference/'result.json')
    assert exported['observations']==[dict(name=o['name'],exit=o['exit'],record=list(struct.unpack('>12I',bytes.fromhex(o['stdout_hex']))),stderr=o['stderr']) for o in ref['observations']]
    for n,o in oracle.items():
        c=cases[n.split('-',1)[1].rsplit('-',1)[0]];r=old.rt.elfmap_record(bytes.fromhex(o['stdout_hex']))
        if c['name']=='elfmap-no-bounded-space':assert o['exit']==99 and r['v0']==r['v1']==0;continue
        assert o['exit']==(139 if c['netbsd']['signal'] else 0),(n,o)
        assert not o['stderr'] and r['magic']==0x58494531 and r['case']==c['number'] and r['v1']==0xfeedface
        assert r['reserved']==(0xc000 if c['name']=='elfmap-mixed-align' else 0)
        if c['action'] in [8,9]:assert r['checks']==1 and r['second_v0']==4096
    report=dict(schema=1,status='partial' if a.partial else 'qualified',reference=str(a.reference),reference_result_sha256=sha(a.reference/'result.json'),reference_records_sha256=sha(ROOT/'lab/irix-elfmap-subpage/reference.json'),manifest_sources=manifest['sources'],fixture_files=manifest['files'],runs=[],mapping_cases=0,limit_cases=0,controls=0,qualifier_sha256=sha(Path(__file__)))
    seen=set()
    for d in a.runs:
        r=json.loads((d/'result.json').read_text());key=(r['kernel_abi'],r['mode']);assert key not in seen;seen.add(key)
        assert r['status']=='observed' and r['clean_shutdown'] and not r['limits_only'] and r['manifest']==manifest
        for path,h in r['sources'].items():assert sha(ROOT/path)==h,path
        pin=json.loads((ROOT/'lab/irix-elfmap-subpage'/('o32-baseline.json' if key[0]=='o32' else 'baseline.json')).read_text());assert r['pin']==pin
        abis=['o32'] if key[0]=='o32' else ['o32','n32'];want={abi+'-'+n+'-'+str(uid) for abi in abis for n in cases for uid in [0,1234]}
        assert len(r['observations'])==len(want) and {o['name'] for o in r['observations']}==want
        diffs=[]
        for o in r['observations']:
            c=cases[o['name'].split('-',1)[1].rsplit('-',1)[0]];x=o['actual'];sig=c['netbsd']['signal']
            assert x['errno_bytes']==x['errno']==x['killed']==0 and x['exit']==(-1 if sig else 0) and x['signal']==sig and not x['stderr'],(o['name'],x)
            decoded=old.rt.elfmap_record(bytes.fromhex(o['record_hex']));assert decoded==o['record'];check(c,decoded,layouts[c['name']],pin['page_bytes'])
            original=old.rt.elfmap_record(bytes.fromhex(oracle[o['name']]['stdout_hex']))
            fields={k:dict(netbsd=v,irix=original[k]) for k,v in decoded.items() if v!=original[k]}
            if fields:diffs.append(dict(name=o['name'],fields=fields))
        assert len(r['limits'])==len(abis)*2
        for o in r['limits']:
            x=o['actual'];assert x['exit']==x['signal']==x['killed']==x['errno']==0 and not x['stderr']
            assert o['record']['v0']==12 and o['record']['a3']==1 and o['record']['v1']==0xfeedface and o['record']['checks']==0
        assert len(r['controls'])==(8 if key[0]=='o32' else 12)
        for c in r['controls']:
            x=c['actual'];assert x['errno_bytes']==x['errno']==x['signal']==x['killed']==0 and not x['stderr']
            assert (x['exit'],x['stdout'])=={'native-o32':(37,'XIRI_ABI_PROBE\n'),'vendor-asa':(0,'XIRI_VENDOR_O32\n'),'vendor-echo':(0,'XIRI_VENDOR_N32\n')}[c['name']]
        report['mapping_cases']+=len(want);report['limit_cases']+=len(r['limits']);report['controls']+=len(r['controls'])
        report['runs'].append(dict(directory=str(d),result_sha256=sha(d/'result.json'),kernel_abi=key[0],mode=key[1],clean_shutdown=True,pin=pin,sources=r['sources'],mapping_cases=len(want),limit_cases=len(r['limits']),controls=len(r['controls']),oracle_differences=diffs))
    if not a.partial:assert seen=={('lp64','ci'),('lp64','ordinary'),('o32','ci')}
    report['policy_notes']=['LP64 maps the preceding 4 KiB of a congruent data page: file bytes for initialized data, zeros for pure BSS. o32 and IRIX have 4 KiB pages.','LP64 rejects native-page incongruence and code/data virtual page sharing. Both kernels reject logical file overlap and byte-aligned segments.','The four original IRIX no-bounded-space cases fail while establishing the 960 MiB occupant; no mapper conclusion follows from them.','Placement differences and all record-field differences are retained per run. Backing input hashes are checked before and after each native case.']
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k in ['status','mapping_cases','limit_cases','controls']},indent=2))
if __name__=='__main__':main()
