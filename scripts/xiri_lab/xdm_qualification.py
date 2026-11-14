"""Strict promotion gates for an installed xdm image and both user desktops."""
import json
import re
import shutil
import struct

from . import ROOT, sha256
from .xdm_image import support_files
from .fonts import verify as verify_fonts


def verify_job_control(entry):
    assert entry['status'] == 'passed'
    assert set(entry['shells']) == {'native', 'irix'}
    for shell in entry['shells'].values():
        proof = shell['proof']
        assert proof[:3] == ['xiritest', '/usr/people/xiritest', '/usr/people/xiritest']
        assert {'i', 'm'} <= set(proof[4]) and shell['monitor_enabled_at_start']
        foreground = shell['stop_resume']
        worker = foreground['worker']
        assert worker['uid'] == 1234 and worker['foreground'] == 1
        assert worker['pid'] == worker['pgid'] == worker['tpgid']
        assert worker['pgid'] != int(proof[3])
        assert re.search(r'Stopped|Suspended', foreground['stopped'], re.I)
        assert 'Running' in foreground['background']
        assert foreground['exit'] == 42
        assert '\nCONT\n' in foreground['events'] and foreground['events'].endswith('INT\n')
        read = shell['background_read']
        assert read['worker']['uid'] == 1234 and read['worker']['foreground'] == 0
        assert re.search(r'Stopped|Suspended', read['jobs'], re.I)
        assert read['exit'] == 0 and read['events'].endswith('READ\n')
        assert shell['background_wait']['exit'] == 37
    clean = r'GUARD .*absent=1 valid=1 .*remaining=0 '
    assert re.search(r'GUARD .*exit=0 signal=0 stopped=0 absent=1 valid=1 '
                     r'.*remaining=0 reason=leader-exit uid=1234 gid=1234 ',
                     entry['shells']['irix']['terminal_guard'])
    assert re.search(clean, entry['logout_guard'])
    jobs = entry['logout_jobs']
    assert jobs['running']['uid'] == jobs['stopped']['uid'] == 1234
    assert jobs['running']['foreground'] == 0 and jobs['stopped']['foreground'] == 1
    assert len({jobs['running']['pid'], jobs['stopped']['pid'], jobs['shell_pid']}) == 3
    assert entry['archive']['path'] == 'job-control.tgz'


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
        if '/usr/local/libexec/xiri/save-session' in r['installed_files']:
            assert 'SESSION_SAVE acknowledged by 4Dwm' in entry['guard']
            assert 'SESSION_SAVE completed=1 exit=0 ' in entry['guard']
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
    if 'job_control' in r or 'scripts/xiri_lab/job_control.py' in r.get('sources', {}):
        verify_job_control(r['job_control'])
    if 'lab/irix-desktop-behavior/colour-names.c' in r.get('sources', {}):
        checks = r['colour_checks']
        assert sum(c['user'] == 'xiritest' for c in checks) == 3
        if 'multiuser' in r:
            assert sum(c['user'] == 'xiritest2' for c in checks) == 1
        for check in checks:
            assert 'COLOUR_NAMES entries=142 failures=0' in check['output']
            assert len(re.findall(r'^PASS name=', check['output'], re.M)) == 142
            assert re.search(r'^Background\*useGl:\s+False$', check['resources'], re.M)
    if 'scripts/xiri_lab/multiuser.py' in r.get('sources', {}):
        multi = r['multiuser']
        fam = multi['fam']
        assert fam['status'] == 'passed' and fam['native_databases_unchanged']
        for user, uid in [('xiritest', 1234), ('xiritest2', 1237)]:
            assert (f'FAM_MULTIUSER_PASS uid={uid} own=1 supplementary=1 '
                    'other=0 forged_root=0 created=1 deleted=1') in fam['concurrent_clients'][user]
        second = multi['second_session']
        assert second['catalog_pages'] == 17
        assert re.search(r'Icon Catalog:.*\(Page [0-9]+ of 17\)', second['tree'])
        assert second['shell'][:3] == ['xiritest2', '/usr/people/xiritest2', '/usr/people/xiritest2']
        assert '1235' in second['shell'][3].split()
        assert '1280x1024 pixels' in second['dimensions']
        assert 'RENDER_PASS pixels=8536 mismatches=0' in second['render']
        assert re.search(r'GUARD .*absent=1 valid=1 .*remaining=0 ', second['guard'])
        assert '"xlogin"' in second['greeter_after']
        assert {home['user'] for home in multi['homes']} == {'xiritest', 'xiritest2'}
        assert sum(home['user'] == 'xiritest' for home in multi['homes']) == 3
        for home in multi['homes']:
            assert home['private_state'] and home['owner_verified'] and home['desktop_links']
        assert {'during-second-user', 'after-second-user'} <= set(r['survivors'])
    if '/usr/local/libexec/xiri/save-session' in r['installed_files']:
        saved = r['saved_sessions']
        primary = [entry for entry in saved if entry['user'] == 'xiritest']
        assert len(primary) == 3
        assert primary[0]['restore'].startswith('mode=no ')
        assert all(entry['restore'].startswith('mode=yes ') for entry in primary[1:])
        for entry in saved:
            assert entry['counts'] == dict(winterm=1, xclock=1, catalog=1)
            assert '"/usr/libexec/xiri-shell" }' in entry['restart_command']
            assert '/session.' not in entry['restart_command']


def qualify(a, verify_irix_module):
    r=json.loads((a.run/'result.json').read_text())
    verify_sessions(r)
    bundle=ROOT/r['bundle']
    sources=[bundle/'manifest.json',bundle/'verification/build-manifest.json',
             *sorted((bundle/'verification').glob('manifest-*.json'))]
    source=next(p for p in sources if p.exists() and sha256(p)==r['input_manifest_sha256'])
    m=json.loads(source.read_text())
    if m.get('multiuser_checks') or 'xiritest2' in m.get('xdm', {}).get('accounts', {}):
        assert 'scripts/xiri_lab/multiuser.py' in r['sources'] and 'multiuser' in r
    if m.get('job_control_checks'):
        verify_job_control(r['job_control'])
    if m.get('colour_checks') or 'runtime/libexec/sgi-colours.awk' in m.get('runtime_sources', {}):
        assert 'lab/irix-desktop-behavior/colour-names.c' in r['sources'] and r['colour_checks']
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
    # A prepared disk can record dirty build inputs honestly. Establish later
    # committed equivalence separately; do not rewrite its pin or observation.
    build = json.loads((bundle/'irix-module-build.json').read_text())
    source_commit = m['pin'].get('committed_source_revision')
    equivalent = {}
    if source_commit is None:
        path = a.source_equivalence or (ROOT/m['pin']['module_build_manifest']).with_name('source-equivalence.json')
        path = path.resolve()
        if path.exists():
            equivalent = json.loads(path.read_text())
            assert equivalent['status'] == 'source-equivalent'
            assert equivalent['build_manifest_sha256'] == m['pin']['module_build_manifest_sha256']
            assert equivalent['source_files'] == build['source_files']
            assert equivalent['branch'] == 'xiri' and equivalent['tracked_clean']
            source_commit = equivalent['commit']
            assert re.fullmatch('[0-9a-f]{40}', source_commit)
            report['source_equivalence'] = dict(path=str(path.relative_to(ROOT)),
                sha256=sha256(path), commit=source_commit)
    if a.promote:
        assert source_commit, 'Commit and verify the built source before promoting this image'
    core_commit = source_commit
    # A later committed-source record can identify the reused core without
    # rewriting the frozen build manifest or the cold-boot observation.
    core_provenance = build.get('core_kernel_provenance') or equivalent.get('core_kernel_provenance')
    if core_provenance:
        # A module-only update can deliberately retain a previously qualified
        # core. Do not describe the current module checkout as that core's
        # source merely because both are packaged in the same image.
        core_path = ROOT/core_provenance['manifest']
        assert sha256(core_path) == core_provenance['manifest_sha256']
        core_build = json.loads(core_path.read_text())
        for name in ('netbsd', 'netbsd.boot'):
            assert core_build['artifacts'][name]['sha256'] == build['artifacts'][name]['sha256']
        assert core_build['debug_kernel_sha256'] == build['debug_kernel_sha256']
        core_equivalent = json.loads(core_path.with_name('source-equivalence.json').read_text())
        assert core_equivalent['status'] == 'source-equivalent'
        assert core_equivalent['build_manifest_sha256'] == sha256(core_path)
        assert core_equivalent['source_files'] == core_build['source_files']
        core_commit = core_provenance['source_equivalent_commit']
        assert core_commit == core_equivalent['commit']
        report['core_kernel_provenance'] = core_provenance
    report['kernel_source_equivalent_commit'] = core_commit
    report['module_source_equivalent_commit'] = source_commit
    if 'job_control' in r:
        jobs = r['job_control']
        assert sha256(a.run/jobs['archive']['path']) == jobs['archive']['sha256']
        for name, digest in jobs['screenshots'].items():
            frame = a.run/name
            assert sha256(frame) == digest
            assert struct.unpack('>II', frame.read_bytes()[16:24]) == (1282, 1024)
            target = a.png.with_stem(a.png.stem+'-'+frame.stem)
            shutil.copyfile(frame, target)
            report['screenshots'][frame.stem] = dict(path=str(target), sha256=digest,
                source=str(frame), dimensions=[1282, 1024], method='IRIS ordinary scanout', byte_identical=True)
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
            report['limitations'][0] = 'Winterm uses explicit bitmap Courier; these desktop checks do not qualify scalable Type1 metrics. See the matching kernel qualification.'
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
    if 'multiuser' in r:
        report['limitations'][2] = ('Two IRIX accounts pass xdm login switching and concurrent FAM access; '
            'simultaneous graphical seats, original clogin and saved sessions remain unqualified.')
        frame = a.run/'xdm-desktop-xiritest2.png'
        assert sha256(frame) == r['screenshots']['xdm-desktop-xiritest2']
        assert struct.unpack('>II', frame.read_bytes()[16:24]) == (1282, 1024)
        target = a.png.with_stem(a.png.stem+'-second-user')
        shutil.copyfile(frame, target)
        report['screenshots']['second-user'] = dict(path=str(target), sha256=sha256(target),
            source=str(frame), dimensions=[1282, 1024], method='IRIS ordinary GL scanout', byte_identical=True)
    if 'saved_sessions' in r:
        report['limitations'][2] = ('Original clogin and simultaneous graphical seats remain unqualified. '
            'The tested applications restore after normal logout; arbitrary applications and additional desks need separate checks.')
        if '/usr/local/libexec/xiri/stop-sessions' in seed['installed_files']:
            report['shutdown_session_service'] = True
            report['limitations'].append(
                'Use shutdown -r/-h/-p now for ordered session saving. Direct reboot/halt/poweroff '
                'bypass rc.shutdown; emulator termination and power loss cannot save an active desktop.')
        else:
            report['limitations'].append('Log out before shutdown/reboot: xdm can close an active X display before 4Dwm completes its save.')
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
        if 'saved_sessions' in r:
            promoted['saved_session_checks']=True
        if 'job_control' in r:
            promoted['job_control_checks']=True
        if 'multiuser' in r:
            promoted['multiuser_checks'] = True
        if 'colour_checks' in r:
            promoted['colour_checks'] = True
        (bundle/'manifest.json').write_text(json.dumps(promoted,indent=2)+'\n')
    if a.promote:
        public={key:m[key] for key in ('chd_sha256','chd_bytes','logical_bytes','nvram_sha256',
                'config_sha256','copy_ledger_sha256','permission_manifest_sha256','manual_nvram_sha256',
                'manual_console','emulator_files')}
        public.update(schema=1,bundle=r['bundle'],image=r['bundle']+'/netbsd-xiri.chd',
            raw_sha256=m['source_raw_sha256'],kernel_source=m['pin']['source_revision'],
            kernel_source_equivalent_commit=core_commit,
            module_source_equivalent_commit=source_commit,
            emulator_revision=m['pin']['emulator_revision'],qualification=str(a.output),
            qualification_sha256=sha256(a.output),session_manager='xdm',xdm=promoted['xdm'],
            irix_module=r['irix_module'],module_build_manifest_sha256=m['pin']['module_build_manifest_sha256'],
            newport_driver_sha256=seed['newport_driver']['sha256'],xaa_enabled=True,
            desktop_behavior_resource_ledger_sha256=seed['desktop_behavior']['resource_ledger_sha256'],
            native_fam_source_manifest_sha256=seed['native_fam_build']['source_manifest_sha256'])
        (ROOT/'lab/irix-installed-desktop/image.json').write_text(json.dumps(public,indent=2)+'\n')
    print('Verified CHD autoboot, xdm/4Dwm/ctwm login cycles, catalog launch, full-screen XAA and cleanup')
