# Original Toolchest resources and menu input

Validation passed: seven Toolchest runs, 73 frame captures, four native input
controls and four native Expose controls. Combined-resource pixels match
across both identities and execution modes; both guests halt cleanly.

The resource experiment separates two missing inputs. Original `XKeysymDB`
enables Motif key-name parsing and keyboard menu navigation. Explicit numeric
colors, taken from the original IRIX RGB table, provide SGIGray76 (`#c1c1c1`)
and SGIDarkGray (`#555555`). The original executable, libraries, menu definition
and app-defaults remain unchanged. No kernel or emulator change is involved.

The [lab](../../lab/irix-toolchest-input/README.md) contains the reproduction
commands, native input driver and [resource hashes](../../lab/irix-toolchest-input/resources.json).
Vendor resources, traces and screenshots remain under ignored `.work`. The
NetBSD source stays at `355e0ca310039839b426e66d00744edab5cd5608`, and IRIS at
`9df1df14334838a989253efefe26f0547e6da592`.

## Resource isolation

The CI matrix compares the existing resources, keysyms alone, colors alone,
and both, as uid 1234. The combined setup also runs as root, and ordinary
execution repeats it under both identities. Native XTEST and Expose controls
bracket each workload. All input targets the disposable guest's Xvfb display;
no host desktop input is generated.

The missing-keysyms baseline emits six translation-table syntax warnings. A
mouse click posts the Desktop menu, but Down, Right and Escape leave its
frame unchanged. The color-only stage isolates the same keyboard limitation
from the menu's appearance. With the original keysym database installed mode
0444 in the foreign namespace, keyboard traversal and Escape become usable.
The combined configuration emits no captured stderr.

The server's initial XLookupColor control rejects the two SGI color names and
accepts their numeric values. The experiment supplies the two values with
ordinary Xt `-xrm` options. It does not add general SGI color-name support to
X.org or establish a complete SGI theme. The original RGB table is retained
as provenance; simply copying a table is not the tested color mechanism.

## Menu behavior

The [SGI menu guidelines](https://techpubs.jurassic.nl/library/manuals/2000/007-2167-006/sgi_html/ch08.html)
motivate separate posting, traversal, cascading and dismissal checks. XTEST
provides server-generated input; a native observer verifies button coordinates,
press/release events and `send_event=0` independently.

| Phase with keysyms present | Viewable windows | Observed behavior |
| --- | ---: | --- |
| Rest | 8 | Toolchest and its descendants |
| Click Desktop | 13 | Posted menu |
| Down | 13 | Selection highlight moves to Shared Resources |
| Right | 15 | Cascading submenu opens |
| Escape | 13 | Submenu closes |
| Escape again | 8 | Posted menu closes; original pixels restored |

The combined-resource cases also set focus explicitly to Toolchest, press F10,
then Down to post a menu and Right to open a submenu. Escape closes the submenu;
the final cleanup restores the initial frame. This qualifies the measured
keyboard sequence after explicit focus, not window-manager focus policy.
The observer clears the viewable windows with Expose notifications and checks
that Toolchest restores its original pixels afterward.

Each client is intentionally terminated by its native parent at 90 seconds.
Frame capture happens during the input sequence; slow serial transfers happen
after the client exits. No application-launching item is selected. Spring-loaded
dragging, double clicks, timers, application launch, a window manager and a full
desktop session remain outside this checkpoint. In particular, gettimeofday
(1128) remains unimplemented on the tested kernel.

## Validation and retained evidence

The final [machine-readable report](2026-10-31-irix-toolchest-input.json) checks
resource/source pins, raw traces, parent observations, every frame hash,
pixel restoration, native controls and guest shutdowns. It also compares the
combined-resource frames across identities and execution modes.

The new full-frame PNG is retained privately at
`.work/irix-toolchest-input/screenshots/toolchest-menu-netbsd-xorg.png`, with
adjacent JSON provenance. It shows uid 1234 opening the Shared Resources
submenu in ordinary mode. Its source XWD SHA-256 is
`ccac67619c794897b3ed8c705e4d540a7d1cc2af0ac5f7d293bec85b9335ef81`.

Two initial diagnostics transferred screenshots inside the interaction window;
they were stopped cleanly to move transfers after client exit. A second pair
was stopped cleanly after the parallel winterm experiment exposed restrictive
permissions on freshly copied files. The final harness installs readable
resources explicitly and checks the resulting behavior as uid 1234. Those
four diagnostic runs are excluded from final qualification.

The separate [winterm experiment](2026-10-31-irix-winterm.md) reaches X but
does not yet produce a terminal window. Its fonts and locale data are evaluated
in the [font-import lab](../../lab/irix-x11-fonts/README.md). The earlier
[xclock libXmu/libXaw collision](2026-10-31-irix-xclock-elfmap.md) remains a
separate loader problem; this resource work does not implement relocation.
