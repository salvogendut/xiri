#!/usr/bin/env python3
"""Summarize bounded catalog startup observations without claiming full support."""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import re
import tarfile

ROOT=Path(__file__).resolve().parent.parent

def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def validate_inventory(manifest):
    source=ROOT/'lab/irix-installed-desktop/manifest.json'
    assert sha(source)==manifest['source_inventory_sha256']
    original=json.loads(source.read_text())
    entries={e['catalog_path']:e for e in manifest['entries']}
    assert len(entries)==len(manifest['entries'])==len(original['entries'])
    assert set(entries)=={e['catalog_path'] for e in original['entries']}
    for entry in original['entries']:
        assert all(entries[entry['catalog_path']].get(k)==v for k,v in entry.items())
    cases={c['id']:c for c in manifest['cases']}
    assert len(cases)==len(manifest['cases'])
    assert set(cases)=={e['case'] for e in entries.values() if 'case' in e}
    assert collections.Counter(e['page'] for e in entries.values())==original['pages']

def windows(text):
    out={}
    pattern=r'^WINDOW id=([0-9a-f]+) width=(\d+) height=(\d+) name=([0-9a-f]*) class=([0-9a-f]*) instance=([0-9a-f]*)$'
    for line in text.splitlines():
        m=re.fullmatch(pattern,line)
        assert m,line
        out[m[1]]=dict(id=m[1],width=int(m[2]),height=int(m[3]),
            name=bytes.fromhex(m[4]).decode(errors='replace'),
            class_name=bytes.fromhex(m[5]).decode(errors='replace'),
            instance=bytes.fromhex(m[6]).decode(errors='replace'))
    return out

def processes(text,owned):
    result=[]
    for line in text.splitlines()[1:]:
        fields=line.split(None,6)
        if len(fields)!=7 or not fields[0].isdigit() or int(fields[0]) not in owned:continue
        result.append(dict(pid=int(fields[0]),ppid=int(fields[1]),uid=int(fields[2]),
            state=fields[3],cpu_time=fields[4],pcpu=fields[5],command=fields[6]))
    return result

def summarize(run,record,archive):
    observations=[]
    for entry in record['cases']:
        case=entry['case'];prefix='.xiri-catalog/'+case['id']+'/'
        interrupted=entry.get('interrupted',False)
        members={m.name[len(prefix):]:m for m in archive if m.name.startswith(prefix) and m.isfile()}
        def read(name):return archive.extractfile(members[name]).read().decode(errors='replace')
        guard=read('guard');match=re.search(r'^GUARD (.+)$',guard,re.M);assert match,case
        values=dict(word.split('=',1) for word in match[1].split())
        cleanup_verified=values['absent']==values['valid']=='1' and values['remaining']=='0'
        # A failed tracker is a recorded failure, never an application pass.
        # It is admissible only in an explicitly interrupted, cleanly halted run.
        assert cleanup_verified or interrupted
        assert values['uid']==values['gid']=='1234'
        owned={int(p) for p in re.findall(r'^OWN pid=(\d+)',guard,re.M)}
        before=windows(read('before.windows'));new={};samples={};query_failures=[]
        if 'before.windows.status' in members:assert read('before.windows.status').strip()=='0'
        for name in ['3','15','35','last']:
            if name+'.windows' not in members:continue
            code=int(read(name+'.windows.status')) if name+'.windows.status' in members else 0
            if code:query_failures.append(dict(sample=name,status=code,error=read(name+'.windows.err')))
            else:assert not read(name+'.windows.err'),case
            frame=windows(read(name+'.windows')) if not code else {}
            added={k:v for k,v in frame.items() if k not in before}
            new.update(added)
            samples[name]=dict(windows=list(added.values()),
                processes=processes(read(name+'.ps'),owned) if name+'.ps' in members else [],
                snapshot_complete=not code and name+'.ps' in members,query_status=code)
        assert not read('before.windows.err')
        if not interrupted:
            code=int(read('after.windows.status')) if 'after.windows.status' in members else 0
            if code:query_failures.append(dict(sample='after',status=code,error=read('after.windows.err')))
            else:assert not read('after.windows.err')
        # NOTE_TRACK and the guard's process identities establish cleanup.
        # A later ps may contain a zombie or a recycled numeric PID; retain it
        # for review instead of mistaking it for a live owned descendant.
        after_matches=processes(read('after.ps'),owned) if 'after.ps' in members else None
        stderr=read('stderr');stdout=read('stdout')
        if not cleanup_verified:status='cleanup-unverified'
        elif interrupted or query_failures:status='observation-interrupted'
        elif new:status='window-observed'
        elif values['reason']!='leader-exit':status='no-window-before-test-stop'
        elif int(values['signal']):status='terminated-by-signal'
        elif int(values['exit']):status='nonzero-exit'
        else:status='zero-exit-without-window'
        shot=entry.get('screenshot',{})
        if shot.get('path'):assert sha(run/shot['path'])==shot['sha256']
        observations.append(dict(case=case,run=str(run),status=status,
            guard=values,owned_pids=sorted(owned),new_windows=list(new.values()),samples=samples,
            after_ps_pid_matches=after_matches,
            observation_interrupted=interrupted or bool(query_failures),
            batch_interrupted=interrupted,
            window_query_failures=query_failures,
            cleanup_verified=cleanup_verified,
            stdout=stdout[:8192],stderr=stderr[:8192],stdout_bytes=members['stdout'].size,
            stderr_bytes=members['stderr'].size,screenshot=shot,
            normal_interaction_tested=False,catalog_double_click_tested=False,
            record_hashes={name:hashlib.sha256(archive.extractfile(m).read()).hexdigest() for name,m in members.items()}))
    return observations

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runs',type=Path,nargs='+',required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();inventory=ROOT/'lab/irix-catalog/inventory.json';manifest=json.loads(inventory.read_text())
    validate_inventory(manifest)
    seen={};records=[];bundle_hashes=set();interruptions=[]
    for run in a.runs:
        r=json.loads((run/'result.json').read_text())
        assert r['clean_shutdown'] and r['source_unchanged'],str(run)
        assert not r.get('cleanup_error')
        if r['status']!='observed':
            # Preserve verified completed cases before an observer failure.
            # Admit the interrupted attempt explicitly, never as a normal case.
            assert r['status']=='diagnostic'
            assert 'guest command failed (2)' in r.get('error','')
            progress=json.loads((run/'progress.json').read_text())
            assert progress['cases']==r['cases']
            match=re.search(r'observe.sh (app-\d+) ',r['error']);assert match
            case=next(c for c in manifest['cases'] if c['id']==match[1])
            assert case not in [o['case'] for o in r['cases']]
            shot=run/(case['id']+'.png')
            r['cases'].append(dict(case=case,interrupted=True,
                screenshot=dict(path=shot.name,sha256=sha(shot)) if shot.exists() else {}))
            interruptions.append(dict(run=str(run),case=case['id'],error=r['error'],
                progress_sha256=sha(run/'progress.json'),clean_shutdown=True))
        else:assert not r.get('error')
        assert r['inventory_sha256']==sha(inventory)
        assert sha(run/'harness.py')==r['harness_sha256']
        assert sha(run/'observations.tgz')==r['observations_sha256']
        for name,digest in r['media_sources'].items():assert sha(run/'media'/name)==digest
        control=r['guard_controls']
        assert control.count('CATALOG_NATIVE_CHILD_FINISHED')==1
        assert len(re.findall(r'^GUARD .*exit=37 signal=0 .*absent=1 valid=1',control,re.M))==2
        assert 'reason=leader-exit' in control and 'reason=timeout' in control
        visible=windows(r['window_control']);assert any(w['name']=='SURVEY_VISIBLE' for w in visible.values())
        assert not any(w['name']=='SURVEY_HIDDEN' for w in visible.values())
        if 'query-control.c' in r['media_sources']:
            assert r['query_timeout_control']=='SURVEY_SERVER_HELD\nQUERY_STATUS=142\n'
        with tarfile.open(run/'observations.tgz') as archive:
            for item in summarize(run,r,archive):
                key=item['case']['id'];assert key not in seen;seen[key]=item
        bundle=Path(r['bundle']);m=json.loads((bundle/'manifest.json').read_text());bundle_hashes.add(m['chd_sha256'])
        assert sha(bundle/'manifest.json')==r['manifest_sha256']
        assert r['pin']==m['pin'] and r['module']==m['irix_module']
        records.append(dict(run=str(run),result_sha256=sha(run/'result.json'),archive_sha256=r['observations_sha256'],
            serial_sha256=sha(run/'serial.log'),harness_sha256=r['harness_sha256'],media_sources=r['media_sources'],
            clean_shutdown=True,source_unchanged=True,guard_controls=control,
            window_control=r['window_control'],pin=r['pin'],module=r['module'],
            query_timeout_control=r.get('query_timeout_control'),
            manifest_sha256=r['manifest_sha256']))
    assert len(bundle_hashes)==1
    assert set(seen)=={c['id'] for c in manifest['cases']},'The full inventory has not been observed'
    for case in manifest['cases']:assert seen[case['id']]['case']==case
    review_path=ROOT/'lab/irix-catalog/review.json'
    reviews=json.loads(review_path.read_text())['cases']
    assert set(reviews)<=set(seen)
    for key,review in reviews.items():
        if 'screenshot' in review:assert sha(ROOT/review['screenshot'])==review['sha256']
        if review['ui']=='busy-without-window':
            item=seen[key]
            assert item['status']=='no-window-before-test-stop'
            assert review['samples']==item['samples'].get('35',item['samples'].get('15',{}))
    report=dict(schema=1,status='evidence-verified-startup-survey',inventory_sha256=sha(inventory),
        qualifier_sha256=sha(Path(__file__)),chd_sha256=bundle_hashes.pop(),runs=records,
        interruptions=interruptions,
        review_sha256=sha(review_path),reviews=reviews,
        all_launch_cleanup_verified=all(o['cleanup_verified'] for o in seen.values()),
        counts=dict(collections.Counter(o['status'] for o in seen.values())),observations=list(seen.values()),
        limitations=['Mapped windows establish startup UI, not useful operation, error-free behavior, or normal GUI exit.',
            'The survey invokes program targets through original IRIX sh as xiritest; catalog double-clicks and document handlers require separate checks.',
            'The launch guard has a 45-second stop deadline; scheduling and cleanup can take longer. Its measured elapsed time is retained. No-window cases are not proof of a permanent hang.',
            'Standard input is /dev/null; terminal-dependent launchers need interactive checks.',
            'Background/root-window programs, CLI prompts, hardware tools and license dialogs need individual interpretation.',
            'Programs run sequentially within each disposable desktop; user preferences and helper state can persist between cases.'])
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(len(seen),'startup observations:',report['counts'])

if __name__=='__main__':main()
