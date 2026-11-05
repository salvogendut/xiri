"""Strict promotion gates for an installed xdm image and both user desktops."""
import json
import re
import shutil
import struct

from . import ROOT, sha256
from .xdm_image import support_files
from .fonts import verify as verify_fonts


def verify_sessions(r):
    assert r['scope']=='xdm-direct-chd' and r['status']=='passed'
    assert r['clean_shutdown'] and r['base_chd_unchanged'] and r['direct_disk_boot']
    assert 'unmounting done' in r['shutdown_log'][-2048:] and 'halting...' in r['shutdown_log'][-256:]
    assert 'ttyE0' in r['graphics_console'] and 'ttyZ0' in r['graphics_console']
    assert '1280x1024 pixels' in r['greeter_dimensions']
    assert 'Using XFree86 Acceleration Architecture (XAA)' in r['xorg_log']
    assert 'pam_authenticate failure' in r['xdm_log']
    assert {s['logout_route'] for s in r['sessions']}=={'toolchest','root-menu'}
    for entry in r['sessions']+[r['retry']]:
        assert entry['shell'][:3]==['xiritest','/usr/people/xiritest','/usr/people/xiritest']
        assert '1235' in entry['shell'][3].split()
        assert entry['shell'][4].startswith('/')
        assert '1280x1024 pixels' in entry['dimensions']
        assert 'RENDER_PASS pixels=8536 mismatches=0' in entry['render']
        assert re.search(r'GUARD .*absent=1 valid=1 .*remaining=0 ',entry['guard'])
        assert '"xlogin"' in entry['greeter_after']
    failed=r['failed_startup']
    assert re.search(r'GUARD .*exit=7 .*absent=1 valid=1 .*remaining=0 ',failed['guard'])
    assert '"xlogin"' in failed['greeter']
    native=r['native_login']
    assert native['shell']==['netbsdtest','/home/netbsdtest','/home/netbsdtest','1236']
    assert native['wm_pid']>0 and '"UXTerm"' in native['tree']
    assert '1280x1024 pixels' in native['dimensions'] and '"xlogin"' in native['greeter_after']
    if native.get('wheel_expected'):
        assert 'wheel' in native['groups'] and 'netbsdtest' in native['groups']
    if 'wm_process' in native:
        pid,ppid,state,command=native['wm_process']
        assert int(pid)==native['wm_pid'] and int(ppid)>0 and command.rsplit('/',1)[-1]=='ctwm' and not state.startswith('Z')
    assert set(r['survivors']) >= {'before-login','during-toolchest','after-toolchest',
        'during-root-menu','after-root-menu','after-failure','during-native-login','after-native-login','after-retry'}
    assert set(r['greeter_text']) >= {'xdm-greeter','xdm-after-toolchest','xdm-after-root-menu','xdm-after-native-login'}
    for text in r['greeter_text'].values():
        assert text['dark_pixels']>500 and text['light_pixels']>text['dark_pixels']
    launch=r['catalog_launch']
    assert launch['initial_pid']>0 and launch['launched_pid']>0 and launch['initial_pid']!=launch['launched_pid']
    assert launch['input']=='XTEST double-click' and launch['page']=='Freeware' and launch['target']=='xmahjongg'
    assert '"xmahjongg"' in launch['tree'] and 'granite' in launch['backdrop'] and 'pixmap id #' in launch['backdrop']
    assert '"/usr/freeware/bin/xmahjongg" Executing' in launch['execution_events']
    events=r['rpcbind_warning_events']
    assert 'XIRI_RPC_WATCH_START' in events and 'XIRI_RPC_WATCH_END' in events
    assert events.index('XIRI_RPC_WATCH_START')<events.index('XIRI_RPC_WATCH_END')
    assert 'rpcbind: cannot bind' not in events
    for key in ('native_control','native_after'):
        assert 'XIRI_ABI_PROBE' in r[key] and '_RC=0' in r[key]
    if 'winterm' in r:
        assert len(r['winterm'])==3
        for entry in r['winterm']:
            assert entry['foreground_resize']==[
                'READY rows=24 cols=80 foreground=1',
                'RESIZED rows=21 cols=66 SIGWINCH=1']
            assert re.search(r'rows=24 cols=(78|80)\b',entry['handoff'])
            if '/etc/xiri/Xresources' in r['installed_files']:
                cell = r.get('terminal_font', {}).get('cell', [8, 15])
                assert f'resize increment: {cell[0]} by {cell[1]}' in entry['initial_hints']
        extra=r['winterm'][0]
        assert re.search(r'rows=30 cols=(98|100)\b',extra['extra_handoff'])
        assert extra['normal_exit']['process_gone'] and extra['normal_exit']['window_gone']
        assert not extra['exit_stderr']
    if 'terminal_font' in r:
        profile = json.loads((ROOT/'lab/newport-text/font-profile.json').read_text())
        assert r['terminal_font'] == profile
        for path, digest in [(profile['resource'], profile['resource_sha256']),
                             (profile['greeter_resource'], profile['greeter_resource_sha256']),
                             (profile['native_file'], profile['native_file_sha256']),
                             ('/usr/X11R7/lib/modules/drivers/newport_drv.so', profile['newport_module_sha256'])]:
            assert r['installed_files'][path] == digest
        assert len(r.get('winterm', [])) == 3
        assert set(r.get('font_checks', {})) == {'greeter', 'irix-1', 'irix-2', 'irix-3', 'native'}
    for entry in r.get('font_checks', {}).values():
        verify_fonts(entry)


def qualify(a, verify_irix_module):
    r=json.loads((a.run/'result.json').read_text())
    verify_sessions(r)
    bundle=ROOT/r['bundle']
    sources=[bundle/'manifest.json',bundle/'verification/build-manifest.json',
             *sorted((bundle/'verification').glob('manifest-*.json'))]
    source=next(p for p in sources if p.exists() and sha256(p)==r['input_manifest_sha256'])
    m=json.loads(source.read_text())
    assert m['status']=='chd-roundtrip-verified' and m['session_manager']=='xdm'
    assert m['source_raw_sha256']==m['decoded_raw_sha256'] and m['logical_bytes']==8589934592
    assert sha256(bundle/'netbsd-xiri.chd')==m['chd_sha256']==r['chd_sha256']
    for path,key in [('seed-result.json','source_result_sha256'),('copy-ledger.json','copy_ledger_sha256'),
                     ('permissions.json','permission_manifest_sha256'),('iris.toml','config_sha256')]:
        assert sha256(bundle/path)==m[key],path
    for path,digest in m['emulator_files'].items():assert sha256(bundle/path)==digest,path
    assert sha256(bundle/m['qualification_nvram'])==m['qualification_nvram_sha256']==m['manual_nvram_sha256']
    assert sha256(ROOT/m['baseline'])==m['baseline_sha256']
    assert r['pin']==m['pin']==json.loads((ROOT/m['baseline']).read_text())
    assert sha256(bundle/'irix-module-build.json')==m['pin']['module_build_manifest_sha256']
    assert sha256(ROOT/m['pin']['module_build_manifest'])==m['pin']['module_build_manifest_sha256']
    seed=json.loads((bundle/'seed-result.json').read_text())
    assert m['kernel_msgbuf_symbol']==seed['kernel_msgbuf_symbol']
    verify_irix_module(m['pin'],seed,json.loads((bundle/'irix-module-build.json').read_text()),r)
    assert r['support_files_verified']==support_files(bundle,seed)
    for path,digest in r['installed_files'].items():assert digest==seed['installed_files'][path],path
    for path,digest in r['sources'].items():assert sha256(ROOT/path)==digest,path
    # The image keeps its recorded runtime revision while the host checkout
    # evolves. Installed guest bytes above, not today's runtime sources, are
    # the execution contract for a check of an older selected image.
    assert sha256(bundle/'desktop-behavior-resources.json')==seed['desktop_behavior']['resource_ledger_sha256']
    assert sha256(bundle/'native-fam-source.json')==seed['native_fam_build']['source_manifest_sha256']
    screenshots={}
    for name,target in [('xdm-catalog-launch',a.png),('xdm-native-ctwm',a.png.with_stem(a.png.stem+'-native')),
                        ('xdm-greeter',a.png.with_stem(a.png.stem+'-greeter'))]:
        frame=a.run/(name+'.png');assert sha256(frame)==r['screenshots'][name]
        assert struct.unpack('>II',frame.read_bytes()[16:24])==(1282,1024)
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(frame,target)
        screenshots[name]=dict(path=str(target),sha256=sha256(target),source=str(frame),
                              dimensions=[1282,1024],method='IRIS ordinary GL scanout',byte_identical=True)
    report=dict(r,status='disk-boot-and-xdm-desktops-verified',
        qualifier_sha256=sha256(ROOT/'scripts/xiri_lab/xdm_qualification.py'),
        directory=str(a.run),result_sha256=sha256(a.run/'result.json'),serial_sha256=sha256(a.run/'serial.log'),
        raw_sha256=m['source_raw_sha256'],chd_bytes=m['chd_bytes'],logical_bytes=m['logical_bytes'],
        session_manager='xdm',screenshots=screenshots,desktop_dimensions=[1280,1024],xaa_enabled=True,
        runtime_sources=seed['runtime_sources'],
        limitations=['Winterm startup font metrics remain imperfect; input checks resize its window.',
                     'Native ctwm logout is tested through its terminal, not its Quit menu.',
                     'FAM supports one configured IRIX desktop account; clogin and saved sessions remain open.',
                     'The greeter uses Xft.render:false; the underlying Render glyph issue remains open.',
                     'Kernel/module require Xiri fork hooks; physical hardware is unqualified.'])
    if 'winterm' in r:
        for entry in r['winterm']:
            frame=a.run/entry['untouched_png']
            assert sha256(frame)==entry['untouched_png_sha256']
            assert struct.unpack('>II',frame.read_bytes()[16:24])==(1282,1024)
        frame=a.run/r['winterm'][0]['untouched_png']
        target=a.png.with_stem(a.png.stem+'-winterm')
        shutil.copyfile(frame,target)
        report['screenshots']['winterm-untouched']=dict(path=str(target),sha256=sha256(target),source=str(frame),
            dimensions=[1282,1024],method='IRIS ordinary GL scanout',byte_identical=True)
        if 'terminal_font' in r:
            report['terminal_font'] = r['terminal_font']
            report['limitations'][0] = 'The explicit Courier bitmap avoids the reproduced scalable Type1 metric collapse; the Type1 defect remains open.'
            report['limitations'][3] = 'Native core and Xft/Render text pass with the Newport software-fallback correction; arbitrary Render operators and physical hardware are unqualified.'
        elif '/etc/xiri/Xresources' in r['installed_files']:
            report['terminal_font']=dict(resource='/etc/xiri/Xresources',
                face='-sgi-screen-medium-r-normal--15-150-72-72-m-80-iso8859-1',cell=[8,15])
            report['limitations'][0]='The SGI Screen bitmap default avoids the reproduced Type1 font collapse; the native Type1 metric defect remains open.'
        else:
            report['limitations'][0]='Three untouched winterm starts, resizing and normal exit pass; this image retains the wildcard font choice and its intermittent collapse remains possible.'
    if 'menu_captures' in r:
        assert set(r['menu_captures']) == {'desktop', 'selected', 'internet', 'find',
            'system', 'help', 'access-files', 'shared-resources', 'customize', 'utilities'}
        report['menu_captures'] = {}
        for name, entry in r['menu_captures'].items():
            frame = a.run/entry['path']
            assert sha256(frame) == entry['sha256']
            assert struct.unpack('>II', frame.read_bytes()[16:24]) == (720, 620)
            report['menu_captures'][name] = dict(path=str(frame), sha256=sha256(frame),
                dimensions=[720, 620],
                method='IRIS ordinary GL scanout; capture integrity only; visual review is separate')
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2)+'\n')
    if a.promote or a.record_bundle:
        # Keep both original PROM profiles and all manual overlays untouched.
        original=bundle/'verification/build-manifest.json'
        if not original.exists():shutil.copyfile(bundle/'manifest.json',original)
        retained=bundle/'verification'/('manifest-'+sha256(source)+'.json')
        if source.resolve()!=retained.resolve():shutil.copyfile(source,retained)
        shutil.copyfile(a.run/'nvram.bin',bundle/'verification/tested-graphics-nvram.bin')
        promoted=dict(m,direct_chd_boot='verified',
                      xdm={**m['xdm'],'image_login_qualification':'verified'},qualification=str(a.output),
                      qualification_sha256=sha256(a.output),qualification_run=str(a.run))
        if 'winterm' in r:
            promoted['winterm_checks']=True
        (bundle/'manifest.json').write_text(json.dumps(promoted,indent=2)+'\n')
    if a.promote:
        public={key:m[key] for key in ('chd_sha256','chd_bytes','logical_bytes','nvram_sha256',
                'config_sha256','copy_ledger_sha256','permission_manifest_sha256','manual_nvram_sha256',
                'manual_console','emulator_files')}
        public.update(schema=1,bundle=r['bundle'],image=r['bundle']+'/netbsd-xiri.chd',
            raw_sha256=m['source_raw_sha256'],kernel_source=m['pin']['source_revision'],
            kernel_source_equivalent_commit=m['pin']['committed_source_revision'],
            emulator_revision=m['pin']['emulator_revision'],qualification=str(a.output),
            qualification_sha256=sha256(a.output),session_manager='xdm',xdm=promoted['xdm'],
            irix_module=r['irix_module'],module_build_manifest_sha256=m['pin']['module_build_manifest_sha256'],
            newport_driver_sha256=seed['newport_driver']['sha256'],xaa_enabled=True,
            desktop_behavior_resource_ledger_sha256=seed['desktop_behavior']['resource_ledger_sha256'],
            native_fam_source_manifest_sha256=seed['native_fam_build']['source_manifest_sha256'])
        (ROOT/'lab/irix-installed-desktop/image.json').write_text(json.dumps(public,indent=2)+'\n')
    print('Verified CHD autoboot, xdm/4Dwm/ctwm login cycles, catalog launch, full-screen XAA and cleanup')
