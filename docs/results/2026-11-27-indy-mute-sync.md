# Native mixer changes in the IRIX Audio Panel

On the emulated Indy, an open SGI Audio Panel now follows
`mixerctl -w outputs.master.mute=on` and `off`. This fixes the case where
the panel opened with Mute checked, a native command cleared it, and the
next click did nothing. The test used the original panels and players from
6.5.22f and 6.5.30f, each in its own `xiritest` xdm session.

| IRIX release | Indy CPU | Player PID across all seven observations | Left and right peaks after the final panel click | Panel after native off and native on |
| --- | --- | ---: | --- | --- |
| 6.5.22f | R4400 | 1483 | 4016 / 8031 | [Framebuffer crops](2026-11-27-indy-mute-sync-6.5.22f.png) |
| 6.5.30f | R5000 | 1973 | 4016 / 8031 | [Framebuffer crops](2026-11-27-indy-mute-sync-6.5.30f.png) |

The test started muted at 64,128. A native unmute restored the 440 Hz left
channel and 730 Hz right channel. Clicking Mute silenced both channels.
The test then used native writes to clear, set and repeat mute. The final
panel click restored stereo playback. Every muted recording contained
digital zero in both channels. The checkbox center contained 38 red pixels
when checked and zero when clear. The two pictures for each release show
the same open panel after native writes, with unmuted on the left.

Prismatic plays its own shutter sound when F4 captures a framebuffer.
The test recorded each settled PCM interval before pressing F4. The player
ran continuously within each release's seven observations.
[Measurements and build hashes](2026-11-27-indy-mute-sync.json) ·
[Repeat the checks](../../lab/irix-hdsp/playback/README.md#check-native-mixer-changes-with-audio-panel-open).

## Kernel and images

Both native and IRIX mixer writes reach `haltwo_set_port()`. After the HAL2
driver writes a changed mute setting, it now calls a NetBSD module hook.
The loaded IRIX personality places the new value in each interested HDSP
event queue. A repeated write of the same value leaves the queue alone.
The old IRIX-only write notification has been removed so a panel click
delivers the change once. [NetBSD source change](https://github.com/salvogendut/NetBSD-xiri/commit/888d4c1fb86).

After logout to xdm, the normal desktop securelevel prevented a module
unload. A one-time boot check on each disposable guest exercised the
module at securelevel 0 during normal startup. It unloaded the module,
set and cleared mute through the native mixer, checked both readbacks
and reloaded the module. Both guests subsequently ran the IRIX shell,
reached the graphical greeter and powered off.

The tests booted the matched kernel, PROM boot file and module from
private copies of the audio-v7 base images. The retained local test CD is
`.work/builds/indy-mute-sync-20261127/boot.iso`. It contains the three
native boot files. The published audio-v7 installers and CHDs still have
the earlier driver. The [audio-v8 installers, updates and CHDs](2026-11-27-indy-audio-v8.md) include the tested boot set.
