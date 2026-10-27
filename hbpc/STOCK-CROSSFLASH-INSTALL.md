# Flashing CN 3.4.6 onto a `B651 NO_EEA_M2` HiBreak Pro Color

Commands only, in order. **Why** every one of them is there — the partition-by-partition
comparison of the two firmware lines, the `super` arithmetic, the two fastboot modes, the
rollback analysis — is in [STOCK-CROSSFLASH-INFO.md](STOCK-CROSSFLASH-INFO.md).

This replaces 22 partitions of the phone with Bigme's CN 3.4.6 firmware. It has been carried
out once, on a `B651 NO_EEA_M2` HiBreak Pro Color going 3.1.6 → 3.4.6, and that phone boots
3.4.6 with its baseband string and Bluetooth address unchanged.

## Read before starting

- **The bootloader has to be unlocked.** That wipes `/data` and turns verified boot `orange`
  for good; there is no undo.
- **The update channel becomes `B651 CN` permanently.** The servers answer for CN only
  afterwards and no server offers downgrades, so the factory image of your own line is the
  only way back. Get it before you start — step 1.3.
- **The Google app set shrinks.** `Chrome64`, `Gmail2`, `Maps`, `Photos`, `YouTube`, `Drive`,
  `Keep`, `Meet`, `CalendarGoogle`, `Messages`, `CrossDeviceServices` and about a dozen more
  leave the `product` image, all reinstallable from Play. `LatinImeGoogle` becomes the AOSP
  `LatinIME` and `TagGoogle` becomes `Tag`.
  [STOCK-CROSSFLASH-INFO.md](STOCK-CROSSFLASH-INFO.md#what-changes-on-the-phone) has both
  lists.
- **A GSI does not survive this.** If the phone runs the image of [README.md](README.md), it
  is gone: stock 3.4.6 first, then the GSI again.
- **There are two fastboot modes and neither can do the whole job.** `fastbootd` writes the
  four dynamic partitions of step 4 and nothing else in this package; the bootloader's own
  `fastboot` writes the remaining 18 of step 5. Flashing `dtbo_a` from `fastbootd` uploads the
  image happily and then dies with `Writing 'dtbo_a' FAILED (remote: 'No such file or
  directory')`. If that is the error in front of you, change mode, not image.
- **Never** write `nvram`, `nvdata`, `nvcfg`, `protect1`, `protect2`, `proinfo`, `otp`, `sec1`
  or `seccfg`, and never use "Format All + Download" in SP Flash Tool. The IMEI, the MAC
  addresses and the RF calibration live in those partitions. No command on this page names
  them; what is forbidden outright is listed under [Never](#never) at the end.

## The shape of it

| Step | What | Where the phone is |
| --- | --- | --- |
| 1 | Back up and record | Android, USB debugging on |
| 2 | Download, verify, extract 22 images | host only, phone untouched |
| 3 | Unlock the bootloader — wipes `/data` | bootloader `fastboot` |
| 4 | Flash `system`, `system_ext`, `product`, `vendor` | **`fastbootd`** |
| 5 | Flash `dtbo`, `boot`, 13 firmware images, 3 `vbmeta`s | **bootloader `fastboot`** |
| 6 | Reboot | — |
| 7 | Check that it took | Android |
| 8 | Roll back to 3.1.6, if you need to | both modes again |

4 + 18 = the 22 images of the package. Steps 4 and 5 cannot be merged into one session.

## What you need

| On the host | For |
| --- | --- |
| `adb`, `fastboot` | every step (Arch: `android-tools`) |
| `dumpe2fs` | one sanity check in step 2.3 (`e2fsprogs`) |
| Python 3 and `payload_dumper` | the extraction in step 2 |
| ~10 GB free, on a filesystem that supports holes | the 2.4 GiB zip, the 2.4 GiB `payload.bin` and 5.4 GB of extracted images. FAT32 refuses files over 4 GiB outright |
| the factory image zip of your own line | the way back — step 1.3 |
| a USB port that you can leave alone for six minutes | step 6 |

Set this up once, in one directory you will use for all of it:

```sh
mkdir -p ~/bigme-b651 && cd ~/bigme-b651
HBPC=/path/to/LineageOS_GSI_Bigme/hbpc      # the directory holding payload-parts.py
```

## 1. Backups and records

Everything in this section is read-only apart from making files on the host. Do it all before
step 3 wipes anything, or there is nothing to compare against afterwards.

### 1.1 Copy off what you want to keep

The unlock in step 3 erases `/data`: photos, downloads, chat databases, everything not already
in an account.

```sh
cd ~/bigme-b651 && mkdir -p before after
adb devices -l                      # approve the authorisation prompt on the phone
adb pull /sdcard/Download before/sdcard-Download
# and the same for /sdcard/DCIM, /sdcard/Documents, anywhere else you keep things
```

`/data` itself needs root and is not readable on a stock phone.

### 1.2 Write down what identifies this phone

Three readings, and step 7 repeats two of them to prove the per-device partitions came
through:

```sh
adb shell ip link show wlan0                    | grep -i ether > before/wlan.txt
adb shell settings get secure bluetooth_address > before/bt.txt
```

If SELinux refuses the first, read the Wi-Fi address in the Settings app. The IMEI is not a
property at all: dial `*#06#` and write it down somewhere that is not this directory.

### 1.3 Get the factory image of your own line, and unpack what step 8 needs

`B651_NO_EEA_M2_3.1.6_User_20260306_SMR_FW.zip`, 6,784,064,175 bytes, published at
`https://bj.bcebos.com/bos-dawoyuji/fw/B651_NO_EEA_M2_3.1.6_User_20260306_SMR_FW.zip` — use
the file for **your** version and model, and keep the zip itself, not just the extracts. Once
`ro.build.versionCode` reads `B651 CN` the servers answer for CN only, so this file is the
only copy of NO_EEA firmware you will have.

```sh
cd ~/bigme-b651
unzip -o B651_NO_EEA_M2_3.1.6_User_20260306_SMR_FW.zip -d factory \
  '*/boot.img' '*/dtbo.img' '*/lk.img' '*/tee.img' '*/gz.img' '*/scp.img' '*/sspm.img' \
  '*/spmfw.img' '*/mcupm.img' '*/dpm.img' '*/pi_img.img' '*/cam_vpu1.img' '*/cam_vpu2.img' \
  '*/cam_vpu3.img' '*/md1img.img' '*/vbmeta.img' '*/vbmeta_system.img' '*/vbmeta_vendor.img'
find factory -name '*.img' | wc -l           # 18, under the directory the zip carries
```

Those 18 files are what step 8 writes back to undo this, and step 8 looks them up by name
under `factory/`. Keep the zip whole as well: its `super.img` (6,432,293,208 bytes sparse) is
the 3.1.6 dynamic partitions, and step 8 unpacks that one only if it is needed, since it costs
another 6 GB.

### 1.4 Record what the phone says now

```sh
adb shell getprop > before/props.txt
for p in ro.build.versionCode ro.build.versionName ro.build.version.incremental \
         ro.build.display.id ro.build.fingerprint \
         ro.product.device ro.product.model ro.product.cpu.abi \
         ro.boot.slot_suffix ro.boot.flash.locked ro.boot.verifiedbootstate \
         ro.boot.vbmeta.device_state ro.boot.vbmeta.avb_version \
         ro.boot.vbmeta.hash_alg ro.boot.vbmeta.digest ro.boot.veritymode \
         gsm.version.baseband gsm.sim.state ro.virtual_ab.enabled; do
  printf '%s = %s\n' "$p" "$(adb shell getprop "$p")"
done | tee before/key-props.txt
adb shell ls -l /dev/block/by-name/ > before/by-name.txt
adb shell df -k                     > before/df.txt
# nothing may be sitting mid-update: this must show no active snapshot or merge
adb shell getprop | grep -E 'virtual_ab|snapshot|update_engine' | tee before/ab.txt
```

`ro.boot.slot_suffix` has to read `_a`. Every command on this page writes the `_a` copies,
because that is what this phone boots; on a phone that says `_b`, stop and reconsider before
flashing anything.

### 1.5 What is deliberately not backed up

`nvram`, `nvdata`, `nvcfg`, `protect1`, `protect2`, `proinfo`, `otp`, `sec1` and `seccfg` hold
the IMEI, the MAC addresses and the RF calibration. They can only be read from a Download-Agent
session, which this guide does not cover, and **nothing in these steps writes them** — that is
what the partition comparison in
[STOCK-CROSSFLASH-INFO.md](STOCK-CROSSFLASH-INFO.md#partitions-it-leaves-alone) establishes.
If you want copies of them anyway, that is a separate mtkclient job, done before anything
else, and a wrong write there is the one failure a factory image does not repair.

## 2. Get the images onto the host

The phone is still untouched through this section.

### 2.1 Download the package and check it

```sh
cd ~/bigme-b651
url='https://bdbos.bigme.vip/phone/b651/B651CN/B651_CN_3.4.6-OTA-FULL-7b21b7069c315b7c9b02472420c542a7.zip'
curl -fL -o "$(basename "$url")" "$url"
md5sum B651_CN_3.4.6-OTA-FULL-*.zip      # 7b21b7069c315b7c9b02472420c542a7
sha256sum B651_CN_3.4.6-OTA-FULL-*.zip   # e4e937495166d1d31dcebcc4dcafbd8c41cd2b0289ba0ed227f230fe2543dcee
unzip -t B651_CN_3.4.6-OTA-FULL-*.zip > before/unzip-test.log && echo zip-ok
unzip -p B651_CN_3.4.6-OTA-FULL-*.zip META-INF/com/android/metadata | tr ';' '\n'
#   -> ota-type=AB, pre-device=Smartphone, and no pre-build key at all
unzip -p B651_CN_3.4.6-OTA-FULL-*.zip payload.bin > payload.bin
```

**Stop if the MD5 does not match.** If that URL no longer resolves, ask the servers for a
current one — the query sends your serial number, so run it yourself and take `otaUrl` and
`otaMd5` from `ota-query/cn-response.json`
([BIGME-OTA.md](BIGME-OTA.md) is the protocol):

```sh
$HBPC/bigme-ota.py --os-name 'B651 CN' --os-version 0.0.0 --output-dir ota-query
```

### 2.2 Take the 22 images out of the payload

```sh
cd ~/bigme-b651
python3 -m venv .venv && .venv/bin/pip install payload_dumper
.venv/bin/python $HBPC/payload-parts.py payload.bin --list      # 23 in the package
.venv/bin/python $HBPC/payload-parts.py payload.bin extracted \
  system system_ext product vendor boot dtbo \
  lk tee gz scp sspm spmfw mcupm dpm pi_img cam_vpu1 cam_vpu2 cam_vpu3 md1img \
  vbmeta_system vbmeta_vendor vbmeta 2>&1 | tee extract.log
grep -c 'HASH OK' extract.log      # 22
grep -v  'HASH OK' extract.log     # nothing
du -sh extracted                   # about 5.4G
```

`preloader_raw`, the 23rd image in the package, is deliberately left out. The preloader that
actually runs lives on the UFS boot LUNs, which fastboot cannot reach, and this flash changes
nothing down there.

Extraction checks every operation hash and the hash of each rebuilt image, so these files are
byte for byte what Bigme's own updater would have written.

### 2.3 One check worth doing

The four dynamic partitions are the ones whose size changes. Each file should be exactly what
the manifest promises, and a whole ext4 filesystem:

```sh
for i in system system_ext product vendor; do
  printf '%-11s file=%13s  ext4=%13s\n' "$i" "$(stat -c %s extracted/$i.img)" \
    "$(dumpe2fs -h extracted/$i.img 2>/dev/null |
        awk '/^Block count:/{c=$NF} /^Block size:/{s=$NF} END{print c*s}')"
done
#  system      file=3267571712  ext4=3267571712
#  system_ext  file= 756183040  ext4= 756183040
#  product     file= 744222720  ext4= 744222720
#  vendor      file= 681676800  ext4= 681676800
```

Those four total 5,449,654,272 bytes. The `main` group on the phone holds 12,882,804,736 and
the 3.1.6 partitions inside it take 6,423,732,224, so `fastbootd` has room to resize each one
as it writes it. **Nothing has to be assembled first — there is no `super.img` to build.**

## 3. Unlock the bootloader — this wipes the phone

Everything under `/data` goes. Step 1.1 is the only thing that survives it.

```sh
adb reboot bootloader
fastboot getvar product             # k6877v1_64_k419
fastboot getvar unlocked            # no
fastboot getvar current-slot        # a
fastboot flashing unlock            # on the phone: Volume Up, then Power
```

If the build does not know `flashing unlock`, the older spelling is `fastboot oem unlock`; the
warning screen is the same either way. The phone wipes, reboots, and shows the orange verified
boot state on every boot from now on. Afterwards `fastboot getvar unlocked` says `yes` and
`fastboot getvar secure` says `no`.

Two ways forward from the wipe:

- **straight to step 4**, without going through Android: `fastboot reboot fastboot`;
- or let it boot the factory-reset welcome, switch **USB debugging** back on (Developer
  options is off again after a wipe), and use `adb reboot fastboot` when you get there.

## 4. Flash the dynamic partitions — `fastbootd`

```sh
fastboot getvar is-userspace        # yes — if it says no, stop, this is the wrong mode
cd ~/bigme-b651
fastboot flash system     extracted/system.img
fastboot flash system_ext extracted/system_ext.img
fastboot flash product    extracted/product.img
fastboot flash vendor     extracted/vendor.img
```

Four names, no `_a`: `fastbootd` picks the slot itself. That is 5.4 GB across the wire, so
expect a few minutes; every line ends `OKAY`. Read the new geometry back before moving on:

```sh
fastboot getvar partition-size:system_a      # 0xC2C33000 = 3,267,571,712
fastboot getvar partition-size:system_ext_a  # 0x2D127000 =   756,183,040
fastboot getvar partition-size:product_a     # 0x2C5BF000 =   744,222,720
fastboot getvar partition-size:vendor_a      # 0x28A19000 =   681,676,800
```

Each one equals its image size: the metadata has been rebuilt for 3.4.6 and the new layout has
taken. If a `partition-size` there answers `Could not open partition`, you are in the
bootloader's fastboot and not in `fastbootd`.

## 5. Flash the other 18 — the bootloader's own `fastboot`

```sh
fastboot reboot bootloader
fastboot getvar is-userspace            # no — and the four of step 4 have gone from getvar all
fastboot getvar partition-size:dtbo_a   # 0x800000, which fastbootd could not tell you
```

Order matters at the end only: the three `vbmeta` images go **last**, so a session that stops
halfway never leaves a `vbmeta` hashing images the phone does not have.

```sh
# 5.1 overlays, then kernel
fastboot flash dtbo_a extracted/dtbo.img
fastboot flash boot_a extracted/boot.img

# 5.2 the coprocessors and the modem
for p in lk tee gz scp sspm spmfw mcupm dpm pi_img cam_vpu1 cam_vpu2 cam_vpu3 md1img; do
  fastboot flash ${p}_a extracted/$p.img
done

# 5.3 verified boot, last of all. Do NOT add --disable-verity --disable-verification here:
#     that flag belongs to the GSI instructions, where system is a foreign image. Every
#     image in this flash is Bigme's own and its hash has to stay in the chain.
fastboot flash vbmeta_system_a extracted/vbmeta_system.img
fastboot flash vbmeta_vendor_a extracted/vbmeta_vendor.img
fastboot flash vbmeta_a        extracted/vbmeta.img
```

Every name in this section takes the `_a` suffix: 2 + 13 + 3 = 18 writes, about 130 MB, under a
minute on a USB 3 port. `lk_a` is the bootloader itself, which makes it the one write where a
cable pulled mid-transfer would matter — it went through without incident here, `lk_b` is
untouched underneath, and the factory `lk.img` unpacked in step 1.3 replaces it.

## 6. Reboot, and then leave it alone

```sh
fastboot reboot
adb wait-for-device
```

Wait, and do not touch the cable. On this phone `adb wait-for-device` sat on
`no devices/emulators found` for about **six minutes** before USB came back
(`0e8d:201d MediaTek Inc. HiBreak`), and the screen stayed on the Bigme logo for most of that:
a cross-line first boot migrates `/data` and re-runs dex2oat. That is normal. Interrupting it is
the one thing here that turns a flash into a repair job.

## 7. Checks

Once `adb devices` lists the phone:

```sh
for p in ro.build.versionCode ro.build.versionName ro.build.version.incremental \
         ro.build.display.id ro.build.fingerprint \
         ro.boot.slot_suffix ro.boot.flash.locked ro.boot.verifiedbootstate \
         ro.boot.vbmeta.device_state ro.boot.vbmeta.digest \
         gsm.version.baseband gsm.sim.state \
         ro.vendor.xrz.display_policy_version ro.vendor.xrz.pen_type; do
  printf '%s = %s\n' "$p" "$(adb shell getprop "$p")"
done | tee after/key-props.txt
diff before/key-props.txt after/key-props.txt
```

What the phone that ran these steps reported:

| Property | Measured after the flash |
| --- | --- |
| `ro.build.versionCode` | `B651 CN` — the channel flip, and permanent |
| `ro.build.versionName` / `ro.build.display.id` | `3.4.6` / `Bigme_HiBreak_V1.0_20260831` |
| `ro.build.version.incremental` | `1781167373` |
| `ro.build.fingerprint` | `Bigme/HiBreak/Smartphone:14/UP1A.231005.007/1781167373:user/release-keys` |
| `ro.boot.vbmeta.digest` | different from `before/`, because the images it hashes are different |
| `gsm.version.baseband` | **unchanged**: `MOLY.NR15.R3.MP.V155,MOLY.NR15.R3.MP.V155` |
| `ro.boot.flash.locked` / `ro.boot.verifiedbootstate` | `0` / `orange`, from the unlock |
| `ro.vendor.xrz.*` | `display_policy_version` 12, `pen_type` 3, `support_eink_animation` 1, `persist.vendor.xrz.fps` 120 |
| `gsm.sim.state` | **not checked**: no SIM was fitted. Do this one with a SIM in, and make one call in and one call out over mobile before you trust the phone |

Then the identity readings of step 1.2, which must match `before/`:

```sh
adb shell ip link show wlan0 | grep -i ether
adb shell settings get secure bluetooth_address
```

and dial `*#06#` once more. On the measured phone the Bluetooth address was **identical** to
the one recorded beforehand — the stronger form of that check than it looks, because the unlock
wiped `/data` and the value in `settings` had to be re-read from the controller in
`nvram`/`proinfo` rather than replayed from the settings database. If the IMEI or either
address has moved, stop using the radio and get those partitions restored before anything
else.

The last two things are housekeeping. The Google apps the CN `product` image drops come back
from the Play Store — except `LatinImeGoogle` → the AOSP `LatinIME` and `TagGoogle` → `Tag`,
which are substitutions rather than reinstalls. And the channel really has flipped; these
queries send your serial number, so run it yourself
([BIGME-OTA.md](BIGME-OTA.md)):

```sh
$HBPC/bigme-ota.py --os-name 'B651 CN' --os-version 3.4.6 --output-dir ota-query
#   -> 已是最新版本, already the newest of the line
```

## 8. If it does not boot, or you want 3.1.6 back

A red verified-boot state or a bootloop before the launcher means one image did not land or the
AVB set is inconsistent. Re-run the failed command from step 5 first — a partition interrupted
mid-write is the usual cause, and the fix is the same command again.

To go all the way back, use the 18 factory images unpacked in step 1.3 plus the factory
`super.img`, in the same two modes:

```sh
# 8.1 fastbootd: the 3.1.6 dynamic partitions, straight out of the factory zip
unzip -o B651_NO_EEA_M2_3.1.6_User_20260306_SMR_FW.zip '*/super.img' -d factory
adb reboot fastboot                 # or: fastboot reboot fastboot
fastboot getvar is-userspace        # yes
fastboot flash super "$(find "$PWD/factory" -name super.img)"

# 8.2 the rest, from the bootloader's fastboot
fastboot reboot bootloader
fastboot getvar is-userspace        # no
F=$(find "$PWD/factory" -name vbmeta.img -printf '%h\n' | head -1)
for p in boot_a dtbo_a lk_a tee_a gz_a scp_a sspm_a spmfw_a mcupm_a dpm_a pi_img_a \
         cam_vpu1_a cam_vpu2_a cam_vpu3_a md1img_a \
         vbmeta_system_a vbmeta_vendor_a vbmeta_a; do
  fastboot flash "$p" "$F/${p%_a}.img"
done
fastboot reboot
```

Four things about that:

- **Name the partitions, as above; never loop over a scatter file's download list.** Rows such
  as `nvram`, `proinfo`, `sec1`, `frp`, `misc` and `para` point at blank templates inside that
  zip, and writing them is how a repair becomes a phone with no IMEI.
- Add `fastboot -w` before the last reboot if it is `/data` that will not mount. The
  3.4.6 → 3.1.6 step over an existing `/data` has not been tested.
- Both firmware lines are signed with the same AVB key and the anti-rollback index never moved,
  so restored 3.1.6 images verify.
- `preloader` is in neither list, which is what you want: neither this flash nor the rollback can
  reach the UFS boot LUNs from fastboot.

### Never

- "Format All + Download" in SP Flash Tool, or any erase command aimed at a partition you did
  not name yourself.
- Writing `nvram`, `nvdata`, `nvcfg`, `protect1`, `protect2`, `proinfo`, `otp`, `sec1` or
  `seccfg`. The bootloader's fastboot lists every one of them and accepts
  `fastboot flash nvram …` or `fastboot erase proinfo` without a second thought, which does not
  make it a good idea: the IMEI, the MAC addresses and the RF calibration live there, and
  nothing but a backup — or Bigme support — puts them back. Nothing in steps 1 to 8 writes them.
- A HiBreak Pro (monochrome) firmware, or any other model's factory image, on this phone. Only
  the B651 packages named here apply.
- Unlocking without a backup of `/data`: it wipes, whatever else it was meant to achieve.

---

The reasons behind every step here — the partition-by-partition comparison of the two firmware
lines, what the payload writes and leaves alone, the `super` arithmetic, the two fastboot modes
with their partition lists, and the factory image's download list — are in
[STOCK-CROSSFLASH-INFO.md](STOCK-CROSSFLASH-INFO.md). The GSI this replaces is
[README.md](README.md).
