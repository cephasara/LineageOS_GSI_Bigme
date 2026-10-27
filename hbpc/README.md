# LineageOS 23.2 GSI for the Bigme HiBreak Pro Color

A patch set and build driver that turn the LineageOS 23.2 (Android 16 QPR2) generic
system image into a system image for the **Bigme HiBreak Pro Color** E-Ink phone.
It replaces only `system`; the phone keeps its stock kernel, vendor and boot
partitions (stock Android 12 vendor, VNDK 31).

**Only the HiBreak Pro Color is supported.** The image is not meant for the
monochrome HiBreak Pro, other Bigme devices or other phones.

The patches build on [MisterZtr/LineageOS_gsi](https://github.com/MisterZtr/LineageOS_gsi)
and the TrebleDroid GSI work. Everything under `hbpc/` is specific to this phone.

This project was written almost entirely with LLM assistance and is not
independently reviewed. Flashing a custom system image can lose your data or leave
the phone unbootable. **Use it at your own risk.**

## Features

| Area | What it does | Feature ids | Details |
| --- | --- | --- | --- |
| Device baseline | E-Ink waveform key, XRZ composer properties, forced GPU composition, touch and pen orientation, frontlight, the E-Ink settings app, shortcut panel and daemon | `hibreak-baseline` | [EINK-DISPLAY.md](EINK-DISPLAY.md), [PATCHES.md](PATCHES.md) |
| E-Ink display | Hyper dithering and refresh rate, no ColorFade on sleep/wake, WebView without smooth scrolling, damage for removed or moved layers, touch-driven scroll mode, keyboard waveform | `eink-no-color-fade`, `eink-webview-flags`, `eink-composition-damage`, `eink-touch-scroll`, `eink-ime-layer-flag` | [EINK-DISPLAY.md](EINK-DISPLAY.md) |
| Ghost cleaning | Per-app clean interval after user input, one-shot GC16 full clear from the key and tile | `xrz-anti-ghosting`, `eink-gc16-clear` | [EINK-CLEAN.md](EINK-CLEAN.md) |
| Sleep screen | A picture, clock, lock screen or custom image stays on the panel while the screen is off | `eink-sleep-screen` | [SLEEP-SCREEN.md](SLEEP-SCREEN.md) |
| Hardware keys | The two case keys no longer leak F1/F2 into apps; Page Up/Down actions | `hardware-keys` | [HARDWARE-KEYS.md](HARDWARE-KEYS.md) |
| Black and white UI | Monochrome theme, opaque white surfaces, outlined containers and windows, flat Launcher | `eink-theme`, `opaque-colors`, `outlined-containers`, `flat-launcher` | [OPAQUE-UI.md](OPAQUE-UI.md), [APP-ADAPTATION.md](APP-ADAPTATION.md) |
| Navigation and system UI | Opaque three-button bar, readable disabled text, outlined volume panel | `opaque-navigation`, `disabled-text`, `volume-outline` | [UI-FOLLOWUPS.md](UI-FOLLOWUPS.md) |
| Fewer refreshes | Quiet resource defaults; animations-off leaks closed in View, widgets and SystemUI | `quiet-eink-ui`, `animations-off` | [QUIET-UI.md](QUIET-UI.md) |
| Static gestures | Home, Overview and Back gestures without motion | `static-system-gestures` | [STATIC-GESTURES.md](STATIC-GESTURES.md) |
| Launcher | Page swipes complete on release, static white app drawer, Overview close action and outlines, themed icon contours and colours, themed icons on by default (also in the drawer) | `launcher-swipe-on-release`, `static-launcher-drawer`, `overview-close`, `overview-paper`, `themed-icon-outline`, `themed-icon-colors`, `themed-icons-default` | [LAUNCHER-SWIPE.md](LAUNCHER-SWIPE.md), [LAUNCHER-DRAWER.md](LAUNCHER-DRAWER.md), [UI-FOLLOWUPS.md](UI-FOLLOWUPS.md), [THEMED-ICON-COLORS.md](THEMED-ICON-COLORS.md) |
| Lock screen and Quick Settings | Static black/white lock screen and PIN, outlined Quick Settings tiles, brightness slider hidden by default | `static-eink-keyguard`, `static-quick-settings`, `qs-brightness-hidden` | [LOCKSCREEN.md](LOCKSCREEN.md), [OVERVIEW-TILES-SLEEP.md](OVERVIEW-TILES-SLEEP.md) |
| Apps | Paper-and-ink Clock, Dialer, Contacts, Messaging, Files and Camera | `clock-widget`, `clock-light`, `eink-dialer-incall`, `eink-dialer-main`, `eink-contacts`, `eink-messaging`, `eink-documentsui`, `eink-aperture` | [UI-FOLLOWUPS.md](UI-FOLLOWUPS.md), [DIALER.md](DIALER.md), [CONTACTS.md](CONTACTS.md), [MESSAGING.md](MESSAGING.md), [DOCUMENTSUI.md](DOCUMENTSUI.md), [APERTURE.md](APERTURE.md) |
| Mobile network | Radio power cycle for a SIM stuck out of service; optional one-shot registration refresh (off by default) | `wwan-oos-radio-recovery`, `wwan-service-reconnect-refresh` | [OOS-RECOVERY.md](OOS-RECOVERY.md), [NRM-RECONNECT.md](NRM-RECONNECT.md) |
| Compatibility | SELinux ioctl rules kept on this 4.19 kernel, TrebleApp doze toggle, native `adb root` on userdebug | `selinux-xperms`, `doze-suspend-toggle`, `native-adb-root` | [SELINUX-XPERMS.md](SELINUX-XPERMS.md), [PATCHES.md](PATCHES.md), [ADB-ROOT.md](ADB-ROOT.md) |
| Packaging | Only EXT4 products; helpers for other vendors' hardware are not installed | `ext4-only-products`, `hibreak-only-packages` | [PATCHES.md](PATCHES.md), [UPSTREAM-DELTA.md](UPSTREAM-DELTA.md) |

[PATCHES.md](PATCHES.md) indexes every patch by category, and
[`patches/hibreak/series.json`](patches/hibreak/series.json) gives the order the
patches are applied in. Changes to upstream files outside `hbpc/` are listed in
[UPSTREAM-DELTA.md](UPSTREAM-DELTA.md).

## Download

Release images are on SourceForge:
<https://sourceforge.net/projects/lineageos-hibreakpro-color/>

Each release has two EXT4 images from the same source: GApps
(`LineageOS-23.2-<date>-HBPC-GAPPS-EXT4-GSI.img.xz`, with MindTheGapps) and Vanilla
(`...-HBPC-VANILLA-EXT4-GSI.img.xz`, without Google apps). Each has an
`.img.xz.sha256` file, and the release README lists the changes. Check the download,
then decompress it (use the `VANILLA` names for the vanilla image):

```sh
sha256sum --check LineageOS-23.2-<date>-HBPC-GAPPS-EXT4-GSI.img.xz.sha256
xz -dk LineageOS-23.2-<date>-HBPC-GAPPS-EXT4-GSI.img.xz
```

Flash the decompressed `.img`, never the `.xz` file. It needs about 3 GiB of free space.

## Install

You need a PC with the Android platform tools (`adb`, `fastboot`). Back up anything
you want to keep first: unlocking the bootloader and the first install both erase
the phone.

1. **Unlock the bootloader.** This is required and wipes the phone. The community
   guides below describe the procedure for the HiBreak Pro.
2. **Make a backup** of the stock partitions if you may ever want to return to the
   stock system (see Guide 3 below).
3. **Verified boot: check before you flash.** `vbmeta`, `vbmeta_system` and `vbmeta_vendor`
   decide whether a foreign `system` is verified at boot, so this is a step to check and not
   one to perform blindly. Guide 4 below shows the usual `fastboot flash vbmeta...
   --disable-verity --disable-verification` commands. On our phone all three already had
   verification disabled, so nothing was written and the image booted anyway.

   ```sh
   # vbmeta_a, vbmeta_system_a and vbmeta_vendor_a are physical partitions: only the
   # bootloader's own fastboot writes them, and that is the mode where `is-userspace`
   # says `no`. Step 4's `system` needs the other mode, so these three writes come last
   # in a session: one that dies halfway must not leave a `vbmeta` hashing images the
   # phone no longer has.
   fastboot getvar is-userspace      # no: the bootloader's fastboot, not fastbootd
   fastboot flash vbmeta_system_a vbmeta_system.img --disable-verity --disable-verification
   fastboot flash vbmeta_vendor_a vbmeta_vendor.img --disable-verity --disable-verification
   fastboot flash vbmeta_a        vbmeta.img        --disable-verity --disable-verification
   ```

   Four things to know before you spend those flashes on the Pro Color:

   - The two flags make `fastboot` parse the file before it writes it. When the file is
     not a vbmeta image it refuses with `Failed to find AVB_MAGIC at offset: 0` and
     writes nothing at all; without the flags the same command writes the file whatever
     it holds, so a bad extract becomes a broken verified-boot chain instead of an error.
     A vbmeta image starts with `AVB0`, so check: `head -c 4 vbmeta.img | xxd | head -1`
     must print `4156 4230`. These are 8 KiB and 4 KiB partitions on this phone, so a
     megabyte-sized "vbmeta" is not one.
   - The images must come from your own model and version. `vbmeta_a` is the top of the
     chain and holds the hashes of everything under it, so another model's file describes
     another phone's `boot`, `dtbo` and `vendor`. Keep your own copy: a rollback to the
     stock system needs the chain back the way Bigme wrote it.
   - `fastboot fetch` is not implemented on this phone; it answers `Unable to get
     max-fetch-size. Device does not support fetch command.` So the images come from your
     own firmware package, or off the running phone with root
     (`dd if=/dev/block/by-name/vbmeta_a of=/sdcard/vbmeta_a.img`, then `adb pull`).
     `avbtool info_image --image vbmeta_a.img | grep -i flags` then prints the flag field
     of the struct: `Flags: 3` means both bits are already off and there is nothing to
     flash.
   - `ro.boot.vbmeta.device_state`, `ro.boot.verifiedbootstate` and `ro.boot.veritymode`
     are not measurements on this image. The `securize` block of `phh-on-boot.sh` in
     `device/phh/treble`
     ([patch 0003](../patches/personal/device_phh_treble/0003-securize-rework-to-property-based-toggle-with-GSI-fi.patch))
     rewrites them to `locked`, `green` and `enforcing` after boot completes, whatever the
     partitions hold; it is guarded by the absence of `/metadata/securize_disable`, and
     `setprop persist.sys.phh.securize 0` (as root, through the `vndk.rc` trigger in
     `phh-prop-handler.sh`) writes that file and stops the rewrite, so the next boot
     reports the truth. `fastboot getvar unlocked` and `getvar secure` are the
     bootloader's own answer and need none of this. A `locked`/`enforcing` reading on a
     GSI says what the image wants Play Integrity to think; it is not a reason to flash.
4. **Reboot to fastbootd** (userspace fastboot) with `adb reboot fastboot`. Then
   `fastboot getvar is-userspace` must print `yes`. `system` is a logical
   partition, so the bootloader's own fastboot mode cannot flash it.
5. **Flash the image:**

   ```sh
   fastboot flash system LineageOS-23.2-<date>-HBPC-GAPPS-EXT4-GSI.img
   ```

   fastbootd resizes the logical `system` partition to fit the image. The phone uses
   virtual A/B; flashing the current slot (slot `a` on our phone) works.
6. **First install only:** wipe data with `fastboot -w`. A wipe is required when
   you come from the stock system or another ROM.
7. Run `fastboot reboot`.

**Updating.** To update from an earlier build of this GSI, repeat steps 4, 5 and 7
without the wipe. Your data, apps and settings are kept. A Magisk-patched `boot`
is not touched by flashing `system`, so Magisk keeps working.

**Rollback.** Keep the previous image. Flash it the same way to go back. Flashing
an older build over newer data has not been tested; wipe if it does not boot. To
return to the stock system, restore your stock `system` (or the full stock
firmware) from your backup and wipe data.

**Stock firmware.** [BIGME-OTA.md](BIGME-OTA.md) describes Bigme's official firmware
(OTA) and system-app update servers, with [`bigme-ota.py`](bigme-ota.py) to query
them and the official downloads seen so far. Those packages are for the stock
system; they cannot be installed over this GSI.

### Community guides (written for the HiBreak Pro)

These guides by vbh.ai cover the monochrome **HiBreak Pro**, not the Pro Color. They
are useful background, but their images, firmware and post-install tweaks are not
for the Pro Color. Blog index: <https://vbh.ai/blog/>

- [Guide 1: debloating and Private DNS](https://vbh.ai/hibreak-pro-guide-1-debloating-the-hibreak-pro-and-setting-up-private-dns/):
  removes vendor apps from the *stock* system over ADB and sets up a Private DNS
  provider. It is not needed with this GSI, which does not include the vendor apps.
  Private DNS is in Android's network settings.
- [Guide 2: bootloader unlock and root](https://vbh.ai/unlocking-the-bootloader-and-rooting-the-hibreak-pro/):
  unlocks the bootloader with fastboot and roots by patching `boot` with Magisk. The
  general steps match this phone. We have not checked each command or the
  pre-patched boot image on the Pro Color: use only your own phone's `boot`.
- [Guide 3: firmware upgrade and backup](https://vbh.ai/hibreak-pro-guide3-an-extremely-rubbish-way-to-upgrade-your-hibreak-pro-to-the-latest-firmware/):
  backs up partitions and flashes an extracted OTA with mtkclient. The backup part
  applies here. Never flash HiBreak Pro firmware on a Pro Color.
- [Guide 4: flashing the Android 15 GSI](https://vbh.ai/hibreak-pro-guide-4-flashing-the-android-15-gsi/):
  vbmeta, fastbootd, wipe and flash steps for a TrebleDroid GSI. Steps 3 to 7 above
  follow the same pattern. Its post-install tweaks (disabling hardware overlays,
  global refresh mode, backlight nodes) are not needed: this GSI handles
  composition, refresh modes and the frontlight itself.
- [HiBreak Pro Android 14 GSI release](https://vbh.ai/hibreak-pro-gsi-release/):
  an Android 14 GSI for the HiBreak Pro, built on another Treble ROM, with a ported
  E-Ink accessibility service. It is not for the Pro Color.
- [Reddit: more hacks for the HiBreak Pro](https://www.reddit.com/r/Bigme/comments/1jvij9x/guide_more_hacks_for_the_hibreak_pro_fix_android/):
  stock-framework tricks (per-app DPI, global E-Ink refresh mode codes). Background on
  the XRZ display properties only. This GSI has its own E-Ink settings.

## Known limits

- HiBreak Pro Color only, on its stock Android 12 vendor (VNDK 31). Other vendor
  versions are not tested.
- Both EXT4 variants are released. The GApps variant is the one used on the phone.
  The Vanilla image is built and passes the same packaged-image checks, but has not
  been tested on the phone. Switching variants over existing data is not tested;
  wipe data when you change the variant.
- The panel always uses GPU (client) composition, as the stock system does. The vendor
  composer's device-composition path is not used.
- Android's always-on display is not supported. The E-Ink sleep screen takes its place.
- The mobile-network workarounds address MediaTek modem states seen on this phone.
  The registration refresh is an opt-in experiment.
- App restyling covers the apps listed above. Other apps keep their own colours and
  animations.
- `--debug-adb` images accept ADB from any USB host without authorization. Build
  them only for diagnostics, and never use one as your daily image.

## Building from source

Build on Linux with the usual Android build dependencies, `repo`, Git LFS,
Python 3, OpenSSL, e2fsprogs and JDK 17 (for the TrebleApp Gradle build). On NixOS,
use an Android-compatible FHS environment. The platform compilers and JDKs come from
the source checkout. The SDK and Gradle dependencies download on the first TrebleApp
build and can be cached.

```sh
git clone -b lineage-23.2 https://github.com/dianqk/LineageOS_gsi_HBPC.git LineageOS_gsi
mkdir lineage-23.2
cd lineage-23.2
repo init -u https://github.com/LineageOS/android.git -b lineage-23.2 --depth=1 --git-lfs --no-clone-bundle
mkdir -p .repo/local_manifests
cp /path/to/LineageOS_gsi/hbpc/manifest-snapshot.xml .repo/local_manifests/hibreak.xml
repo sync -c --optimized-fetch --no-clone-bundle --no-tags -j8
python3 /path/to/LineageOS_gsi/hbpc/build-hibreak.py build \
  --tree . --variant gapps --out-dir out \
  --keys /path/to/signing-keys \
  --eink-key /path/to/eink_key \
  --treble-java-home /path/to/jdk17 \
  --ccache-dir /path/to/ccache \
  --gradle-user-home /path/to/gradle-cache \
  --android-sdk-root /path/to/android-sdk \
  --dist /path/to/output -j16
```

The driver applies the TrebleDroid, TrebleDroid staging and personal patches in
order, then the HiBreak series, builds `systemimage` and checks the packaged image.
Any failure stops the build. Use `--variant vanilla` for the build without Google
apps; both variants are EXT4. `check` runs only the Soong graph (`nothing` target)
and `apply` only applies the patches.

**Inputs you supply.** These files are not in this repository:

- Signing keys: unencrypted `.pk8`/`.x509.pem` pairs for releasekey, platform,
  shared, media, networkstack, bluetooth, nfc and sdk_sandbox, with mode 0600 on the
  private keys. Keep the same keys for every build, so that updates install over
  existing data.
- The factory E-Ink waveform key, found on the phone at `/system/eink_key` (stock
  firmware or this GSI). It is proprietary and not redistributed here. Extract it
  from your own phone, e.g. `adb pull /system/eink_key`, and pass it with
  `--eink-key`. Its SHA-256 must be
  `69804441c70e866d81e0a80dfb762a993076c1325e41aee1d604925c20f977a1`. The build
  copies it to `device/phh/treble/bigme-display/eink_key` in the source tree
  (ignored by Git), and later builds reuse it.

Google apps keep their original signatures. TrebleApp is built from source and
signed with the platform key.

**Manifests.** Copy one of them to `.repo/local_manifests/hibreak.xml`:

- `manifest-snapshot.xml` (recommended) pins every project, including the extra
  TrebleDroid, GApps and HiBreak projects, to the commits these patches were last
  rebased and built on. Its header names the LineageOS manifest commit it came from.
  If the `lineage-23.2` manifest has since added or removed projects, initialise
  `repo` at that commit with `repo init ... -b <commit>`.
- `manifest.xml` adds the extra projects and pins only the patched projects. All
  other projects follow the current `lineage-23.2` heads. Use it to move to newer
  sources, then rebase the patches that fail.

Before you sync a tree that already has the patches applied, reset the patched
projects (`repo sync -l -d <projects>`) and delete
`.repo/lineage-gsi-upstream-applied.json`, so that the builder applies everything
again. To regenerate the snapshot after a pin update, run `repo manifest -r` on the
synced, unpatched tree. Peel each project's revision to a commit
(`git rev-parse m/lineage-23.2^{commit}`); AOSP projects otherwise resolve to
annotated tags.

**Output.** Images keep the upstream naming,
`LineageOS-23.2-YYYYMMDD-GAPPS-EXT4-GSI.img`, in a directory named after the build
number `HBPC.23.2.P1.<UTC date>.<UTC time>.g<commit>`, next to build info, SHA-256
and the resolved manifest. Only an image that passes the packaged-image checks
updates `latest.img`. The build never touches a connected phone.

**Debug ADB.** Normal images use Android's authorised, opt-in ADB. `--debug-adb`
adds the [debug series](patches/debug-adb/series.json), which accepts any USB host
and allows `adb root`. Such builds get `.debug-adb` in the build number and
`-DEBUG-ADB` in the file name. Building without the flag removes these changes
again, and the checks confirm they are absent. No TCP listener is enabled in either
case.

## Credits

- [LineageOS](https://lineageos.org/) and the Android Open Source Project.
- [TrebleDroid](https://github.com/TrebleDroid) and Pierre-Hugues Husson (phh):
  `device_phh_treble`, TrebleApp and the GSI patch series.
- [MisterZtr/LineageOS_gsi](https://github.com/MisterZtr/LineageOS_gsi): the
  LineageOS GSI patch set and build approach this repository forks, and the
  contributors credited in its README.
- [damianmqr](https://github.com/damianmqr): the original E-Ink accessibility service
  and patcher for the Hisense A9 (`a9_accessibility_service`, `A9PatchingService`).
- [vbbot/HibreakProPatchingService](https://github.com/vbbot/HibreakProPatchingService):
  the HiBreak Pro port of that service, used here as `vendor/a9_services`. vbh.ai wrote
  the HiBreak Pro guides above.
- [MindTheGapps](https://gitlab.com/MindTheGapps) for the GApps variant.

## License

Files under `hbpc/` are licensed under the [Apache License 2.0](LICENSE), unless a
file says otherwise. Patches keep their authors and the licenses of the projects
they modify. The upstream patches outside `hbpc/` come from MisterZtr/LineageOS_gsi
and its sources under their own terms. `vendor/a9_services` is MIT-licensed, with
one AOSP-derived Apache-2.0 file. Our patches to it
(`patches/hibreak/vendor_a9_services/` and `patches/hibreak/device/vendor_a9_services/`)
are MIT-licensed too. See [NOTICE](NOTICE) for details and the full notices.
