#!/usr/bin/env python3
"""Check the retained executable suite and n32 half-page data layouts."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import tarfile

ROOT=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('runtime',ROOT/'scripts/probe-irix-runtime.py')
runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive',type=Path,required=True)
    p.add_argument('--fixtures',type=Path,default=ROOT/'.work/irix-exec-subpage')
    p.add_argument('--run',type=Path)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();manifest=json.loads((a.fixtures/'manifest.json').read_text())
    for name,item in manifest['files'].items():assert sha(a.fixtures/name)==item['sha256'],name
    expected_names={c['name']+'-'+str(uid)+'.log' for c in manifest['cases'] for uid in (0,1234)}
    with tarfile.open(a.archive) as archive:
        logs={m.name.removeprefix('./'):archive.extractfile(m).read().decode() for m in archive if m.isfile()}
    assert set(logs)==expected_names,(set(logs)-expected_names,expected_names-set(logs))
    records=[]
    for case in manifest['cases']:
        success=case['expect']=='output'
        expected=dict(errno_bytes=0 if success else 4,errno=0 if success else 8,
            exit=37 if success else 126,signal=0,killed=0,
            stdout='XIRI_ABI_PROBE\n' if success else '',stderr='')
        for uid in (0,1234):
            name=case['name']+'-'+str(uid);log=logs[name+'.log'];actual=runtime.observation(log)
            passed=actual==expected and 'GROUP absent=1' in log
            records.append(dict(name=name,passed=passed,actual=actual,expected=expected))
    passed=all(r['passed'] for r in records)
    result=dict(schema=1,status='checks-passed' if passed else 'mismatch',
        qualifier_sha256=sha(Path(__file__)),archive_sha256=sha(a.archive),manifest=manifest,observations=records)
    if a.run:
        guest=json.loads((a.run/'result.json').read_text())
        assert guest['clean_shutdown'] and guest['base_unchanged'],guest
        result.update(run=str(a.run),clean_shutdown=True,base_unchanged=True)
        if passed:result['status']='passed'
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(sum(r['passed'] for r in records),'/',len(records),'executable checks passed')
    for r in records:
        if not r['passed']:print(r['name'],r['actual'],r['expected'])
    return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())
