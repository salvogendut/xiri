# Install XiriBSD on an Indy in Prismatic

This installs NetBSD and the Xiri compatibility module on a fresh virtual disk.
Your first login opens the native NetBSD **ctwm** desktop. The IRIX desktop
requires a separate donor import. The installer ISO for this build is
`.work/images/xiribsd-indy-xiriprep-11.99.11.iso` in the Xiri checkout.
If you already installed `xiribsd-indy-native-11.99.11.iso`, keep that disk
and go straight to the [tools CD instructions](XIRIPREP.md#use-the-tools-cd-on-an-existing-indy).

## 1. Attach the disk and CD

Start Prismatic. While paused, open **F9 → General** and select **Indy**,
**R4400** or **R5000**, and **256 MiB** of RAM. Use the default **Newport** graphics.
Set **PROM boot** to **Keep existing** and use the **Graphics** console to
follow the installation in the Prismatic window.

| In **F9 → Media** | What to attach |
| --- | --- |
| **SCSI ID 1 → New disk…** | Choose **Raw**, enter **6144 MiB**, give it a new filename such as `xiribsd-indy.raw`, then select **Create disk and attach to draft**. The installer will format this disk. |
| **SCSI ID 6 → CD-ROM** | Select `xiribsd-indy-xiriprep-11.99.11.iso`. |

## 2. Boot the CD

Save with **F9** and start the Indy with **Ctrl+P**. Click the guest display,
press **Esc** during startup and choose **5 — Enter Command Monitor**.
If the blank disk gives an “Unable to boot” message first, press **Enter**
to reach the menu. At the Indy’s `>>` prompt, enter

```text
boot -f scsi(0)cdrom(6)rdisk(0)partition(8)ip2xboot
```

The `6` in `cdrom(6)` is Prismatic’s usual CD-ROM slot. If you attached
the ISO at ID 4, as in the automated tests, use `cdrom(4)` instead.

The CD installer uses Newport’s black-to-green gradient. On the first boot
from disk, the installed kernel should draw the SGI-style frame around the
boot messages on the 1280×1024 graphics console, before xdm starts.
The frame is built into the kernel and works before any IRIX donor import.

## 3. Install NetBSD

1. In **sysinst**, choose **Install NetBSD to hard disk**. Confirm that
   `sd0` is the new **6 GiB** disk, then accept the default partition sizes.
2. Choose **Full installation** and **CD-ROM / DVD**. If asked for the set
   directory, use `sgimips/binary/sets`. Wait for all **15 sets** to unpack.
3. Set the root password. In the configuration menu, set **Enable xdm
   (X Display Manager)** to **YES** and create your regular login account.
4. Select **Finished configuring**, then **Exit Install System**. At the
   installer’s `#` prompt, type `halt` and wait for the disk to unmount.

## 4. Boot from disk and log in

In **F9 → Media**, disconnect the CD at **ID 6** and leave the disk at **ID 1**.
For future starts, select **F9 → General → PROM boot → NetBSD**, save, and
start the Indy. If the PROM menu appears, choose **Start System**.

For a manual disk boot, enter these commands at the Indy’s `>>` prompt.

```text
setenv OSLoader boot
setenv OSLoadFilename netbsd.boot
setenv OSLoadOptions auto
boot
```

The first boot builds the font cache. When **xdm** appears, log in with the
account you created. You should see a **1280×1024 ctwm desktop** with a terminal.
[Screenshot of the installed desktop](results/2026-11-27-native-indy-ctwm.png)

The installed system includes `xiriprep`. Run it as root with your donor
image and the login you want to use for 4Dwm.
[Import a CHD from CD or a raw image from disk](XIRIPREP.md#read-a-donor-from-external-media)
