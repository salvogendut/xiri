#!/usr/bin/env python3
"""Validate private xwsh fault/lookup captures and publish metadata only."""
import argparse,collections,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=argparse.ArgumentParser(description=__doc__);p.add_argument('runs',nargs=2,type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
report=dict(schema=1,status='fault-and-resource-boundary-observed',kernel_pin=json.loads((ROOT/'lab/irix-siocnread/baseline.json').read_text()),runs=[],terminal_window_qualified=False)
seen=set()
for d in a.runs:
 r=json.loads((d/'result.json').read_text());assert r['status']=='observed' and r['clean_shutdown'] and r['lookups'] and r['pin']==report['kernel_pin']
 assert r['mode'] not in seen;seen.add(r['mode']);assert len(r['controls'])==2 and len(r['cases'])==4
 for c in r['controls']:assert c['guards_intact'] and c['entry_exit']==37 and 'Map State: IsViewable' in c['window'] and not c['stderr']
 cases=[]
 for c in r['cases']:
  assert c['signal']==11 and c['code']==1 and int(c['address'],16)==16 and int(c['pc'],16)==0x10024394
  f=d/(c['name']+'.trace');raw=f.read_text();regs={int(k):int(v,16) for k,v in re.findall(r'(\d+)=([0-9a-f]+)',re.findall(r'^REGS (.*)$',raw,re.M)[-1])}
  assert regs[9]==0 and regs[25]==0xf60c370 and regs[35]==16 and regs[36]&0x80000000 and regs[37]==0x10024394
  mem=re.search(r'^MEM pc address=([0-9a-f]+) error=0 bytes=128 hex=([0-9a-f]+)$',raw,re.M);assert mem
  pcbytes=bytes.fromhex(mem[2]);off=0x10024398-int(mem[1],16);assert int.from_bytes(pcbytes[off:off+4],'big')==0x8d240010
  paths=[]
  for h in re.findall(r'^MEM access-path .*?error=0 .*?hex=([0-9a-f]+)$',raw,re.M):
   b=bytes.fromhex(h);assert b'\0' in b;paths.append(b.split(b'\0')[0].decode())
  calls=re.findall(r'^LOOKUP name=(\w+) a0=(\w+) a1=(\w+) a2=(\w+) ra=(\w+)$',raw,re.M)
  returns=re.findall(r'^LOOKUP_RETURN name=(\w+) v0=(\w+) a3=(\w+)$',raw,re.M)
  assert len(calls)==len(returns) and all(int(v,16)==89 and int(e,16)==1 for _,v,e in returns)
  assert collections.Counter(x[0] for x in calls)==collections.Counter(x[0] for x in returns)
  assert len(paths)==sum(x[0]=='access' for x in calls)
  assert '/usr/lib/X11/locale/C/XLC_LOCALE' in paths and '/usr/lib/X11/app-defaults/XWsh' in paths
  seeks=collections.Counter()
  for name,fd,offset,whence,ra in calls:
   if name!='lseek':continue
   assert int(ra,16)==0xfa57690
   value=int(offset,16);value=value-(1<<64) if value&(1<<63) else value
   seeks[(int(fd,16),value,int(whence,16))]+=1
  assert seeks and all(offset<0 and whence==1 for _,offset,whence in seeks)
  cases.append({**c,'faulting_instruction':'lw a0,16(a5) in the delay slot at 0x10024398','null_object_register':'a5 (register 9)','call_target':'XmbTextEscapement (0x0f60c370), not reached','access_paths':sorted(set(paths)),'call_counts':dict(collections.Counter(x[0] for x in calls)),'all_lookup_errno':89,'lseek_caller':'fflush + 0x274 (return address 0x0fa57690)','seeks':[dict(fd=fd,offset=offset,whence=whence,count=n) for (fd,offset,whence),n in sorted(seeks.items())],'trace_sha256':sha(f),'kdump_sha256':sha(d/(c['name']+'.kdump'))})
 report['runs'].append(dict(directory=str(d),mode=r['mode'],clean_shutdown=True,result_sha256=sha(d/'result.json'),controls=r['controls'],cases=cases,execution_sources=r['sources']))
assert seen=={'ci','ordinary'}
report['qualifier_sha256']=sha(Path(__file__));a.output.write_text(json.dumps(report,indent=2)+'\n');print('Eight fault captures and their resource lookups checked')
