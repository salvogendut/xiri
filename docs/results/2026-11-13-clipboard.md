# Text clipboard interoperability

Status: qualified on 2026-11-13. All 19 exact payload checks, user/session
checks, clean halt and the unchanged base CHD hash pass.

The current File Manager CHD supports text exchange between native NetBSD
xterm, original IRIX winterm and original IRIX gedit 0.9.7. These clients
share the native Xorg display. This cycle adds a repeatable GUI/protocol
probe and a [clipboard guide](../IRIX-CLIPBOARD.md); it changes no kernel,
module, desktop runtime or imported vendor resource.

## Behavior and checks

The [cold-image result](2026-11-13-clipboard.json) records exact payload
hashes, selection targets, ownership states, identities and cleanup.
The [maintained lab](../../lab/clipboard/README.md) uses real XTest gestures
and checks the received/saved files. A native Xlib control supplements the
actual applications for target inspection and incremental-transfer tests.

| Path or condition | Bounded acceptance |
| --- | --- |
| Native xterm → winterm, PRIMARY | Left-drag and middle paste produce the complete expected text |
| Winterm → native xterm, PRIMARY | Same check in the reverse direction |
| Original gedit Copy | Native client receives the exact original multiline/tab document |
| Native owner ↔ gedit | Short multiline/tab text and Latin-1 bytes survive paste/save/copy unchanged |
| Large native/IRIX exchange | 113,664 bytes match in each direction; both use INCR |
| Native xterm ↔ gedit, CLIPBOARD | Real xterm selection/paste in `selectToClipboard` mode exchanges text with gedit Copy/Paste |
| PRIMARY versus CLIPBOARD | Different simultaneous text remains independently readable |
| Source exit | Normal gedit exit releases CLIPBOARD ownership |
| Logout and switching users | xdm clears both selections and all eight cut buffers; xiritest2 and native netbsdtest create fresh selections |
| Cleanup | Both IRIX session guards report zero remaining descendants; native ctwm returns to xdm; guest halts cleanly and the base CHD hash matches |

The native producer forces 1 KiB INCR chunks. The reverse large conversion
comes from the original editor, exercising its own incremental implementation.
The fixture does not install a clipboard bridge or manager. The independent
host regression suite also passes all 58 tests.

The [IRIX/native exchange PNG](images/2026-11-13-clipboard.png) and
[native-user PNG](images/2026-11-13-clipboard-native.png) are unmodified
captures of the graphical emulator framebuffer. Active Xorg dimensions are
1280×1024; IRIS includes its two additional scanout columns in the PNG.

## Gestures and limits

Default winterm and native xterm mouse selection/middle paste use PRIMARY.
Gedit's Edit → Copy/Paste uses CLIPBOARD. Gedit 0.9.7 provides Select All in
the Edit menu without a displayed Ctrl+A accelerator. The image's xterm 397
does not bind Ctrl+Shift+C to Copy by default. Its documented
`-xrm '*selectToClipboard: true'` setting supplies the tested clipboard mode.

Winterm advertises `STRING`; gedit also offers `TEXT` and `COMPOUND_TEXT`.
The native producer's refused COMPOUND_TEXT conversion falls back to STRING
successfully. The Latin-1 check includes `é`, `è` and `£`. Gedit explicitly
refuses `UTF8_STRING`; arbitrary Unicode conversion is not qualified.

There is no clipboard manager in the default session. Closing the source
can release copied text; a legacy cut buffer can remain within the same
session until xdm resets the display. Clipboard history/keep-after-exit,
image/rich-text formats, drag-and-drop and host-machine clipboard integration
remain separate work. These results do not qualify every catalog application.

Exploratory runs established the gestures and exposed assumptions in the
test driver: selection endpoints, changing window titles and winterm's
TARGETS property label. One early replay was stopped for a window-title
lookup correction; another failed a checker that expected an asterisk in
gedit's edited title. Their logs and clean halts are retained, and they are
excluded from final acceptance. The final probe observes the actual title
change before saving and requires exact file content.

## Existing manual image and fork checkpoint

Use the current selected image with `./xiri run`, or:

```sh
.work/images/xiri-netbsd-desktop-20261113-filemanager/run-iris.sh
```

No replacement CHD is needed. Its SHA-256 remains
`ac2e0702746448da893a623045cee06d359bbe6b8dc0f96668d66d3b8e9ec06e`.
The native core, `8bf86af` compatibility module, accelerated Newport driver
and bundled `819c682` emulator retain their qualified pins.

The separately required IRIS upstream integration is pushed on `xiri` at
`2dc6fa9132233d3aa9fd96bdaa1c5c556675cf6b`, through upstream `74e26554`.
The [integration ledger](2026-11-13-clipboard-upstream.json) records the
15-commit merge, serial-constructor adaptation, 5,530 feature-enabled
workspace library passes, 4,843 default library passes and both CLI builds.
NetBSD source is unchanged in this cycle.

Completed private disks, media and build output are removed after their
evidence is saved. Logs, source fixtures, results, screenshots and the current
manual image/state remain available; see the
[cleanup ledger](2026-11-13-clipboard-cleanup.json).

Cleanup removed 3.34 GiB of file allocations.
Shared reflink blocks mean this is not a physical-space savings measurement.
The filesystem has 467.0 GiB available. All owned test IRIS instances
are stopped; the selected manual image and saved emulator state are retained.
