# CN 3.4.6 onto a `B651 NO_EEA_M2` phone: the background

The `B651 NO_EEA_M2` firmware line stops at 3.1.6 while `B651 CN` is on 3.4.6, so a NO_EEA
HiBreak Pro Color can only reach 3.4.6 by installing a CN package
([BIGME-OTA.md](BIGME-OTA.md) covers the servers and the lines). This page is the evidence:
what that package actually contains for this hardware, partition by partition, what it
changes, and why the flash has to be done the way it is.

**The commands are on the other page:**
[STOCK-CROSSFLASH-INSTALL.md](STOCK-CROSSFLASH-INSTALL.md). Read at least its safety box and
the mode warning before doing anything here.

**Verdict.** The CN package is the same firmware for the same board: same bootloader board
configuration, same AVB key, same modem build and band database, same APN database, same
panel overlays, same locale defaults. It does not touch `nvram` or the other per-device
partitions, so IMEI, MAC addresses and RF calibration survive it, and it raises no
anti-rollback index, so going back to 3.1.6 with the factory image stays possible. What it
costs: the update channel flips to `B651 CN` for good, and the CN `product` image carries a
much smaller Google app set.

Everything here comes from the package, its payload, the factory image and read-only
properties from a phone. It is no longer a paper claim: the flash has been carried out end to
end on the `B651 NO_EEA_M2` 3.1.6 phone of [What was compared](#what-was-compared), and it
boots 3.4.6. The one thing that session had to discover the hard way — that this phone has
two fastboot modes and each sees a different half of the partition table — is
[Two fastboot modes and what each can write](#two-fastboot-modes-and-what-each-can-write).

## What was compared

| Object | Identity |
| --- | --- |
| CN 3.4.6 full OTA | `B651_CN_3.4.6-OTA-FULL-7b21b7069c315b7c9b02472420c542a7.zip`, 2,568,381,284 bytes, MD5 `7b21b7069c315b7c9b02472420c542a7`, SHA-256 `e4e937495166d1d31dcebcc4dcafbd8c41cd2b0289ba0ed227f230fe2543dcee` |
| NO_EEA factory image | `B651_NO_EEA_M2_3.1.6_User_20260306_SMR_FW.zip`, 6,784,064,175 bytes, SP Flash Tool format with `MT6877_Android_scatter.xml` |
| Phone | stock 3.1.6, slot `_a`, locked |

The phone at the time of the check:

| Property | Value |
| --- | --- |
| `ro.build.versionName` / `.incremental` | `3.1.6` / `1772711616` |
| `ro.build.versionCode` | `B651 NO_EEA_M2` |
| `ro.product.device` | `Smartphone` |
| `gsm.version.baseband` | `MOLY.NR15.R3.MP.V155,MOLY.NR15.R3.MP.V155` |
| `ro.boot.flash.locked` | `1` |
| `ro.boot.verifiedbootstate` | `green` |
| `ro.boot.vbmeta.device_state` | `locked`, AVB 1.2, sha256, digest `c6d6a5102b856e54465c2744242e6a680a44f97dd576263213f261bdb66123f4` |
| `ro.boot.veritymode` | `enforcing` (`ro.boot.veritymode.managed` `yes`) |
| `super` | 12 GiB (GPT length `0x300000000`), UFS `MT256GAXAT4U31` |
| Filesystem sizes (`df -k`) | `system` 2,316,316 KiB, `system_ext` 748,080 KiB, `product` 2,452,792 KiB, `vendor` 654,052 KiB — each 100 % full, as squeezed images are |

## Reading a payload

The payload inside the OTA zip starts with its own headers rather than trailing them:

```
'CrAU' | BE u64 format version | BE u64 manifest size | BE u32 signature size
       | DeltaArchiveManifest | payload signature | blob data
```

For the 3.4.6 full package that is version 2, a manifest of 153,615 bytes at offset 24,
a 267-byte signature, and blob data from offset 153,906.
[`payload-parts.py`](payload-parts.py) parses the manifest with the protobuf module
`payload_dumper` ships and prints or extracts partitions:

```sh
python3 -m venv .venv && .venv/bin/pip install payload_dumper
.venv/bin/python payload-parts.py payload.bin                  # report
.venv/bin/python payload-parts.py payload.bin --list           # partition names
.venv/bin/python payload-parts.py payload.bin OUT boot dtbo    # extract those two
.venv/bin/python payload-parts.py payload.bin --lpmake         # the super.img build command
```

`--lpmake` prints the `lpmake` command that assembles the extracted dynamic partitions
into one `super` image with the payload's own sizes; [`check-super.py`](check-super.py)
then compares such a built image, byte for byte, with the images that went into it. **Neither
is needed to install anything**: the route in
[STOCK-CROSSFLASH-INSTALL.md](STOCK-CROSSFLASH-INSTALL.md) writes the four dynamic partitions
one at a time and lets `fastbootd` resize each, which is exactly what
[Does it fit in `super`](#does-it-fit-in-super) works out the room for. A hand-built `super`
is only worth assembling for a tool that insists on writing the whole group in one go.

Extraction verifies every operation hash and the hash of the rebuilt image, so an
extracted image is provably what `update_engine` would write. The four dynamic partitions
land as ext4 inside `super`; the matching files in the factory image are Android sparse,
so run those through `simg2img` before comparing. Both kinds can be read without root and
without mounting via `debugfs -R` (set `PAGER=cat`, `debugfs` pages by default).

## What the 3.4.6 payload writes

`block_size` 4096, `partial_update` false, `snapshot_enabled` true, `vabc_enabled`
false, 2,677 operations, 2,568,220,104 bytes of blob data. No operation references a
source partition: every partition is replaced whole, which is what makes a full package
installable from any other stock version.

| Partition | New image size | Ops | Payload data | SHA-256 of the rebuilt image |
| --- | --- | --- | --- | --- |
| `system` | 3,267,571,712 | 1559 | 1,689,389,300 | `9e1727f4f94ece385a94034d7dedb59ea472f4d7155161da15e529aa934d7926` |
| `product` | 744,222,720 | 355 | 285,529,893 | `eb5289d037ed887751fa0a5b2cbaaaa33377c290ef40e1520c362ef4d1a163c5` |
| `system_ext` | 756,183,040 | 361 | 263,924,233 | `b34921e6b8a0ca3c7667dd25e4958bdebac8a188529585ef48b5bef92e0ca0c6` |
| `vendor` | 681,676,800 | 326 | 261,252,679 | `01adad4356f8a047f8c4fa272bedee86ecf5bb05ae169c55f5511e3f7ef34e0d` |
| `md1img` | 63,479,808 | 31 | 34,978,507 | `d825963e4f7b09fe213d3bcde3fa3e1ab131c8cc977cfc67f91683c29bb36d34` |
| `boot` | 41,943,040 | 20 | 25,889,736 | `11019157acf62c9db368b6df783554a08714f966cd017010afc68b0fafc5a7c4` |
| `dtbo` | 8,388,608 | 4 | 8,540 | `ed48f789625916103d970509230a207ccff4fa58131b7d7bdad53881be39765c` |
| `gz` | 2,269,184 | 2 | 2,261,724 | `9ebd549e85cde6bc50cf4a93112906a93cb10cd1e32fbf8326bdc1a45426c3dd` |
| `lk` | 1,470,464 | 1 | 408,260 | `511f1571c3ea75d74c74d004f20dbc59c97d272ee73c23cee8aa7f7ad51fb626` |
| `scp` | 974,848 | 1 | 242,420 | `b00bc99edc557b29079d5613afc6155b2776db478cb3b5decaede39eb911609c` |
| `sspm` | 786,432 | 1 | 696,464 | `7ed81f0f20e2151572162c4b4b14de4a39874a76a1fa149042a7db10d0804725` |
| `tee` | 786,432 | 1 | 282,600 | `c7e96e6b4e04c24816b1ac33279185c4267d46af8ecb5da274be6e6f79af4cba` |
| `preloader_raw` | 618,496 | 1 | 241,736 | `c521973706d1f236a9543a743c2adfce2f6e7c8834f3c3ef0a9f481c6e680a97` |
| `mcupm` | 446,464 | 1 | 364,404 | `cfd0d8c1c7ea2aaa89a4decd8ecff4ff76d289059d86287391e21ba55130a535` |
| `cam_vpu2` | 6,508,544 | 4 | 2,136,340 | `e95e28f973c66622ef628535a1a05a1c33df76b9ff6204e9e156bd595c94c02a` |
| `cam_vpu1` | 2,768,896 | 2 | 441,884 | `259bf9534fd19f0c3cc6d2bee12c679c152df18f3fcc45dfc9d31eb1f2314cae` |
| `dpm` | 200,704 | 1 | 154,252 | `af291a468d17af11e38809c1c743126f701643615ffc09b5473f42c07c2d39cf` |
| `spmfw` | 16,384 | 1 | 8,180 | `0560cd3d4a1d6910155fa09a0a71a110d7f431de187eb17d440150a8ca9865a0` |
| `cam_vpu3` | 8,192 | 1 | 1,576 | `7efeda9b06563f9e34cb09a635077fe71e997c6cf08e487125ceec5b4d2e08c9` |
| `pi_img` | 8,192 | 1 | 1,868 | `9701f9362785c301c2a888a389d58c4a192b04e4ca922a4bf14d0f9b1a01e8d4` |
| `vbmeta` | 8,192 | 1 | 3,040 | `d64154ab481a99c19f1d325dfc00b6db43da94c8eca2cda15a5dac25bb0a106e` |
| `vbmeta_system` | 4,096 | 1 | 1,236 | `3f82f2d6c6720d4e327661ff93d5f03cdf208fa91d861dd32586869fe9d0a881` |
| `vbmeta_vendor` | 4,096 | 1 | 1,232 | `61d0ca381bd1a9d6a05652eb366c29f3455e261caa82bd72e2b031dc0b2d0215` |

Only `system` and `vendor` run a post-install step. The dynamic-partition metadata names
one group, `main`, of 12,882,804,736 bytes holding `product`, `system`, `system_ext` and
`vendor`. `vendor_boot` and `init_boot` are written by neither the payload nor the
factory image — the scatter gives both `file_name` `NONE` — so this firmware does not use
them, and `boot` carries kernel and ramdisk.

Every payload partition name resolves on the NO_EEA GPT through `/dev/block/by-name/` while
Android is running (`dtbo_a` is `sdc34`, `vbmeta_a` is `sdc7`, `lk_a` is `sdc30`,
`preloader_raw_a` is the device-mapper target `/dev/block/mapper/pl_a`), apart from the four
dynamic partitions, which live in `super`. **That is not the same thing as being writable
from fastboot.** The userspace `fastbootd` on this phone exposes only 20 of those names; the
other 17 partitions this package writes — `dtbo`, `lk`, `tee`, `gz`, `scp`, `sspm`, `spmfw`,
`mcupm`, `dpm`, `pi_img`, `cam_vpu1..3`, `md1img`, `vbmeta`, `vbmeta_system`,
`vbmeta_vendor` — can only be written from the bootloader's own fastboot mode. See
[Two fastboot modes and what each can write](#two-fastboot-modes-and-what-each-can-write).
The package also declares `pre-device=Smartphone` and **no** `pre-build`, so nothing in it
is tied to a particular source build.

## Partitions it leaves alone

`nvram`, `nvdata`, `nvcfg`, `protect1`, `protect2`, `proinfo`, `otp`, `sec1`, `seccfg`,
`frp`, `para`, `misc`, `metadata`, `logo`, `boot_para`, `waveform`, `vcom`,
`vendor_boot`, `init_boot` and `userdata`.

That list is the safety argument: `nvram`, `nvdata` and `proinfo` hold the IMEI, the
Bluetooth and Wi-Fi addresses and the per-device RF calibration, and none of them is
written. `seccfg` and `sec1` (the MTK security policy and its storage) are untouched too,
which is why verified boot stays `green`. `userdata` is untouched, so an applied OTA
keeps your data — the partition set is an upgrade, not a flash-everything image.

## CN 3.4.6 against NO_EEA 3.1.6, partition by partition

| Checked | CN 3.4.6 | NO_EEA_M2 3.1.6 | Reading |
| --- | --- | --- | --- |
| Board in `lk` | `k6877v1_64_k419`, `mediatek,mt6877`, and the build id `k6877v1_64_k419-28a8fec569e-20260831155526-…` | `k6877v1_64_k419`, `mediatek,mt6877`, `k6877v1_64_k419-a7215195c90-20260306110959-…` | one board configuration; only the build differs |
| RSA public keys inside `lk` (DER `30 82 01 22 30 0d 06 09 2a 86 48 86 f7 0d 01 01 01`) | `edf343d880317d38c6cd9ba2ab775051…` at 1280293 and 1463493, `051e3c5a1d927b9c756a339e62ed0412…` at 1280608, 1282517, 1463808, 1465717 | the same keys at the same offsets | Bigme signs both lines with one AVB key, so a locked phone keeps verifying after the flash |
| `vbmeta` | header bytes 0–255 identical to the NO_EEA copy; differences confined to bytes 256–4455 (signature, hash and per-partition descriptors); `sha256` at 3248, `boot` descriptor at 668, `vbmeta_system` at 1284, `com.android.build` property at 2488 in both | same | no anti-rollback or flags change, same descriptor layout |
| `md1img` | `TK_MD/NLWCG_MP_6877`, stamp `2025-02-26 14:49`, `MOLY_NR15_R3_MP_V155`, `MDDB_InfoCustomAppSrcP_MT6877_S00_MOLY_NR15_R3_MP_V155.EDB`, `DbgInfo_DSP_MT6877_MOLY_NR15_R3_MP_V155_2023-11-29_10_42.xz` | identical strings | same modem build and same band database. 147,941 unique strings against 147,943: the two extras are compressed-data noise |
| `vendor/build.prop` | 20,349 bytes; differs only in `ro.vendor.build.date`, `ro.vendor.build.date.utc`, `ro.vendor.build.fingerprint`, `ro.vendor.build.version.incremental` | 20,349 bytes | every radio, carrier, sensor and product property is shared |
| `/system/etc/apns-conf.xml` | MD5 `0cabe64dc72e8686368f4a04f4d1b3a0`, 1,657,924 bytes | same MD5 on the running phone | one APN database for both lines |
| `dtbo` | 802 unique strings | 803 | the only real difference is the build fingerprint: same panel and overlay set |
| Region defaults in `system/build.prop` | `ro.product.locale=en-US`, `persist.sys.language=zh`, `persist.sys.country=CN`, `persist.sys.timezone=Asia/Shanghai`, `ro.build.locale.area=http://ereader.xrztech.com:8090` | the same lines | no locale or timezone surprise; and an OTA keeps the user's own settings anyway (this phone runs `en-US`, `America/Los_Angeles`) |
| `ro.build.versionCode` | `B651 CN` | `B651 NO_EEA_M2` | the one thing that genuinely changes the phone's behaviour |
| `ro.build.versionName` / `ro.build.display.id` | `3.4.6` / `Bigme_HiBreak_V1.0_20260831` | `3.1.6` / `Bigme_HiBreak_V1.0_20260306` | both are Android 14 `UP1A.231005.007` system on an Android 12 `SP1A.210812.016` vendor |

## What changes on the phone

The visible difference is the app set, and it follows the `product` image: 744,222,720
bytes in CN 3.4.6, where this phone's `product` filesystem is 2,452,792 KiB.

Still there: `GmsCore`, `GoogleServicesFramework`, `Phonesky`, `WebViewGoogle64`,
`TrichromeLibrary64`, `SpeechServicesByGoogle`, `GooglePartnerSetup`, `GoogleRestore`,
`GoogleOneTimeInitializer`, `PersonalSafety`, `PrivateComputeServices`,
`SettingsIntelligence`, `Turbo`, `ImsServiceEntitlement`, `FamilyLinkParentalControls`,
`ConfigUpdater`, `AndroidSystemIntelligence` (all in `product/priv-app`), plus
`GmsSimProcessor`, `GoogleFeedback` and `NonFrameworkLbs` in `system_ext`. Google
accounts, Play Store, FCM and WebView keep working.

Gone, all reinstallable from the Play Store: `Chrome64`, `Gmail2`, `Maps`, `Photos`,
`YouTube`, `YTMusic`, `Drive`, `Keep`, `Meet`, `CalendarGoogle`, `CalculatorGoogle`,
`GoogleContacts`, `Velvet`, `Messages`, `Wellbeing`, `CrossDeviceServices`,
`AndroidAutoStub`, `GWP`, `PlayGames`, `SwitchAccess`, `talkback`, `ThemesStub`,
`AssistantShell`, `PartnerBookmarksProvider`. `LatinImeGoogle` is replaced by the AOSP
`LatinIME` and `TagGoogle` by `Tag`, which matters if you rely on either.

In `system/app`, CN 3.4.6 adds `xNote`, `Calculator`, `GlobalWritingService` and
`Recognize`; the rest of the Bigme/XRZ suite is the same list (`xLauncher3`, `xReader`,
`xReaderPro`, `xSettings`, `xMusicNew`, `xCloud`, `BookMall`, `BookSelf`, `ChatGPT`,
`ColorDict`, `XDict`, `XRZ_OuLuDict`, `ScanDOC`, `TranSlator`, `WifiTransferBook`,
`OfflineTTs`, `Googletts`, `XRZ*` tools, `xrzResService`, …). Nothing China-only such as
a CN app store or CN social apps appears.

The XRZ e-ink knobs move with the version: `ro.vendor.xrz.display_policy_version` 10 →
12, `ro.vendor.xrz.pen_type` 0 → 3, new `persist.vendor.xrz.fps` 120,
`persist.vendor.xrz.fps_low` 40, `persist.vendor.xrz.fps_high` 50, and
`ro.vendor.xrz.support_eink_animation=1`; the comic and video contrast, colour-enhance
and brightness defaults change too. These are 3.4.6 features, not CN-only behaviour, but
they do sit under the E-ink refresh and pen behaviour this GSI replicates — see
[EINK-DISPLAY.md](EINK-DISPLAY.md) and [HARDWARE-KEYS.md](HARDWARE-KEYS.md) for the
property names.

## Does it fit in `super`

The group `main` is 12,882,804,736 bytes of the 12 GiB `super` — 12,884,901,888 bytes,
with 2 MiB left for the `super` metadata itself.

| Bytes | `system` | `system_ext` | `product` | `vendor` | total |
| --- | --- | --- | --- | --- | --- |
| CN 3.4.6 payload images | 3,267,571,712 | 756,183,040 | 744,222,720 | 681,676,800 | 5,449,654,272 |
| this phone's filesystems (`df -k`) | 2,371,907,584 | 766,033,920 | 2,511,659,008 | 669,749,248 | 6,319,349,760 |

Free space in the group today is therefore 6,563,454,976 bytes. A virtual-A/B update does
not free the running slot first, so the new images have to fit into that free space: they
take 5,449,654,272 of it and leave 1,113,800,704 bytes for the copy-on-write device the
snapshot relies on (`snapshot_enabled` true, `vabc_enabled` false). Tight but workable,
and a CN phone taking the same package from the same 3.1.6 base has the same numbers. A
`super` image written from the DA side has no such constraint: it replaces the group
outright and needs only 5,449,654,272 of 12,882,804,736 bytes.

`update_engine` resizes the logical partitions itself during an A/B OTA, so none of this
is manual work on the stock path. It does matter for a hand-built `super`: the extents in
the `super` metadata have to be rebuilt for the new sizes rather than copied from the
3.1.6 layout, and the geometry and header checksums have to match afterwards.

## Two fastboot modes and what each can write

This is the thing that stops a first attempt. The phone answers `fastboot` in two modes, and
each one is told about a different half of the partition table. `fastbootd`, the userspace
one (`fastboot getvar is-userspace` → `yes`, reached with `adb reboot fastboot` or
`fastboot reboot fastboot`), knows the eight logical partitions and twelve physical ones:

```
system_a system_ext_a product_a vendor_a            (is-logical: yes)
system_b system_ext_b product_b vendor_b
boot_a boot_b metadata misc para sdc super userdata vendor_boot_a vendor_boot_b
preloader_raw_a preloader_raw_b
```

Everything else in the GPT is invisible to it. The same query in the bootloader's own
`fastboot` mode (`is-userspace: no`, reached with `adb reboot bootloader` or
`fastboot reboot bootloader`) returns 67 partitions and adds the ones this package writes:

```
dtbo_a dtbo_b lk_a lk_b tee_a tee_b gz_a gz_b scp_a scp_b sspm_a sspm_b spmfw_a spmfw_b
mcupm_a mcupm_b dpm_a dpm_b pi_img_a pi_img_b md1img_a md1img_b
cam_vpu1_a..cam_vpu3_a cam_vpu1_b..cam_vpu3_b
vbmeta_a vbmeta_b vbmeta_system_a/_b vbmeta_vendor_a/_b
logo waveform vcom boot_para expdb flashinfo frp mrdump nvram nvdata nvcfg otp pgpt sgpt
proinfo protect1 protect2 sec1 seccfg preloader preloader_a preloader_b init_boot_a/_b
```

Writing to a name the current mode does not know does not fail with "unknown partition". The
image is staged on the phone first, so `Sending` succeeds and only `Writing` fails — with a
warning that quotes a partition size of zero, because `getvar partition-size:dtbo_a` answers
`Could not open partition` in that mode. Flashing `dtbo` from `fastbootd`, which is where an
attempt that follows the first revision of this page stops:

```
$ fastboot flash dtbo_a extracted/dtbo.img
Warning: skip copying dtbo_a image avb footer (dtbo_a partition size: 0, dtbo_a image size: 8388608).
Sending 'dtbo_a' (8192 KB)                         OKAY [  0.271s]
Writing 'dtbo_a'                                   FAILED (remote: 'No such file or directory')
fastboot: error: Command failed
```

The image and its size are fine: `partition-size:dtbo_a` in the *other* mode says `0x800000`,
exactly the 8,388,608 bytes of `dtbo.img`. The fix is to change mode, not image, and the
install steps are written around that split. Of the 23 partitions the payload writes, `super` (or the four
inside it) and `boot` belong to `fastbootd`, `preloader_raw_a` is curiously visible only to
`fastbootd`, and the remaining 17 belong to the bootloader.

Two more differences between the modes, both measured on this phone:

| | `fastbootd` | bootloader fastboot |
| --- | --- | --- |
| `is-userspace` | `yes` | `no` |
| `max-download-size` | `0x10000000` (256 MiB) | `0x8000000` (128 MiB) |
| `getvar all` lists | 20 partitions | 67 partitions |
| `system`, `system_ext`, `product`, `vendor`, `super` | writable | not visible |
| `dtbo`, `lk`, `tee`, `gz`, `scp`, `sspm`, `spmfw`, `mcupm`, `dpm`, `pi_img`, `cam_vpu1..3`, `md1img`, `vbmeta*` | not visible | writable |
| `boot_a`, `metadata`, `misc`, `para`, `userdata`, `vendor_boot_a/_b` | writable | writable |

The bootloader's mode also reports `product: k6877v1_64_k419` where `fastbootd` reports
`product: Smartphone`, and it does **not** implement `fetch`: `fastboot fetch lk_a out.bin`
answers `Unable to get max-fetch-size. Device does not support fetch command.` Partitions
cannot be pulled off this phone over fastboot in the mode that can see them, so the stock
copies have to come from the factory image — which is the other reason to keep it. Nothing in
the install route needs a copy of `nvram` or its neighbours, because nothing in it writes
them; taking those copies at all needs a DA session, which these pages do not cover.

The AVB chain ties two of these together and leaves the rest alone. The auxiliary data of
`vbmeta.img`, in both firmware lines, carries hash descriptors for `boot` and `dtbo` and
chained-partition descriptors for `vbmeta_system` and `vbmeta_vendor`; no coprocessor
partition appears in it. So `boot`, `dtbo`, `vbmeta`, `vbmeta_system` and `vbmeta_vendor` are
one set that has to move together — step 5 of
[STOCK-CROSSFLASH-INSTALL.md](STOCK-CROSSFLASH-INSTALL.md) writes `dtbo` and `boot` first and
the three `vbmeta` images last, so a session that stops halfway never leaves a `vbmeta`
hashing the wrong images — while `lk` and the coprocessors can land in any order, or not at
all, without breaking verification.

## Ways in, and why only fastboot with an unlock works

This is the part with real risk, and none of it is about compatibility. Three of these five
paths do not exist on this phone at all, one does and is the route the install steps walk
through, and one is possible but deliberately not used.

| Route | Works? | Why |
| --- | --- | --- |
| Stock updater on the phone | no | the server keys the offer on `ro.build.versionCode`, so a `B651 NO_EEA_M2` phone is only ever offered 3.1.6, and there is no local-package path in the client: `/system/app/xSettings/xSettings.apk` has `SystemUpdatePreferenceController` and `retrieveSystemUpdateInfo` but no local-update string in any of its three dex files |
| `adb sideload` from recovery | no | there is no `recovery` partition in the GPT, and `vendor_boot`/`init_boot` are unused, so there is no recovery image to boot into |
| `fastboot flash` of the extracted images | **yes — this is the route, and it has been done on this phone** | it needs an unlock first (stock reports `ro.boot.flash.locked=1`, `verifiedbootstate=green`; unlocking wipes the phone and turns verified boot orange), **and it needs two modes**: `fastbootd` writes the four logical partitions and `boot`, and the bootloader's own fastboot writes `dtbo`, `lk`, the coprocessors, the modem and the three `vbmeta`s. See [Two fastboot modes and what each can write](#two-fastboot-modes-and-what-each-can-write) — an earlier revision of this page had all of it happening inside `fastbootd`, which stops dead at the first `dtbo` |
| `update_engine_client` over adb | no | needs root; a stock user build will not give it to `shell` |
| BROM/DA with mtkclient or SP Flash Tool | works on paper, deliberately not used and not documented here | the Android lock does not gate the BROM path: a `mtk printgpt` log kept beside the firmware downloads shows this unit answering a DA session with `SBC enabled: False`, `SLA enabled: False` and `DaHandler - Device is unprotected`. No DA write has ever been done on this phone. It also costs more than it saves: `system`, `system_ext`, `product` and `vendor` are not GPT partitions, so from that side they have to be assembled into one `super` image with rebuilt metadata extents — and the GSI of [README.md](README.md) needs the bootloader unlocked anyway, so the unlock it avoids is one the phone needs regardless |

`Setup for mtkclient.rtf`, kept beside the firmware downloads, is the Windows setup guide for
that BROM path: drop the old MediaTek drivers, turn Windows Memory Integrity off so
`usb2ser.sys` can load, install UsbDk (or use Zadig to put `libusb-win32` on the "MediaTek
USB Port" while the phone is in BROM), and enter BROM from a powered-off phone by holding both
volume keys and plugging in once the tool is waiting. Those are the same two volume keys that
make a HiBreak Pro show up in BROM at all, and a `printgpt` run through mtkclient on this unit
did complete, listing the 43 partitions of the simplified listing kept next to that guide.
Nothing further about the DA path is written up here.

Two things make an interrupted flash survivable. The GPT holds both copies of every partition
it carries (`lk_a`/`lk_b`, `preloader_raw_a`/`preloader_raw_b`, `md1img_a`/`md1img_b`), so any
of them can be rewritten from the factory image, and the `_b` copy this flash never touches is
still there underneath. Inside `super` it is different: the factory layout gives slot `_b` a
59 MB `system_b` stub and nothing else, so there is no bootable fallback for the four dynamic
partitions — a half-finished write there is repaired by finishing the list or by writing the
factory images back (step 8 of
[STOCK-CROSSFLASH-INSTALL.md](STOCK-CROSSFLASH-INSTALL.md)), never by booting the other slot.
And because the package writes no security or calibration partition, a restore with the
factory image puts the phone back as it was.

## Rolling back with the factory image

The rollback asset is the SP Flash Tool image for the phone's own line:
`B651_NO_EEA_M2_3.1.6_User_20260306_SMR_FW.zip` (6,784,064,175 bytes), published at
`https://bj.bcebos.com/bos-dawoyuji/fw/B651_NO_EEA_M2_3.1.6_User_20260306_SMR_FW.zip`.
Its `MT6877_Android_scatter.xml` lists 64 partitions for both `EMMC` and `UFS`; **24** of
them have `is_download true` and a real file. Those 24 are what a Download-Only session
writes, and 18 of them — the `_a` firmware rows, minus `preloader`, `logo`, `waveform`,
`vcom`, `super` and `userdata` — are exactly the set the fastboot rollback of step 8 writes.
Both counts were checked against the scatter file itself:

| Written | Not written, and why that matters |
| --- | --- |
| `preloader` (to the UFS boot LUs), `lk_a`, `boot_a`, `dtbo_a`, `vbmeta_a`, `vbmeta_system_a`, `vbmeta_vendor_a`, `tee_a`, `gz_a`, `spmfw_a`, `sspm_a`, `scp_a`, `mcupm_a`, `dpm_a`, `pi_img_a`, `cam_vpu1..3_a`, `md1img_a`, `waveform`, `vcom`, `logo`, `super`, `userdata` | `nvram`, `nvdata`, `nvcfg`, `protect1`, `protect2`, `proinfo`, `otp`, `sec1`, `seccfg`, `frp`, `para`, `misc`, `metadata`, `expdb`, `boot_para`, every `_b` partition, `pgpt` and `sgpt` — all `file_name NONE`, `is_download false` |

So calibration and identity survive a rollback: `nvram`, `nvdata` and `proinfo` are never
touched, `seccfg` and `sec1` stay as they are so the phone keeps its lock policy, and
`frp` is untouched. The GPT is not rewritten either — `pgpt` is not downloaded — so a
restore never re-partitions the flash.

Three things to get right:

- **`userdata` is in the download list**, with an 8 MB blank ext4 image, so a default
  Download-Only wipes user data. Untick that row to keep it — but a 3.4.6 → 3.1.6 step
  back over the same `/data` has not been tested, and credential-encrypted data is the
  first casualty when it goes wrong. Back up rather than gamble on it.
- **Only the `_a` copies are written** (`boot_a`, `vbmeta_a`, `lk_a`, …) and `misc` is not
  written, so the active slot stays whatever it was. This phone boots `_a`
  (`ro.boot.slot_suffix=_a`), which is the case a rollback handles cleanly. If CN ever got
  in through `update_engine`, which switches slots, the bootloader would still select `_b`
  after the restore — and the factory image puts nothing there but a small `system_b` stub.
  Clearing that slot state needs fastboot (unlocking, so a wipe) or a `misc` write from DA.
- **It does not need a DA session to apply.** On an unlocked phone every row a rollback needs
  is writable over fastboot — `super` in `fastbootd`, the other 18 in the bootloader's own
  fastboot — which is what step 8 of
  [STOCK-CROSSFLASH-INSTALL.md](STOCK-CROSSFLASH-INSTALL.md) does. SP Flash Tool remains an
  option, and remains the only way to write `userdata` or `preloader`.

`lpdump` over the factory `super.img` shows a single-slot layout, which is what makes the
rollback a clean replacement rather than a mix of two firmwares inside `super`:

| Logical partition | Group | Extent | Bytes |
| --- | --- | --- | --- |
| `product_a` | `main_a` | 4,985,280 sectors at super+2048 | 2,552,463,360 |
| `system_a` | `main_a` | 4,709,352 sectors at super+4,988,928 | 2,411,188,224 |
| `system_b` | `main_b` | 116,784 sectors at super+9,699,328 | 59,793,408 |
| `system_ext_a` | `main_a` | 1,520,920 sectors at super+9,818,112 | 778,711,040 |
| `vendor_a` | `main_a` | 1,330,800 sectors at super+11,339,776 | 681,369,600 |
| `product_b`, `system_ext_b`, `vendor_b` | `main_b` | none | 0 |

Metadata version 10.2, `virtual_ab_device` flag, three slots of 65,536 bytes, block device
`super` starting at sector 2048 and 12,884,901,888 bytes — the same geometry the CN payload
declares. `system_b` is where the zip's `system_other.img` belongs. The layout ends at
sector 12,670,576, so roughly 6.4 GB of the 12 GiB `super` is unallocated in the factory
state, which is the room an update to 3.4.6 sizes itself against.

Because `super.img` is sparse, only its non-empty chunks are written: anything CN 3.4.6 left
outside these extents stays on the flash but is no longer referenced by the metadata. The
rollback also restores `md1img_a`, so the modem returns to the same V155 build. And since both
lines are signed with the same AVB key and the rollback index does not move, the restored
3.1.6 `vbmeta` verifies whether the bootloader is locked or unlocked.

**Bottom line.** For a phone on slot `_a` — which is what this flash leaves — the factory
image is a genuine rollback, and its images are exactly what the phone ran beforehand. Its
fastboot form has not been performed here. It cannot undo anything done to `nvram` or
`seccfg`, but neither the forward flash nor the rollback writes those.

## Reproducing this

```sh
# tools: a venv for the manifest protobufs
python3 -m venv .venv && .venv/bin/pip install payload_dumper

# the OTA's payload and its package metadata
unzip -p B651_CN_3.4.6-OTA-FULL-*.zip payload.bin > payload.bin
unzip -p B651_CN_3.4.6-OTA-FULL-*.zip META-INF/com/android/metadata | tr ';' '\n'
#   -> ota-type=AB, pre-device=Smartphone, post-build=…, and no pre-build key at all

# the manifest, then the images (operation and image hashes are checked while extracting)
.venv/bin/python payload-parts.py payload.bin
.venv/bin/python payload-parts.py payload.bin extracted \
  system system_ext product vendor boot dtbo vbmeta vbmeta_system vbmeta_vendor \
  lk preloader_raw md1img tee gz scp sspm spmfw mcupm dpm pi_img \
  cam_vpu1 cam_vpu2 cam_vpu3

# optional, not used by the install steps: assemble and check a hand-built super image, the
# lpmake command generated from the manifest, check-super.py comparing every extent
.venv/bin/python payload-parts.py payload.bin --lpmake --images extracted --out super.img > lpmake.sh
sh lpmake.sh
simg2img super.img super-check.img && lpdump super-check.img
python3 check-super.py super-check.img extracted

# the factory copies are Android sparse and must be linearised first
unzip -o B651_NO_EEA_M2_3.1.6_User_20260306_SMR_FW.zip \
  '*/vendor.img' '*/system.img' '*/product.img' '*/dtbo.img' '*/lk.img' \
  '*/md1img.img' '*/vbmeta.img' '*/vbmeta_system.img' '*/vbmeta_vendor.img'
for i in vendor system product; do
  simg2img B651_NO_EEA_M2_3.1.6_User_20260306_SMR_FW/$i.img ${i}_raw.img
done

# read files out of ext4 images, no root and no mounting
PAGER=cat debugfs -R 'dump /build.prop cn_vendor.prop'  extracted/vendor.img
PAGER=cat debugfs -R 'dump /build.prop old_vendor.prop' vendor_raw.img
diff old_vendor.prop cn_vendor.prop
PAGER=cat debugfs -R 'ls -p /priv-app' extracted/product.img | awk -F/ 'NF>5 {print $6}'

# the AVB public keys embedded in the bootloader
python3 -c "
import hashlib, sys
pat = bytes.fromhex('30820122300d06092a864886f70d010101')  # RSA-2048 SPKI prefix
d = open(sys.argv[1], 'rb').read(); s = 0
while True:
    j = d.find(pat, s)
    if j < 0: break
    print(j, hashlib.sha256(d[j:j+0x126]).hexdigest())
    s = j + 1" extracted/lk.img

# what the phone says (getprop reads one property at a time: extra arguments are ignored)
for p in ro.build.versionCode ro.build.versionName gsm.version.baseband \
         ro.product.device ro.boot.flash.locked ro.boot.verifiedbootstate \
         ro.boot.vbmeta.digest; do
  printf '%s = %s\n' "$p" "$(adb shell getprop "$p")"
done
adb shell ls /dev/block/by-name/
```

## What this does not cover

- The flash has been walked through on one phone, once, and it boots. That is one data point,
  not a support matrix: no SIM was fitted during it, so mobile registration, voice and data
  after the channel flip have never been checked (step 7 of
  [STOCK-CROSSFLASH-INSTALL.md](STOCK-CROSSFLASH-INSTALL.md) asks for them), and nothing else
  about daily use of 3.4.6 on a NO_EEA unit has.
- A hand-built `super.img` has still not been put on a device, and the install route no longer
  asks for one: `--lpmake` and `check-super.py` were exercised on a synthetic payload — same
  metadata version, flags and layout shape, not Bigme's images. Writing the four logical
  partitions one at a time, which is what was measured here, leaves the metadata to
  `fastbootd`.
- The BROM/DA path is not documented here at all. The mtkclient sub-commands quoted on this
  page come from its README and none has been run by these notes; the scatter rows *are*
  checked against the real `MT6877_Android_scatter.xml`.
- Not compared: the contents of `product/overlay` and the CarrierConfig APKs, SELinux
  policy differences, and the kernel beyond the `boot` image hash. Region-specific
  telephony behaviour sometimes lives in a CarrierConfig overlay, and that would need its
  own pass over the two `product/overlay` directories.
- What is known about the DA is only what a `printgpt` session recorded beside the firmware
  downloads — `SBC enabled: False`, `SLA enabled: False`, `DaHandler - Device is unprotected`,
  43 partitions listed — so this unit accepts a Download Agent for reading. No DA **write** has
  ever been performed on this phone, and the preloader on the UFS boot LUNs was never compared
  between the two lines.
- Regulatory and warranty effects are not assessed: after this the phone reports CN
  firmware, on a CN update channel.
