# What Showcase requests from the Indy graphics device

IRIS Showcase 3.4 opened a new document on the original-media IRIX 6.5.22f Indy with Xsgi and Newport graphics. On the matching Xiri Indy it exits during IRIS GL startup with `ERR_NOGRAPHICS`. [Original IRIX screenshot](2026-11-25-showcase-native.png) · [Xiri double-click and direct-launch observations](2026-11-25-applications-recheck.md).

On a disposable donor copy, we logged in at the graphical console and traced `/usr/sbin/showcase -nofork` with SGI's `par -s -i -SS -t 28 /usr/sbin/showcase -nofork`. The main window measured 672×880. The calls below came from the same Showcase process. [Original par output for the graphics fd](2026-11-25-showcase-par.txt).

| Stage | Original IRIX observation |
| --- | --- |
| Open | `open("/dev/graphics", O_RDWR\|O_NOCTTY)` returned fd 8. The device had character major 57, minor 0. |
| Discover the board | `GFX_GETNUM_BOARDS` and `GFX_GETBOARDINFO` both succeeded on fd 8. |
| Attach the board | `GFX_ATTACH_BOARD` succeeded on the same fd. |
| Set up rendering | `RRM_OPENRN`, `RRM_BINDRNTOCLIP`, `RRM_MESSAGE`, `RRM_BINDPROCTORN` and `RRM_SETDISPLAYMODE` succeeded. The Master Gizmo process also used rendering requests. |

The first comparison to implement on Xiri is an IRIX board-count and board-information query against the guest's actual graphics hardware. The native trace gives a second, separate acceptance test for attaching the board and setting up a rendering context. Publishing a device node alone would still leave those operations outstanding. SGI Clock exercises Xorg GLX through a different library. [GLX qualification](2026-11-24-indy-glx.md).
