# Bigme stock firmware and app update servers

[`bigme-ota.py`](bigme-ota.py) asks Bigme's official update servers which stock
firmware (OTA) package and which system-app updates they offer a phone. It only
fetches metadata: it never downloads or installs anything. This page describes both
protocols so you can check the stock firmware before you go back to stock, or
reimplement the queries.

Nothing here applies to the GSI. The GSI does not use these servers, and the stock
packages they offer cannot be installed over it (see [Limits](#limits)).

The servers answer per device. A request carries your phone's serial number (SN),
and the offer depends on the SN, model and OS version you send. Send only your own
phone's SN. The script never prints it and does not write it in plain text.

## Servers

| Purpose | Endpoint | Body |
| --- | --- | --- |
| Firmware (OTA), CN server | `POST http://ereader.bigme.vip:8090/json/osupgrade.action` | RSA-encrypted, Base64 |
| Firmware (OTA), USA server | `POST http://usa.bigme.vip:8090/json/osupgrade.action` | RSA-encrypted, Base64 |
| System-app updates | `POST http://ereader.bigme.vip:8081/xrzApp` | plain JSON |

All of them use plain HTTP. Downloads come from HTTPS object storage
(`bdboscn.bigme.vip` for firmware, `bame.bj.bcebos.com` for apps). The October 2026
OTA responses named `bdbos.bigme.vip` instead; both hosts serve the same firmware
objects (same size, ETag and checksums), `bdbos` through a CDN edge, `bdboscn` through
nginx.

"CN" and "USA" name the server, not the firmware region: the model you send picks
the firmware. For a `B651 CN` request both servers have returned the same CN package.
The stock client gets its server list from `POST http://ereader.bigme.vip:8081/api/xrzHost`
(a separately signed and encrypted API). In September 2026 that list named exactly
these two hosts, so the script does not query it.

## Firmware (OTA) query

### Request

The stock Settings app builds this JSON object:

| Field | Meaning |
| --- | --- |
| `sn` | Device SN. The stock firmware reads `vendor.gsm.serial`, or `ro.boot.serialno` when that is empty or `unKnow`. |
| `osName` | Stock firmware line, the value of `ro.build.versionCode`: `B651 CN` on a CN build, `B651 NO_EEA_M2` on the same phone at stock 3.1.6. An unknown value gets `不存在此系统名称` ("no such system name") and no offer. See [Firmware lines](#firmware-lines). |
| `osVersion` | Installed stock OS version, for example `3.3.0`. Not a GSI or Android build ID. |
| `otaFailCount` | Optional. The stock client adds it only after a failed update. |

Encoding:

1. Serialize the object as compact UTF-8 JSON.
2. Split the bytes into chunks of at most 117 bytes.
3. Encrypt each chunk with the client's RSA-1024 public key, PKCS#1 v1.5 padding.
   Each chunk gives 128 bytes of ciphertext.
4. Concatenate the ciphertext and Base64-encode it. That is the POST body.

Headers: `Content-Type: application/json; charset=utf-8` and `lang: <locale>`. The
stock client sends `Locale.toLanguageTag()`, for example `zh-CN`. It sends no login
token or signature for this call.

The public key (request) and the private key (response) are the two keys in
`bigme-ota.py` (`PUB_DER_B64`, `PRIV_DER_B64`, DER, Base64). They ship inside the
official client (`libxrzEncrypt.so` in Settings) and are the same for every phone.
They are not device secrets.

### Response

Base64-decode the body. The result must be a whole number of 128-byte blocks. Decrypt
each block with the client private key (PKCS#1 v1.5), concatenate the plaintext and
parse it as UTF-8 JSON.

| Field | Meaning |
| --- | --- |
| `head.resultCode`, `head.resultMsg` | `0` / `访问成功` ("access succeeded") when the request was processed. |
| `upgrade` | `true` when the server offers a package to this device. |
| `msg` | Server note, in Chinese. Seen: `所有设备可升级,差分包升级` ("all devices may upgrade, incremental package") with a delta offer, `所有设备可升级,越级整包升级` ("all devices may upgrade, skip-level full package") with a full one, `禁止升级` ("upgrade not allowed") which gives no reason, `已是最新版本` ("already the latest version") when the version sent is the newest of the line, and `不存在此系统名称=<osName>` ("no such system name") for an unknown `osName`. The same request once got `禁止升级` and weeks later an offer. |
| `otaUrl` | HTTPS download URL of the package, empty without an offer. |
| `otaMd5` | MD5 of the package (lowercase hex). The package file name also ends in it. |
| `osFileSize` | Package size in bytes. |
| `osVersion` | Target OS version, for example `3.4.6`. |
| `wholePackage` | `false` for an incremental package, which needs the exact stock version you sent. `true` for a full package, which the server sends when the version you send is too old for its delta chain — see [Full packages](#full-packages). A full package reports `osFileSize` `-1`. |
| `upgradeMsg` | Release notes as HTML, in Chinese. |
| `forceUpgrade`, `status`, `taskId` | Seen as `0`, `0` and `""`. |

Only one package has been seen per request. The 3.4.6 release notes say that the
rollout is staged ("if no firmware is found, try again the next day").

### Firmware lines

`osName` selects a firmware *line*, and each line carries its own newest version. Seen
for the B651 (HiBreak Pro Color):

| `osName` | Newest build offered | CDN path |
| --- | --- | --- |
| `B651 CN` | 3.4.6: full, plus incremental from 3.3.0 and from 3.4.0 | `/phone/b651/B651CN/` |
| `B651 NO_EEA_M2` | 3.1.6: full only, at 3.0.0, 3.1.2 and `0.0.0` alike | `/phone/b651/no_eea_m2/` |
| `B651 EEA_M2` | 3.1.6: full only | `/phone/b651/eea_m2/` |

A phone reports the line it is on in `ro.build.versionCode`, so a HiBreak Pro Color at
stock 3.1.6 (`B651 NO_EEA_M2`) is told `已是最新版本` and never sees 3.4.6: the newer CN
build only appears when `B651 CN` is sent. Read the line of a stock system with
`adb shell getprop ro.build.versionCode`. `M2` looks like a panel/variant marker and
`NO_EEA` / `EEA` / `CN` a region channel, and one phone may be queried against any of
these lines; both `B651 CN` packages checked here declare `pre-device=Smartphone`.

### Full packages

A line offers exactly one package and it is always its newest build, whose delta chain
reaches back only a version or two. When the `osVersion` sent is older than that chain
the server answers with a **full** package instead of a delta: `msg`
`所有设备可升级,越级整包升级`, `wholePackage: true`, `osFileSize` `-1`, and a file name of
the form `<line>_<version>-OTA-FULL-<md5>.zip`. Sending `0.0.0` did this on all three
B651 lines tried, which is how a phone that cannot complete a delta gets back to
current stock.

The distinction is real in the package itself: the full package has no `pre-build` key
in `META-INF/com/android/metadata`, while the 3.4.6-3.3.0 incremental does, so
`update_engine` has no source-partition hash to verify against the running system.
Because `osFileSize` is `-1` for a full package, take the expected size from the HTTP
`Content-Length` and still verify `otaMd5`.

Nothing here is version-addressable and no downgrade is offered: a version that is not
the newest of its line has no package of its own (`已是最新版本`), and the CDN refuses
listings (`AccessDenied` on `?prefix=`, `404` for guessed names). Older stock firmware,
including the 3.3.0 that the 3.4.6 delta is built from, cannot be pulled from these
servers.

### Flashing one line's package onto another phone of another line

`B651 CN` and `B651 NO_EEA_M2` are the same hardware, and a `NO_EEA_M2` phone is never
offered anything newer than 3.1.6, so the only way onto 3.4.6 is the CN package. That
package was compared, partition by partition, with the
`B651_NO_EEA_M2_3.1.6_User_20260306_SMR_FW.zip` factory image and with a phone running
it: one board configuration in `lk` (`k6877v1_64_k419`), the same AVB public keys, an
identical `vbmeta` header so no anti-rollback index moves, the same modem build and band
database, the same APN database, the same panel overlays — and none of the partitions
that hold per-device data written, so `nvram`, `proinfo`, `sec1` and the rest keep the
IMEI, the MAC addresses and the RF calibration intact. What it costs: the update channel
becomes `B651 CN` for good, and the CN `product` image carries a much smaller Google app
set. Getting it onto a locked phone is the hard part — stock Settings has no
local-package path, there is no `recovery` partition to sideload from, and a locked
bootloader refuses `fastboot flash`.

[STOCK-CROSSFLASH-INFO.md](STOCK-CROSSFLASH-INFO.md) carries the whole comparison: the
23 partitions the payload writes with their hashes, what changes on the phone, the ways in
and their risks, the backup and rollback plan, and the commands to reproduce it all.
[STOCK-CROSSFLASH-INSTALL.md](STOCK-CROSSFLASH-INSTALL.md) is that flash written out step by
step. [`payload-parts.py`](payload-parts.py) is the tool behind it — it prints a payload
manifest and extracts images with every hash verified.

That has since been carried out, on the HiBreak Pro of [README.md](README.md): the fastboot
route — bootloader unlocked, then flashed in both of its fastboot modes — and the phone boots
3.4.6 with `ro.build.versionCode` reading `B651 CN`, the baseband string unchanged, and a
Bluetooth address identical to the one recorded before the unlock wiped `/data`. What it does
not settle is the OTA question above: with the channel now `B651 CN`, nothing has been seen
coming from `fota.bigmecloud.com` in either direction.

## System-app update query

The stock app updater sends plain JSON, without encryption or signature:

```text
POST http://ereader.bigme.vip:8081/xrzApp
Content-Type: application/json; charset=UTF-8
lang: zh_CN

{"deviceSn": "<SN>", "productModel": "B651 CN", "versionCode": "3.3.0", "versionName": "HiBreak pro"}
```

The field names do not mean what they mean in an APK:

| Field | Meaning |
| --- | --- |
| `deviceSn` | Device SN, read the same way as for the OTA query. |
| `productModel` | Stock model and channel, the same value as `osName`. |
| `versionCode` | The stock **OS version string** (`3.3.0`), not an app version code. |
| `versionName` | The stock `ro.build.versionProduct` (`HiBreak pro` on the Pro Color), not an app version name. |

The response is plain JSON: `code` (`0` on success), `msg`, and `data`, a list with one
entry per app:

| Field | Meaning |
| --- | --- |
| `appName`, `appNameEng` | Display name (Chinese, English). |
| `packageName` | Android package name. |
| `versionCode`, `versionName` | The APK's own version. The stock updater compares `versionCode` with the installed app. |
| `downloadUrl` | HTTPS APK URL. |
| `fileSize` | APK size in bytes (a string). |
| `md5` | Seen as `"0"` for every entry: no checksum is provided. |
| `forceUpdate`, `upgradeEnabled` | `"0"`/`"1"` flags. |
| `updateLog`, `updateLogEng` | Change notes (Chinese, English). |
| `productModel`, `osVersion` | Properties of the entry. `osVersion` may differ from the version you sent; it does not mean the APK is only for that OS version. |

Display names can mislead: the entry named **"Bigme OS 5.0" is the Launcher APK**
(`com.android.launcher3`), not a firmware version.

## Using the script

Requirements: Python 3 and the `openssl` command. Run `./bigme-ota.py --help` for
every option.

`--os-name`, `--os-version` and, for the app list, `--product-name` have no defaults:
pass the values of your phone's **stock** firmware. The GSI may report spoofed or
different build properties. Take them from the stock system or a stock backup. The examples use the HiBreak Pro Color (CN) on stock 3.3.0. Check your own phone rather than copying them: the HiBreak Pro Color seen in October 2026 reported `ro.build.versionCode` `B651 NO_EEA_M2` at stock 3.1.6, not `B651 CN` (see [Firmware lines](#firmware-lines)).

Query both OTA servers. The script asks for the SN without echoing it:

```sh
./bigme-ota.py --os-name 'B651 CN' --os-version 3.3.0
```

Ask for the **full** package instead of the delta by sending a version older than the
line's delta chain, for example `0.0.0` (see [Full packages](#full-packages)). The
server still only ever offers the newest build of the line:

```sh
./bigme-ota.py --os-name 'B651 CN' --os-version 0.0.0
```

Query the system-app list, or both lists, with the SN from a file containing only
the SN:

```sh
./bigme-ota.py --query apps --os-name 'B651 CN' --os-version 3.3.0 --product-name 'HiBreak pro' --sn-file my-sn.txt
./bigme-ota.py --query all --server cn --os-name 'B651 CN' --os-version 3.3.0 --product-name 'HiBreak pro' --sn-file my-sn.txt
```

Send the requests from the phone's own network with `--transport adb`. This runs
`curl` on the phone through `adb exec-out` and passes the request on stdin; nothing
is written to the phone. The phone needs `curl` and authorized ADB. Use `--adb-serial`
to pick a device and `--adb` for another adb binary. The adb transport keeps only the
response body, not the HTTP status.

Work offline:

```sh
# Write the encrypted OTA request and a summary, send nothing.
./bigme-ota.py --prepare-only --os-name 'B651 CN' --os-version 3.3.0 --sn-file my-sn.txt
# Decrypt a saved raw OTA response. Needs no SN and no network.
./bigme-ota.py --decode-response bigme-ota-<time>/cn-response.b64
```

Each run writes a new directory, `./bigme-ota-<UTC time>/` by default (`--output-dir`
picks another path that must not exist yet). It is readable only by you:

| File | Contents |
| --- | --- |
| `request-info.json` | Endpoints, fields, language and transport. The SN is replaced by `<omitted>`. |
| `request.b64` | The encrypted OTA request body. It still contains your SN; keep it private. |
| `cn-response.b64`, `usa-response.b64` | Raw OTA responses, kept even if they do not decrypt. |
| `cn-response.json`, `usa-response.json` | Decrypted OTA responses with every field. |
| `apps-response.raw`, `apps-response.json` | Raw and parsed app list. |
| `*-transport.json` | HTTP status (`null` with the adb transport). |
| `response.json` | Output of `--decode-response`. |

The plain-JSON app request contains the SN, so it is sent but never saved. The script
sends one request per endpoint, does not retry, does not follow redirects, and times
out after 25 seconds (`--timeout`). `--lang` overrides the `lang` header (default
`zh-CN` for OTA, `zh_CN` for the app list). It exits 0 when every response was
received and parsed, even if the server offers nothing. It exits 1 on a transport,
decryption or HTTP error, or an app list with `code` other than 0, and 2 on bad
arguments. When one server fails, the script still queries the others.

## Downloading and verifying a package

The script prints the URL; download it yourself. Check the size and MD5 against
`osFileSize` and `otaMd5`, then test the archive:

```sh
curl -fL -o B651_CN_3.4.6-3.3.0-inc-3c88ac9adf72de3986f30ee21fba2e99.zip \
  'https://bdboscn.bigme.vip/phone/b651/B651CN/B651_CN_3.4.6-3.3.0-inc-3c88ac9adf72de3986f30ee21fba2e99.zip'
stat -c %s B651_CN_3.4.6-3.3.0-inc-*.zip     # 127460552
md5sum B651_CN_3.4.6-3.3.0-inc-*.zip         # 3c88ac9adf72de3986f30ee21fba2e99
sha256sum B651_CN_3.4.6-3.3.0-inc-*.zip
unzip -t B651_CN_3.4.6-3.3.0-inc-*.zip       # checks every entry's CRC
```

A matching MD5 and a clean `unzip -t` show that the download is complete and matches
what the server announced. They do not verify Bigme's OTA signature. App entries have
no usable MD5 (`"0"`), so compare their size, and the SHA-256 below where it is known.
Full packages report `osFileSize` `-1`, so compare their size with the HTTP
`Content-Length` instead. Both 3.4.6 packages are signed by the same OTA certificate:
`CN=Sunritel, O=Sunritel, L=BaoAn, ST=Shenzhen, C=CN`, valid 2023-02-24 to 2050-07-12,
SHA-256 fingerprint
`0AFB2F4125D78327BFE4FCB41FE7330B7D4A758398E1434B9A6093D5731900C6`.

## Known downloads

These official URLs have been returned by the servers above. The size and checksums
are from complete downloads. The servers may move or remove the files.

| File | What it is | Size (bytes) | Checksums |
| --- | --- | --- | --- |
| [B651_CN_3.4.6-OTA-FULL-7b21b7069c315b7c9b02472420c542a7.zip](https://bdbos.bigme.vip/phone/b651/B651CN/B651_CN_3.4.6-OTA-FULL-7b21b7069c315b7c9b02472420c542a7.zip) | Stock firmware 3.4.6 for `B651 CN`, **full** A/B OTA, no `pre-build` in its metadata. Offered when the version sent is older than the delta chain (`--os-version 0.0.0`). `Last-Modified: 2026-09-01`. | 2,568,381,284 | MD5 `7b21b7069c315b7c9b02472420c542a7`, SHA-256 `e4e937495166d1d31dcebcc4dcafbd8c41cd2b0289ba0ed227f230fe2543dcee` |
| [B651_CN_3.4.6-3.3.0-inc-3c88ac9adf72de3986f30ee21fba2e99.zip](https://bdboscn.bigme.vip/phone/b651/B651CN/B651_CN_3.4.6-3.3.0-inc-3c88ac9adf72de3986f30ee21fba2e99.zip) | Stock firmware 3.4.6 for `B651 CN`, incremental A/B OTA from 3.3.0. Offered by both the CN and USA servers (identical files). | 127,460,552 | MD5 `3c88ac9adf72de3986f30ee21fba2e99`, SHA-256 `60eef33e073d6b616b4779a746828826dea2157824af3006a88fc5696e416539` |
| [[B651]Settings_v2.8.7_release_2026-08-26.apk](https://bame.bj.bcebos.com/xrzapp/b651/%5BB651%5DSettings_v2.8.7_release_2026-08-26.apk) | Stock Settings `com.android.settings` 2.8.7 (20807), from the app list for `B651 CN` 3.3.0 | 335,220,897 | SHA-256 `e0530deee81c1f6c6c7bc74ef3c9e898fc066976f488aeae5e23b73cabf9f908`; signing certificate SHA-256 `18a2f0efbaf678e3635df0009645a8b2001a82ec5c729afcd79216fcad88887d` (the same as stock Settings 2.7.6) |
| [[Phone]_Launcher3_v1.7.12_release_2026-08-19.apk](https://bame.bj.bcebos.com/xrzapp/b651/%5BPhone%5D_Launcher3_v1.7.12_release_2026-08-19.apk) | Stock launcher `com.android.launcher3` 1.7.12 (10712), listed as "Bigme OS 5.0" | 42,257,925 (listed) | not downloaded |
| [xReaderProV31_V7.1.5.apk](https://bame.bj.bcebos.com/xrzapp/B651CN/xReaderProV31_V7.1.5.apk) | xReaderPro `com.xrz.xreaderV3` 7.1.5 (31) | 121,236,484 (listed) | not downloaded |
| [Phone_BigmeGPT_v1.1.7_release_2026-07-06.apk](https://bame.bj.bcebos.com/xrzapp/B651CN/Phone_BigmeGPT_v1.1.7_release_2026-07-06.apk) | BigmeGPT `com.xrz.ai` 1.1.7 (7) | 17,146,059 (listed) | not downloaded |

"Listed" sizes come from the app list only; those files have not been downloaded and
checked.

Two full packages of the older 3.1.6 builds were also returned by the servers, for the
other B651 lines; neither has been downloaded, so only the server's MD5 is known:

- `https://bdbos.bigme.vip/phone/b651/no_eea_m2/B651_NO_EEA_M2_3.1.6-OTA-FULL-875b1e5d1b0c5d95ff679618bad01455.zip`
  (MD5 `875b1e5d1b0c5d95ff679618bad01455`)
- `https://bdbos.bigme.vip/phone/b651/eea_m2/B651_EEA_M2_3.1.6-OTA-FULL-2b98c905b37c86802e951d05b09cfac5.zip`
  (MD5 `2b98c905b37c86802e951d05b09cfac5`)

### Factory (SP Flash Tool) images

Factory images in DA form are a different thing from these OTA packages: they carry a
scatter file, whole-partition images and a `super.img`, and go in with SP Flash Tool or
mtkclient instead of `update_engine`. Only one for the B651 is known, and it is not on the
OTA storage:

| File | Line | Size (bytes) | Location |
| --- | --- | --- | --- |
| `B651_NO_EEA_M2_3.1.6_User_20260306_SMR_FW.zip` | `B651 NO_EEA_M2` | 6,784,064,175 | `https://bj.bcebos.com/bos-dawoyuji/fw/B651_NO_EEA_M2_3.1.6_User_20260306_SMR_FW.zip` |

That bucket refuses listings — `GET /?prefix=` answers `403` on both
`bj.bcebos.com/bos-dawoyuji/` and `bos-dawoyuji.bj.bcebos.com` — while objects under `fw/`
read fine, so a file can only be fetched by its exact name. Probing the pattern of the one
known name turns up nothing else: `B651_CN_*`, `B651CN_*`, `B651 CN_*` and `B651_EEA_M2_*`
at versions 3.1.6, 3.3.0 and 3.4.6 across the plausible build dates (February–March and
August–October 2026) all answer `404`, and so do the same names on the OTA host under
`bdbos.bigme.vip/phone/b651/…`, which carries only `-OTA-FULL-` and `-inc-` packages. Bigme
publishes DA-form firmware openly only for other products: the single firmware page on the
shop, `store.bigme.vip/pages/firmware-for-b251-monitor-and-all-in-one-pc`, points at Google
Drive folders for the B251 monitor.

So there is no URL to try for a CN DA image — it comes from Bigme support, quoting model
and SN, the way the NO_EEA one apparently did. It is also not needed for this phone:
[STOCK-CROSSFLASH-INSTALL.md](STOCK-CROSSFLASH-INSTALL.md) pulls the CN images out of the
full OTA with [`payload-parts.py`](payload-parts.py) and writes them to the partitions straight
over fastboot, and [STOCK-CROSSFLASH-INFO.md](STOCK-CROSSFLASH-INFO.md) records what the
factory image would restore.

### Limits

- **The 3.4.6-3.3.0 package is incremental.** Its A/B payload patches the exact stock
  3.3.0 partitions and checks their hashes, so it applies only to an unmodified stock
  3.3.0 `B651 CN` phone. It is not a full image and cannot restore a phone. The package
  metadata has the same pre- and post-build fingerprint, so the 3.3.0 → 3.4.6 relation
  rests on the server response and the file name.
- **The full package is the way onto 3.4.6.** `B651_CN_3.4.6-OTA-FULL-...zip` declares
  no `pre-build`, so `update_engine` has no source hash of the running system to check;
  it is the package to use from another stock version and the one to restore stock with.
  Neither package has been installed here, so this rests on the package metadata alone.
- **Neither package keeps the GSI.** A GSI `system` does not match the delta's source
  hashes, and either package writes a complete stock 3.4.6 system to the other slot and
  boots it: their payload metadata names system, system_ext, product and vendor
  alongside boot, dtbo, vbmeta, vbmeta_system, vbmeta_vendor, preloader, scp, sspm and
  tee (the incremental also names odm), so the phone ends up stock, not GSI. To run
  3.4.6 firmware, go back to stock, apply the full 3.4.6 package there, then flash the
  GSI again. That path has not been tested here.
- **An older stock version cannot be fetched.** A line publishes only its newest build
  and never a downgrade, so 3.3.0, the base the 3.4.6 delta was built on, has no
  reachable package of its own, and `B651 NO_EEA_M2` and `B651 EEA_M2` stop at 3.1.6. A
  factory image of an older version comes from Bigme support in the
  `B651_NO_EEA_M2_<version>_User_<date>_SMR_FW.zip` SP Flash Tool form, not from these
  servers.
- **Firmware cannot be downgraded.** The 3.4.6 release notes say so.
- **The stock APKs need the stock system.** They are signed with Bigme's key and
  depend on the XRZ stock framework, so they cannot replace this GSI's apps.
- Starting a download in stock Settings is not a "download only" mode: when it
  finishes, the stock client goes on to apply the update. Download with the URL on a
  computer instead.

## Credits

The OTA protocol and keys follow
[marek-vybiral/bigme-ota-client](https://github.com/marek-vybiral/bigme-ota-client/tree/db50aa682196108ed1b42a7d231c39885b8fa191)
(Unlicense), commit `db50aa6`. They were checked independently against the official
B651 CN Settings 2.8.7 client. See [NOTICE](NOTICE).
