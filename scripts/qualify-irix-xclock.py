#!/usr/bin/env python3
"""Validate saved CI/ordinary xclock loader-boundary runs and fault captures."""
import argparse
import hashlib,importlib.util,json,re
from pathlib import Path
root=Path(__file__).resolve().parent.parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
s=importlib.util.spec_from_file_location('t',root/'scripts/probe-irix-tcp.py');tcp=importlib.util.module_from_spec(s);s.loader.exec_module(tcp)
manifest=root/'lab/irix-xclock/manifest.json'
report=dict(schema=1,status='loader-boundary-observed',source_revision=json.loads((root/'lab/irix-xstat/baseline.json').read_text())['source_revision'],manifest_sha256=sha(manifest),irix_window_or_event_loop_qualified=False,blocker='SGI_ELFMAP returns ENOMEM while rld tries to load libXmu.so; no X socket/connect call follows',runs=[])
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('runs',nargs=2,type=Path)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
seen=set()
for directory in args.runs:
 d=directory.resolve();r=json.loads((d/'result.json').read_text())
 assert r['mode'] not in seen;seen.add(r['mode'])
 assert r['status']=='observed' and r['clean_shutdown'] and r['native_x11_before'] and r['native_x11_after']
 assert r['xclock_manifest_sha256']==sha(manifest) and r['pin']==json.loads((root/'lab/irix-xstat/baseline.json').read_text())
 assert 'Map State: IsViewable' in r['native_clock_window']
 assert len(r['faults'])==2 and len(r['xclock'])==4
 for f in r['faults']:
  assert int(f['pc'],16)==0xfa56b6c and int(f['address'],16)==0x740a0a5c and f['signal']==11
  assert sha(d/(f['name']+'.txt'))==f['raw_sha256']
 serial=(d/'serial.log').read_text()
 assert serial.count("rld: Error: elfmap: couldn't map /usr/lib32/libXmu.so") == 4
 cases=[]
 for c in r['xclock']:
  assert c['actual']==dict(errno_bytes=0,errno=0,exit=1,signal=0,killed=0,stdout='',stderr='')
  assert '0 children.' in c['window_tree'] and 'Map State: IsViewable' not in c['window']
  assert c['frames']['before']==c['frames']['after']
  raw=(d/(c['name']+'.kdump')).read_text()
  assert tcp.trace_records(raw,'irix_o32',True)==c['calls'] and tcp.trace_records(raw,'irix_ret',True)==c['returns']
  assert not any(x.startswith(('syscall=1107 ','syscall=1091 ')) for x in c['calls'])
  assert 'syscall=1040 v0=0xc a3=1' in c['returns']
  for phase,h in c['frames'].items():assert sha(d/(c['name']+'-'+phase+'.xwd'))==h
  cases.append(dict(name=c['name'],actual=c['actual'],window_observed=False,frames_identical=True,frame_sha256=c['frames']['before'],socket_or_connect_calls=0,elfmap_errno=12))
 report['runs'].append(dict(mode=r['mode'],clean_shutdown=True,native_clock_viewable=True,native_controls=len(r['cases']),native_trace_controls=r['native_trace_controls'],faults=r['faults'],cases=cases,result_sha256=sha(d/'result.json'),serial_sha256=sha(d/'serial.log'),directory=str(d.relative_to(root)),execution_sources=r['sources']))
assert seen=={'ci','ordinary'}
report['qualifier_sha256']=sha(Path(__file__).resolve())
args.output.write_text(json.dumps(report,indent=2)+'\n')
print('Eight xclock attempts and four root fault captures checked')
