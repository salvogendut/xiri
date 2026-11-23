# Framed boot console on Octane IMPACT

The Octane now shows NetBSD kernel and service startup messages in the same blue frame as the Indy and Indigo2. The frame appears when NetBSD attaches its HQ4 console, after SCSI autoconfiguration. At handoff it replays earlier kernel messages, then displays new output as it arrives. The PROM and initial loader still use IOC3 serial A. Xorg takes the full 1280×1024 display at xdm.

## Try it

Run one launcher from the Xiri checkout. These are fresh disks built from the preceding Octane base images. Each launcher keeps its own writable overlay. Manual changes made in an older bundle are available by launching that bundle.

| IRIX desktop | Octane graphics | Launch command | Cold boot |
| --- | --- | --- | --- |
| 6.5.22 | Solid IMPACT | `./.work/native/xiri-ip30-frame-6.5.22-20261123/run-iris.sh` | [Boot screenshot](2026-11-23-octane-frame-6.5.22.png) |
| 6.5.30 | High IMPACT | `./.work/native/xiri-ip30-frame-6.5.30-20261123/run-iris.sh` | [Boot screenshot](2026-11-23-octane-frame-6.5.30.png) |

At xdm, log in as `xiritest` with password `xiritest` for 4Dwm, or `netbsdtest` with password `netbsdtest` for ctwm. The launchers use the same R10000 JIT as the previous images. [Desktop login, serial access and shutdown](2026-11-23-octane-xdm.md)

## Driver and verification

The NetBSD `XIRI_IP30_DESKTOP` kernel enables `IMPACT_FRAME` in the HQ4 framebuffer driver. It uses the existing Newport palette and rectangles, clips the 1282-pixel artwork to the 1280-pixel display, and centers 88 columns by 42 rows of 8×16 text in the inset panel. The driver draws in the existing RAM framebuffer. Its normal update thread transfers changes to IMPACT. That thread starts at console attachment and needs the scheduler to run. [NetBSD driver change](https://github.com/salvogendut/NetBSD-xiri/commit/0e208f614c3)

Both standalone CHDs passed raw and overall CHD verification. On a cold SCSI boot of each release, the test read `root on sd0a` and `Starting root file system check` directly from the graphical display. All 837,632 pixels outside the text panel matched the original artwork. The xdm checks exercised 4Dwm and ctwm logins, full-screen Xorg, logout to the greeter and a clean halt.

On both boards a separate Xorg test checked keyboard and mouse input, stopped Xorg and read fresh shell output from the restored frame. After a newline at the bottom of the panel, the marked second row moved to the first row pixel for pixel. The border matched the reference before and after scrolling. The plain framebuffer configuration also compiled. Runtime checks used emulated boards. [Results and SHA-256 hashes](2026-11-23-octane-frame.json)

## Reproduce

Build `XIRI_IP30_DESKTOP` and its module from the NetBSD fork, then use the Octane disk packaging procedure with the previous base CHD for the corresponding release. Add `--frame-netbsd ../NetBSD-xiri` to the `disk.py qualify` invocation to check the decorated cold boot. The retained kernel and module from this build are in `.work/octane-frame/qualified/`. [Disk build and test commands](2026-11-23-octane-xdm.md#reproduce-a-release)

To repeat the separate Xorg exit and scrolling test on High IMPACT, run this from the Xiri checkout with a fresh output directory. For Solid IMPACT, select `solidimpact` and the 6.5.22 disk.

```sh
python3 lab/ip30-impact/check.py --board highimpact --xorg --check-frame \
  --emulator .work/emulators/iris-ip30-jit-08e53ba7 \
  --kernel .work/octane-frame/qualified/netbsd \
  --disk .work/native/xiri-ip30-frame-6.5.30-20261123/netbsd-xiri.chd \
  --firmware .work/octane-m4a-phys-readonly-20261116 \
  --output .work/ip30-frame-recheck-6.5.30
```

IRIS upstream was checked at `a05289ef`, already integrated in the fork's `xiri` at `08e53ba7`. Both boards used that JIT build.
