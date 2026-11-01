#!/usr/bin/env python3
"""Check real time returns, X pixels and cleanup for original xclock."""
import argparse,hashlib,importlib.util,json,re,subprocess,tomllib
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent

def module(name,path):
    s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
clock=module('clock','scripts/qualify-irix-time.py')
traces=module('traces','scripts/qualify-irix-installer-dupfd.py')
sha=clock.sha

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runs',nargs=2,type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    pin=json.loads((ROOT/'lab/irix-time/baseline.json').read_text())
    report=dict(schema=1,status='passed',pin=pin,pin_label_note=clock.PIN_LABEL_NOTE,qualifier_sha256=sha(Path(__file__)),runs=[],clocks=0)
    modes=set()
    for d in a.runs:
        r=json.loads((d/'result.json').read_text())
        assert r['status']=='observed' and r['clean_shutdown']
        clock.check_pin(r['pin'],pin)
        assert r['mode'] not in modes;modes.add(r['mode'])
        assert tomllib.loads((d/'iris.toml').read_text())['ci']==(r['mode']=='ci')
        assert sha(ROOT/r['seed']/'result.json')==r['seed_result_sha256']
        for path,h in r['sources'].items():assert sha(ROOT/path)==h
        assert r['native_x11_before'] and r['native_x11_after']
        required={(phase,uid,n) for phase in ['before','after'] for uid in [0,1234] for n in ['native-o32','vendor-asa','vendor-echo']}
        assert len(r['controls'])==12 and {(c['phase'],c['uid'],c['name']) for c in r['controls']}==required
        for c in r['controls']:
            name=c['name'];out={'native-o32':'XIRI_ABI_PROBE\n','vendor-asa':'XIRI_VENDOR_O32\n','vendor-echo':'XIRI_VENDOR_N32\n'}[name]
            assert c['actual']==dict(errno_bytes=0,errno=0,exit=37 if name=='native-o32' else 0,signal=0,killed=0,stdout=out,stderr='')
        assert len(r['xclock'])==4 and {(c['uid'],c['style']) for c in r['xclock']}=={(u,s) for u in [0,1234] for s in ['analog','digital']}
        summary=[]
        for c in r['xclock']:
            assert c['actual']==dict(errno_bytes=0,errno=0,exit=-1,signal=9,killed=1,stdout='',stderr=''),c['actual']
            assert c['group_absent'] and 'Map State: IsViewable' in c['window']
            lo,hi=clock.clock_bounds(c)
            raw=(d/(c['name']+'.kdump')).read_text();pairs=traces.pairs(raw)
            calls={n:[p for p in pairs if p['call']['syscall']==n] for n in [1013,1128]}
            assert len(calls[1013])>=5 and len(calls[1128])>=5,(c['name'],{n:len(v) for n,v in calls.items()})
            seconds=[p['result']['v0'] for p in calls[1013]]
            assert all(p['result']['a3']==0 and lo<=p['result']['v0']<=hi for p in calls[1013])
            assert seconds==sorted(seconds) and seconds[-1]-seconds[0]>=5
            assert all(p['result']==dict(syscall=1128,v0=0,a3=0) for p in calls[1128])
            pixels={}
            for phase,h in c['frames'].items():
                f=d/(c['name']+'-'+phase+'.xwd');assert sha(f)==h
                pixels[phase]=subprocess.check_output(['magick',str(f),'-depth','8','RGB:-'])
                assert len(pixels[phase])==640*480*3
            changes={phase:sum(pixels['before'][i:i+3]!=pixels[phase][i:i+3] for i in range(0,len(pixels[phase]),3)) for phase in ['after','redraw']}
            assert all(v>=2 for v in changes.values()),changes
            # Gray client interiors contain black hands/ticks or text. An
            # erased/blank window must not pass merely because pixels changed.
            width,height=(600,90) if c['style']=='digital' else (240,240)
            ink={phase:sum(rgb[(y*640+x)*3:(y*640+x)*3+3]==b'\0\0\0' for y in range(21,21+height) for x in range(21,21+width)) for phase,rgb in pixels.items()}
            assert min(ink.values())>100 and all(ink['before']/2<v<ink['before']*2 for v in ink.values()),ink
            summary.append(dict(name=c['name'],uid=c['uid'],style=c['style'],guest_utc_bounds=[lo,hi],time_calls=len(seconds),seconds_advanced=seconds[-1]-seconds[0],gettimeofday_calls=len(calls[1128]),changed_pixels=changes,interior_ink_pixels=ink,frames=c['frames'],trace_sha256=sha(d/(c['name']+'.kdump')),viewable=True,group_absent=True))
        report['runs'].append(dict(directory=str(d),result_sha256=sha(d/'result.json'),serial_sha256=sha(d/'serial.log'),mode=r['mode'],native_controls=12,native_x11_before=True,native_x11_after=True,clean_shutdown=True,clocks=summary))
        report['clocks']+=4
    assert modes=={'ci','ordinary'}
    report['limits']=['Four bounded 18-second vendor launches per mode; watchdog cleanup is intentional for these interactive clients.',
        'UTC0 only; local timezone/DST and longer sessions are unqualified.',
        'Digital text/date also require visual review of retained frames against the recorded guest UTC bounds. Pixel changes alone do not establish correct displayed text.']
    a.output.write_text(json.dumps(report,indent=2)+'\n');print('Passed eight original xclock update/redraw runs')
if __name__=='__main__':main()
