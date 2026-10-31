# Deviations from upstream

Upstream is [MisterZtr/LineageOS_gsi](https://github.com/MisterZtr/LineageOS_gsi)
`lineage-23.2` at `7bf212f`. Everything outside `hbpc/` comes from upstream and is
kept byte-identical, except for the entries below. When syncing a newer upstream,
replay this list.

## Added files outside `hbpc/`

| File | Reason |
| --- | --- |
| `.gitattributes` | `*.patch -whitespace`: unified-diff context lines that hold a single space are not whitespace errors. |
| `.gitignore` | Ignores `__pycache__/` from the `hbpc/` Python build and verify scripts. |
| `.github/FUNDING.yml` | GitHub sponsor button for this repository. |
| `CHANGELOG.md` | User-visible changes of the HiBreak Pro Color port per release. |

## Modified upstream files

| File | Reason |
| --- | --- |
| `README.md` | Replaced by a short landing page for this device that points to `hbpc/README.md`. Upstream's generic build instructions do not build this device's image, link the removed `README-RU.md` and describe the EROFS products that `hbpc/` removes. When syncing upstream, keep this version and review upstream's README for new credits. |

## Removed upstream files

| File | Reason |
| --- | --- |
| `README-RU.md` | Upstream Russian README; not maintained for this HiBreak Pro Color build. |

## Overridden upstream patches

`hbpc/build-hibreak.py` applies a file from `hbpc/patches/upstream-overrides/<upstream path>`
instead of the upstream file with the same path. The upstream file stays unchanged.

None. The goodix guard override was removed with the upstream patch (G9).

## Upstream products removed by an `hbpc/` patch

`patches/personal/device_phh_treble/0002-lineage-use-own-config-and-targets.patch` stays
byte-identical. It adds the EXT4 products `lineage_arm64_bgN4`/`bvN4` and the EROFS
products `lineage_arm64_bgNE`/`bvNE`. Only EXT4 images are built and tested for this
device, and the EROFS products still reference the `product.prop` that the removed
personal 0006 provided. [`defaults/device_phh_treble/0013-ext4-only-products.patch`](patches/hibreak/defaults/device_phh_treble/0013-ext4-only-products.patch)
(feature `ext4-only-products`) deletes both EROFS product makefiles and their
`AndroidProducts.mk` entries. The patch keeps the upstream patch intact (no edit, no
override), and a later upstream change to 0002 shows up as a conflict in 0013.

Patches that mention `EROFS` only as the errno ("read-only file system") are unrelated
and stay: `trebledroid-staging/platform_system_core/0004` (restorecon of a read-only
ext4 `/system/bin/init`) and `trebledroid/platform_frameworks_base/0039`. The
`external/erofs-utils` project stays in the manifests: apexer, releasetools and
update_engine use it on the host.

## Removed upstream patches

Whole upstream patch files deleted because they only serve other hardware, kernels,
VNDK versions or build types. The HiBreak Pro Color (MT6877, kernel 4.19, Android 12
vendor, VNDK 31) does not use them. G8 removes security relaxations this device does
not need; G10 removes patches whose trigger (a vendor service, input switch, fstab flag,
kernel feature, SELinux type or process) was checked to be absent on the device. Groups
are applied in order; patches in one group depend on each other and must be restored
together.

| Upstream patch | Group | Reason |
| --- | --- | --- |
| `patches/trebledroid/platform_external_selinux/0012-Fix-secilc-on-Moto-One-Action.patch` | G1 | Moto One Action secilc hack (skip vendor `ordered` CIL statements). HiBreak needs the stock behavior, so its HiBreak revert patch is removed with it; the resulting `external/selinux` tree is identical. |
| `patches/trebledroid-staging/platform_bionic/0003-bionic-tolerate-MADV_WIPEONFORK-failure-on-pre-4.14-.patch` | G2 | Pre-4.14 kernels only; MADV_WIPEONFORK exists on kernel 4.19. |
| `patches/trebledroid-staging/platform_frameworks_base/0015-voiceinteraction-disable-assistant-screenshot-on-ker.patch` | G2 | Gated on `isLegacyKernel()` (< 4.14); never true on kernel 4.19. |
| `patches/trebledroid/platform_system_core/0019-Disable-project_quota-on-old-devices-but-new-enough-.patch` | G2 | Project-ID quota is only disabled on kernels < 4.9. Needs 0015 context; removed together. |
| `patches/trebledroid/platform_system_core/0015-Disable-quotas-on-legacy-devices-with-encryption-dis.patch` | G2 | Acts only without file-based encryption; the device uses FBE (first API 31). |
| `patches/trebledroid/platform_system_core/0005-Detect-allowed-sdcard-options-based-on-vndk.patch` | G2 | sdcardfs options differ only for `ro.vndk.version` < 29; the vendor is VNDK 31. |
| `patches/trebledroid/platform_frameworks_native/0003-unshared_oob-didn-t-exist-in-O-P-so-detect-its-suppo.patch` | G2 | OBB migration probe only for `ro.vndk.version` <= 28. |
| `patches/trebledroid/platform_frameworks_native/0016-Revert-Remove-dead-code-from-LayerFE.patch` | G2 | Re-adds `LayerFE::onLayerDisplayed`/`releaseFences` that nothing calls. |
| `patches/trebledroid/platform_bionic/0001-Disable-vndklite-handling.patch` | G2 | VNDK-lite (`ro.vndk.lite`) is only used by Android 8.1/9 non-full-Treble vendors. |
| `patches/trebledroid/platform_system_linkerconfig/0001-Disable-vndklite-handling.patch` | G2 | VNDK-lite (`ro.vndk.lite`) is only used by Android 8.1/9 non-full-Treble vendors. |
| `patches/trebledroid-staging/platform_device_phh_treble/0005-Mount-tmpfs-on-metadata-for-devices-without-a-metada.patch` | G2 | Only for devices without `/metadata`; virtual A/B always has it. |
| `patches/trebledroid/platform_frameworks_opt_telephony/0002-Telephony-Don-not-call-onUssdRelease-for-Huawei-RIL.patch` | G3 | Huawei RIL only (`persist.sys.radio.huawei`). |
| `patches/trebledroid/platform_system_core/0014-healthd-offline-charger-fix-screen-off-3-3.patch` | G3 | Charger changes gated on Kirin `ro.hardware` (hi3660/hi3670/hi6250/kirin); elsewhere only extra logging. |
| `patches/trebledroid/platform_frameworks_base/0032-Detect-Moto-dynamic-hardware-feature.patch` | G3 | Motorola sysconfig tag only. |
| `patches/trebledroid/platform_system_core/0016-Add-vendor-firmware_mnt.-Moto-Razr-2019-look-for-fir.patch` | G3 | Motorola Razr 2019 `/vendor/firmware_mnt` path only. |
| `patches/trebledroid/platform_system_core/0020-fix-Nubia-6-series-custom-rc-action-prop-validation.patch` | G3 | Nubia `nubia.perf.` rc trigger prefix only. |
| `patches/trebledroid/platform_frameworks_native/0006-MIUI13-devices-hide-their-vibrator-HAL-behind-non-de.patch` | G3 | Xiaomi MIUI 13 `vibratorfeature` HAL instance only. |
| `patches/trebledroid/platform_frameworks_native/0015-Fix-touch-on-MEIZU-21-Pro-1.patch` | G3 | Meizu 21 Pro device names only. Needs 0014 context; removed together. |
| `patches/trebledroid/platform_frameworks_native/0014-Fix-touch-on-Meizu-21-Note.patch` | G3 | Meizu 21 Note device names only. |
| `patches/trebledroid/platform_frameworks_base/0024-Allow-disabling-of-fingerprint-cleanups-needed-on-so.patch` | G3 | `persist.sys.phh.fingerprint.nocleanup`, set only for Realme (RMX) devices. |
| `patches/trebledroid/platform_frameworks_base/0052-Add-support-for-treating-virtual-biometric-sensors-a.patch` | G3 | Unihertz virtual biometric sensors (`persist.sys.phh.virtual_sensors_are_real`, default off). |
| `patches/trebledroid/platform_frameworks_av/0003-Add-partial-cam-id-is-hardcoded-support-for-Asus-ZF6.patch` | G3 | Asus ZenFone 6 only (`/dev/asusMotoDrv`). |
| `patches/trebledroid-staging/platform_build/0001-Skip-mounting-my_manifest-on-GSIs.patch` | G3 | Oplus `my_*` partition skip-mount entries only. |
| `patches/personal/device_phh_treble/0010-bugfix_PIN_setup_Pixel_devices.patch` | G3 | Only excludes Pixel SoCs (gs101/gs201/zuma/...) from an existing boot block; no change on MT6877. |
| `patches/trebledroid/platform_hardware_interfaces/0003-Fix-crash-on-Samsung-S23-using-stock-properties-beca.patch` | G3 | Samsung S23 AIDL sensors converter. Needs 0002 context; removed together. |
| `patches/trebledroid/platform_hardware_interfaces/0002-Fix-light-sensor-crash-on-Xiaomi-13.patch` | G3 | Xiaomi 13 AIDL sensors converter; the Android 12 vendor serves HIDL sensors. |
| `patches/trebledroid/platform_frameworks_native/0007-powermanager-Add-support-Samsung-miscpower-HAL.patch` | G4 | Samsung miscpower HAL in libpowermanager; removed with frameworks_base 0036/0009. MTK has no `power` IPower instance, so the AOSP lookup order results. |
| `patches/trebledroid/platform_frameworks_base/0036-Once-we-integrate-Samsung-Power-hal-in-libpowermanag.patch` | G4 | Links Samsung miscpower for frameworks_native 0007; its context contains 0009. |
| `patches/trebledroid/platform_frameworks_base/0009-Support-samsung-Pie-and-Q-light-hal.patch` | G4 | Samsung Pie/Q light HAL only. |
| `patches/trebledroid/platform_frameworks_base/0044-Bunch-of-FOD-stuff-commonize-refreshing-the-services.patch` | G4 | Samsung FOD service refresh; builds on 0042/0043, nothing else calls it. |
| `patches/trebledroid/platform_frameworks_base/0043-Add-Samsung-sysinput.patch` | G4 | Samsung sysinput HAL; needs 0042 context. |
| `patches/trebledroid/platform_frameworks_base/0042-Add-support-for-Samsung-full-brightness-on-their-AID.patch` | G4 | Samsung AIDL fingerprint full-brightness only. |
| `patches/trebledroid/platform_frameworks_base/0010-Add-support-for-samsung-touch-physical-and-hover-pro.patch` | G4 | Samsung proximity sensor type strings only. |
| `patches/trebledroid-staging/platform_frameworks_base/0011-fall-back-to-sysfs-touch-poke-when-samsung-sysinput-.patch` | G4 | Samsung `/sys/class/sec/tsp` fallback; the device has no such node. |
| `patches/trebledroid/platform_frameworks_native/0001-On-Samsung-we-need-to-send-a-hack-message-to-HAL-to-.patch` | G4 | Samsung sensors hack (`persist.sys.phh.samsung_sensors`). |
| `patches/trebledroid/platform_frameworks_native/0004-Remove-Samsung-system-permission-on-sensors.patch` | G4 | Samsung `com.samsung.permission.SSENSOR` sensors only. |
| `patches/trebledroid-staging/platform_device_phh_treble/0019-allow-system_server-to-write-samsung-touch-sysfs-on-.patch` | G4 | SELinux rule for Samsung touch sysfs (`sysfs_ss_writable`). |
| `patches/trebledroid/platform_frameworks_av/0017-Add-a-prop-to-change-Samsung-flash-strength.patch` | G4 | Samsung camera flash strength extension; nothing builds on it. |
| `patches/trebledroid/platform_frameworks_av/0023-Allow-using-camera-modes-declared-in-Samsung-proprie.patch` | G4 | Samsung proprietary camera modes; nothing builds on it. |
| `patches/trebledroid/platform_frameworks_opt_telephony/0009-Initialize-Samsung-HIDL-ISehRadio.-Fixes-5G-on-S20-U.patch` | G5 | Samsung HIDL ISehRadio (5G on Galaxy S20 Ultra); needs 0008's `Android.bp` line. |
| `patches/trebledroid/platform_frameworks_opt_telephony/0008-Initialize-Samsung-AIDL-ISehRadioNetwork.-Fixes-5G-o.patch` | G5 | Samsung AIDL ISehRadioNetwork only. |
| `patches/trebledroid/platform_frameworks_base/0047-Include-vendor.samsung.hardware.radio-V2.2-java-HIDL.patch` | G5 | Adds the Samsung radio HIDL Java library to framework.jar for telephony 0009 only. |
| `patches/trebledroid/platform_frameworks_base/0046-Include-vendor.samsung.hardware.radio.network-V1-jav.patch` | G5 | Adds the Samsung radio AIDL Java library to framework.jar for telephony 0008 only. |
| `patches/trebledroid/platform_system_sepolicy/0001-Revert-Remove-28.0-compat-support.patch` | G6 | Restores SELinux 28.0 (Android 9 vendor) compat policy and mappings; the vendor policy is 31.0. Removed with build 0003. |
| `patches/trebledroid/platform_build/0003-Include-vndk-v28-sepolicy-support.patch` | G6 | Adds 28.0 to `PLATFORM_SEPOLICY_COMPAT_VERSIONS`; needs the system_sepolicy 0001 compat files. |
| `patches/personal/device_phh_treble/0005-base-providing-a-choice-of-additional-vndk-to-build-.patch` | G7 | Adds VNDK 30 to `PRODUCT_EXTRA_VNDK_VERSIONS`; the product ships only VNDK 31 (`PRODUCT_EXTRA_VNDK_VERSIONS := 31` in `hibreak-common.mk`). |
| `patches/trebledroid-staging/platform_packages_modules_vndk/0001-Revert-Removing-vndk-apex-v30.patch` | G7 | Restores the VNDK v30 APEX; the vendor is VNDK 31. |
| `patches/trebledroid/platform_packages_modules_vndk/0002-Revert-Remove-VNDK-v28.patch` | G7 | Restores the VNDK v28 APEX; the vendor is VNDK 31. |
| `patches/trebledroid/platform_packages_modules_vndk/0001-Revert-Removing-vndk-apex-v29.patch` | G7 | Restores the VNDK v29 APEX (context of the v28/v30 reverts); the vendor is VNDK 31. |
| `patches/trebledroid/platform_prebuilts_vndk_v29/0001-Add-android.hardware.audio.common-util-android.hardw.patch` | G7 | Extra libraries in the VNDK v29 snapshot; `prebuilts/vndk/v29` is no longer part of the manifest. |
| `patches/trebledroid-staging/platform_device_phh_treble/0002-guard-goodix-sysfs-write-behind-existence-check.patch` | G9 | Guards a Goodix touch `support_pen` sysfs write; the device has Elan/FTS touch and the unguarded write only logs an error. Its rebased override copy is removed as well. |
| `patches/personal/device_phh_treble/0006-Add-own-product-prop.patch` | G9 | Adds `product.prop`, referenced only by the bgNE/bvNE EROFS products, which `defaults/device_phh_treble/0013` removes. |
| `patches/personal/platform_system_sepolicy/0001-allow-TrebleDroid-permissive-domains-in-user-builds.patch` | G9 | `permissive_domains_on_user_builds` is consulted only for `user` builds; this product is built `userdebug`. Restore it if a `user` build is planned. |
| `patches/trebledroid-staging/platform_device_phh_treble/0020-allow-vendor-domains-to-read-system-and-default-prop.patch` | G8 | Security: grants every vendor domain read access to `system_prop`/`default_prop` and lets `vendor_init` set them. No denial on this device needs it; any vendor denial that appears is fixed with a targeted rule instead. |
| `patches/trebledroid/platform_system_core/0006-Ugly-but-secure-Set-dev-uinput-as-0666-to-fix-finger.patch` | G8 | Security: makes `/dev/uinput` world-writable. The fingerprint HAL here runs as user `system` in group `uhid` and does not use uinput; the AOSP mode 0660 suffices. |
| `patches/trebledroid-staging/platform_device_phh_treble/0025-disable-OPPO-touch-firmware-update-to-prevent-kernel.patch` | G8 | Security/robustness: writes to OPPO touch firmware nodes (`/proc/touchpanel`, `/sys/devices/platform/tpd`) at boot; neither node exists on this device. |
| `patches/personal/platform_system_sepolicy/0002-sepolicy-allow-crash_dump-to-ptrace-init-for-GSI-tombstone-capture.patch` | G8 | Security: lets `crash_dump` ptrace `init` and drops the matching neverallow. Init crashes from vendor incompatibilities (Samsung Exynos) do not occur here. |
| `patches/trebledroid/platform_external_selinux/0005-if-service-is-rcs-accept-conflict.-Seen-on-Moto-E5.patch` | G10 | Tolerates a conflicting `rcs` service context (Moto E5). The vendor `*_contexts` files on this device have no `rcs` entry. |
| `patches/trebledroid/platform_external_selinux/0007-Fix-boot-on-Moto-devices-using-unknown-class.patch` | G10 | Drops `class`/`classpermission` statements from vendor CIL and rules on `keystore_moto_key` (Moto). The vendor CIL here has no class declarations and no `keystore_moto_key`. |
| `patches/trebledroid/platform_frameworks_av/0024-Tell-Unihertz-Agold-we-are-not-a-GSI.-Fixes-aux-cam-.patch` | G10 | Calls the Unihertz/Agold `IAgoldDaemon` AIDL service; the service is not registered on this device. |
| `patches/trebledroid/platform_frameworks_av/0022-Include-Samsung-AIDL-camera-ids.patch` | G10 | Samsung AIDL `ISehCameraProvider` camera ids; context of 0024, removed with it. |
| `patches/trebledroid/platform_frameworks_av/0014-Support-Samsung-R-multi-cams.patch` | G10 | Samsung `ISehCameraProvider` 4.0 multi-camera support; needs 0009, base of 0022/0024. |
| `patches/trebledroid/platform_frameworks_av/0009-Add-persist.sys.phh.samsung.camera_ids-property-to-a.patch` | G10 | Samsung `ISehCameraProvider` 3.0 camera ids (`persist.sys.phh.samsung.camera_ids`); base of 0014/0022/0024. |
| `patches/trebledroid/platform_frameworks_av/0002-Fix-BT-in-call-on-CAF-devices.patch` | G10 | Adds a missing `BT SCO Headset` route (Qualcomm CAF policy). The vendor audio policy here already routes `BT SCO Headset`, so the fixup returns early. |
| `patches/trebledroid/platform_frameworks_base/0003-Fix-env-empty-string-ANDROID_STORAGE.patch` | G10 | Treats empty `ANDROID_*`/`EXTERNAL_STORAGE` variables as unset (Huawei hi6250 rc). None is empty in zygote's environment on this device. |
| `patches/trebledroid/platform_frameworks_native/0005-Mark-accelerometer-input-as-sensor-exclusively-if-th.patch` | G10 | Ignores `INPUT_PROP_ACCELEROMETER` on input devices without axes (Mi A2 Lite, Galaxy J8). No input device here has that property. |
| `patches/trebledroid-staging/platform_frameworks_base/0014-EuiccManager-force-enable-when-eUICC-slots-are-forced.patch` | G10 | Forces EuiccManager on when `persist.sys.phh.force_euicc_slots` is set. The device has no eUICC feature, no embedded slot and the property is unset. Removed with frameworks_opt_telephony staging 0002. |
| `patches/trebledroid-staging/platform_frameworks_opt_telephony/0002-UiccSlot-force-eUICC-detection-and-EuiccCard-creatio.patch` | G10 | Forces eUICC detection for slots listed in `persist.sys.phh.force_euicc_slots` (MTK DL2005/HCT eSIM). No eSIM on this device; inert without the property. |
| `patches/trebledroid-staging/platform_device_phh_treble/0007-allow-health-HAL-to-access-vendor-defined-sysfs_batt.patch` | G10 | Grants the health HAL access to a vendor `sysfs_battery` type. power_supply nodes here are labelled AOSP `sysfs_batteryinfo` and no such denial occurs. |
| `patches/trebledroid-staging/platform_device_phh_treble/0011-allow-USB-HAL-to-read-system-properties-on-samsung-e.patch` | G10 | Lets `hal_usb_default` read `system_prop` (coral USB HAL on Exynos). No process runs in `hal_usb_default` here. |
| `patches/trebledroid-staging/platform_device_phh_treble/0024-restart-fingerprint-HAL-after-USB-gadget-recovery.patch` | G10 | Restarts the fingerprint HAL after the USB gadget recovery of staging 0012 (Galaxy M33 TEE session loss). The UDC is bound at boot here, so the recovery is not needed; a fingerprint HAL restart is not wanted. 0012 stays. |
| `patches/trebledroid/platform_system_core/0010-FDE-is-dead.-Fallback-FDE-to-no-encryption-and-FDE-F.patch` | G10 | Accepts the FDE flags `forceencrypt=`/`forcefdeorfbe=` in fstab. The vendor fstabs here use `fileencryption=` and none of those flags. |
| `patches/trebledroid/platform_system_core/0013-watchdogd-Support-pinging-two-watchdogs.patch` | G10 | Pings a second watchdog `/dev/watchdog1`; this device has only `/dev/watchdog` and `/dev/watchdog0`. |
| `patches/trebledroid/platform_system_netd/0001-Huawei-Kirin-960-accept-broken-rpfilter-match.patch` | G10 | Ignores a failing ip6 `rpfilter` match (Kirin 960). The kernel here has `CONFIG_IP6_NF_MATCH_RPFILTER=y` and the match is registered. |
| `patches/trebledroid/platform_system_vold/0004-Exfat-can-be-mounted-with-exfat-kernel-fs-driver-or-.patch` | G10 | Adds Samsung `sdfat`/Sony `texfat` exFAT drivers. The kernel here registers only `exfat`, which AOSP vold already uses. |
