# VoLTE with the MediaTek IMS service

Feature id `mtk-volte`. Patches:
[preinstalled IMS service](patches/hibreak/device/device_phh_treble/0001-preinstall-patched-mediatek-ims.patch)
(`device`) and [VoLTE defaults](patches/hibreak/defaults/device_phh_treble/0016-make-volte-available.patch)
(`defaults`). The APK change is [`mtk-ims/ims-mt-ecpi.patch`](mtk-ims/ims-mt-ecpi.patch).

## What it does

- The image contains TrebleDroid's MediaTek IMS service (`com.mediatek.ims`, the
  `ims-mtk-u` APK that TrebleApp otherwise offers to download) as the privileged system
  app `/system/priv-app/HbpcMtkIms`, signed with the platform key of the build. The app
  joins Android's phone user (`android.uid.phone`), which only a preinstalled,
  platform-signed copy may do. It is direct-boot aware: in testing, IMS registered
  before the first unlock after a reboot; an incoming call before the first unlock has
  not been tested.
- The APK is patched so that **incoming** VoLTE calls ring. The GSI's `rw-system.sh`
  changes the vendor RIL so that the modem no longer asks for approval of an incoming
  call (`AT+EAIC=3`). The modem then reports the call only as call progress
  (`+ECPI ...,0`), which the unmodified service ignores. The patched service creates the
  incoming call session from that report. Outgoing calls are unchanged.
- `persist.dbg.volte_avail_ovr=1`: VoLTE ("4G Calling") is available on every SIM,
  whatever the carrier configuration says. `persist.dbg.allow_ims_off=1`: turning
  4G Calling off really turns IMS off. Both are build defaults for all regions.
- Wi-Fi Calling is not forced (`persist.dbg.wfc_avail_ovr` is not set).

## Build

`build-hibreak.py` prepares the APK before the Android build:

1. It downloads `https://treble.phh.me/ims-mtk-u-resigned.apk` and apktool 3.0.3 (from
   its GitHub release) into the download cache (`--download-cache`, default
   `<tree>/.repo/hibreak-downloads`) and checks both against the SHA-256 values in
   [`mtk-ims/source.json`](mtk-ims/source.json). A failed download or a different
   file stops the build. Later builds use the cache and work offline.
2. It decodes the APK's code (`apktool d -r`, with the source tree's JDK 21), applies
   `ims-mt-ecpi.patch` and rebuilds `classes.dex`. The result must match the pinned
   SHA-256.
3. It copies the original APK with only `classes.dex` replaced and the old signature
   removed to `device/phh/treble/bigme-ims/HbpcMtkIms.apk` (ignored by Git). The
   Android build signs it with the platform key.

The MediaTek APK and every file derived from it stay in the cache and the source tree;
this repository holds only the patch and the pinned hashes. `verify-hibreak.py` checks
the packaged APK (patched `classes.dex`, platform signature, manifest), the privileged
permission allowlist and the properties.

## Diagnostics

The patched service logs to the radio log (`adb logcat -b radio`, tag `ImsService`):
`hbpc: MT ECPI listener registered` once per SIM slot at start,
`hbpc: call info, ...` for each call progress report (phone id, call id, message type
and call mode; no phone number) and `hbpcOnMtEcpi() : ...` when it creates or skips an
incoming call session.

## Turning it off

- In Settings > Network & internet > SIMs, switch **4G Calling** (VoLTE) off. Calls then
  use 2G/3G where the network still offers it.
- To make VoLTE follow the carrier configuration again:
  `adb shell setprop persist.dbg.volte_avail_ovr 0` (as root on a userdebug build), then
  reboot. A value stored this way, or by TrebleApp's "Force the presence of 4G Calling
  setting" switch, overrides the build default until data is wiped. Note that switching
  that TrebleApp option on also forces Wi-Fi Calling.
- To remove the IMS service, build without the two `mtk-volte` patches.

## Limits

- Incoming VoLTE calls depend on the patched service. The modem accepts an incoming call
  on its own, so the service cannot reject it early (for example a call that arrives
  during an emergency call, or a second call while call waiting is off); the call is
  shown and can be answered or declined as usual.
- The vendor RIL does not track these incoming VoLTE calls (it logs
  `Can't find callId`); answering and ending them go through the IMS service.
- The real-time text (RTT) mode of an incoming call is not set.
- Do not use TrebleApp's "Download and install IMS APK" button. The GSI accepts the
  TrebleDroid signature, so the unpatched APK may install as an update over the
  preinstalled one (not tested), and incoming VoLTE calls would then stop ringing. To
  undo it, uninstall the updates of `com.mediatek.ims` in Settings > Apps (show system
  apps).
- If the phone ran an earlier build with the TrebleDroid IMS APK installed from
  TrebleApp, Android is expected to remove that copy (and its data) at the first boot,
  because it is signed with another key than the preinstalled one (from reading the
  package manager code; not tested).
- In testing, incoming calls were missed on 5G SA with Wi-Fi connected; [No 5G while on
  Wi-Fi](NR-OFF-ON-WIFI.md) keeps the phone on LTE while Wi-Fi is the default network.
- Only the HiBreak Pro Color's MediaTek vendor is supported. Video calls (ViLTE) and
  Wi-Fi Calling are not part of this feature.
