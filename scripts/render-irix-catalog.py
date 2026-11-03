#!/usr/bin/env python3
"""Render the 2026-11-03–04 evidence into the maintained per-tab checklist."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parent.parent
report=json.loads((root/'docs/results/2026-11-03-irix-catalog.json').read_text())
inventory=root/'lab/irix-catalog/inventory.json'
assert hashlib.sha256(inventory.read_bytes()).hexdigest()==report['inventory_sha256']
inv=json.loads(inventory.read_text())
obs={o['case']['id']:o for o in report['observations']}
assert set(obs)=={c['id'] for c in inv['cases']}
reviews=report['reviews']
def esc(s):return s.replace('|','\\|').replace('`',"'").replace('\n',' ')
def diagnostic(o):
 lines=[x.strip() for x in (o['stdout']+'\n'+o['stderr']).splitlines() if x.strip()]
 lines=[x for x in lines if 'Gdk-WARNING **: shmget failed:' not in x]
 if not lines:return ''
 text=' '.join(lines)
 return ' '+esc(text[:210]+('…' if len(text)>210 else ''))
def result(e):
 if e.get('prior_qualification'):
  if e['name']=='gimp':return '[Prior bounded pass: setup, paint, XCF/PNG save/reopen, catalog launch and exit](results/2026-11-03-irix-gimp.md). Preference backup and wider plug-ins remain open.'
  if e['name']=='xmahjongg':return '[Prior bounded rendering/interaction pass](results/2026-11-03-newport-xmahjongg.md); a complete game remains unqualified.'
  return '[Prior bounded UTC/time pass](results/2026-11-01-irix-time.md); not repeated by this survey.'
 if e['kind']=='missing':
  return 'Unresolved target in the original source inventory; no launch attempted.'+(' The target contains command-line text; check registration/action handling.' if ' --' in e['target'] else '')
 if e['kind']=='directory':return 'Directory target; browsing and its payload remain untested.'
 if e['kind']=='document':return 'Document/web shortcut; assigned handler and destination remain untested.'
 o=obs[e['case']];v=reviews.get(e['case'])
 if v:
  labels={'launch-error':'Launch fails','usage-only':'Needs arguments','error-dialog':'Error dialog','main-window':'Main window opens','catalog-launch-fails':'Catalog launch fails','partial-use':'Partial use','busy-without-window':'Busy without a window','privilege-prompt':'Privilege prompt','information-dialog':'Information dialog','missing-x-extension':'Missing X extension','cleanup-unverified':'Cleanup not verified'}
  note=v['note']
  if v['ui']=='busy-without-window':note='Running and accumulating CPU time, with no viewable app window before the test stop. Late CPU samples are in the evidence; investigate whether a shared GNOME startup issue explains the pattern.'
  return '**'+labels[v['ui']]+'.** '+esc(note)
 status=o['status'];g=o['guard']
 if status=='window-observed':
  names=list(dict.fromkeys(w['name'].strip() or w['class_name'] for w in o['new_windows']))
  return '**Window observed.** '+esc(', '.join(names[:3]))+'. Use and normal exit remain untested.'+diagnostic(o)
 if status=='no-window-before-test-stop':
  note='**No window before test stop.**'
  if e['name']=='xwininfo':note+=' This tool needs interactive window selection; the survey supplied no selection.'
  return note+diagnostic(o)
 if status=='nonzero-exit':return '**Exits '+g['exit']+' without a window.**'+diagnostic(o)
 if status=='terminated-by-signal':return '**Terminates on signal '+g['signal']+'.**'+diagnostic(o)
 if status=='zero-exit-without-window':return '**Exits 0 without a new window.**'+diagnostic(o)
 if status=='observation-interrupted':return '**X observation interrupted.** The bounded X query failed; process cleanup and the guest halt are recorded. Repeat interactively before classifying the application.'+diagnostic(o)
 if status=='cleanup-unverified':return '**Cleanup not verified.** The application tracker failed; the disposable guest was halted.'+diagnostic(o)
 raise RuntimeError(status)
intro='''# Icon Catalog application checklist

Updated 2026-11-04 after the [startup survey](results/2026-11-03-irix-catalog.md).
This is the requested list to use when returning to failures one by one.
It preserves all **166 registered entries in 17 system tabs** from the supplied
IRIX 6.5.22 installation, including unresolved source links that the running
catalog may omit. The eighteenth page is the user's empty **Blank** page.
Click the stacked page edges at the bottom-right of Icon Catalog to open the
[menu of all pages](results/images/2026-11-03-irix-catalog-pages.png), including
those whose tabs do not fit along the bottom.

The current GIMP CHD was tested as **xiritest**, UID/GID 1234, HOME and cwd
`/usr/people/xiritest`, with accelerated 1280×1024 NetBSD Xorg. There were
**124 distinct direct program-target attempts**; repeated targets share the
same startup observation. GIMP, xmahjongg and xclock retain their separately
linked bounded results. The 19 document/web entries, 13 unresolved source
links and one directory target are distinguished below.

**A window is not a functional pass.** It may be a warning, privilege request
or setup dialog. The launch guard requested a stop at its 45-second deadline;
measured cleanup could take longer. Such a stop is not a normal GUI exit or
an application crash. CPU/process samples, exact output, window observations,
interrupted queries and cleanup failures are retained in the
[machine-readable evidence](results/2026-11-03-irix-catalog.json).

The [interactive checks](results/2026-11-03-irix-catalog-interactive.json)
exercise real catalog double-clicks for Acrobat and Freeware NEdit. NEdit
accepts visible text and restores its icon after Quit/Discard, but saving
fails; Acrobat's launcher reaches its missing Reader helper. Other aliases
still need individual double-click, running-icon, useful-action, persistence
and normal-exit tests. Terminal tools ran with stdin closed and may require
arguments or a terminal. System/hardware tools were observed without applying
settings or installing software.
'''
parts=[intro]
for page in sorted({e['page'] for e in inv['entries']}):
 entries=[e for e in inv['entries'] if e['page']==page]
 parts.append(f'\n## {page} ({len(entries)})\n\n| Entry | Original target | Observed result / next check |\n| --- | --- | --- |')
 for e in sorted(entries,key=lambda e:e['name'].lower()):parts.append(f"| `{esc(e['name'])}` | `{esc(e['target'])}` | {result(e)} |")
parts.append('\n## Blank (user page, 0)\n\nThe native directory listing confirms that `.desktop-xiri-indy/iconcatalog/pages/Blank`\nis empty. It is an additional user page, not a missing system-application tab.\n')
(root/'docs/ICON-CATALOG.md').write_text('\n'.join(parts))
print('Rendered',len(inv['entries']),'entries with',len(obs),'direct attempt records')
