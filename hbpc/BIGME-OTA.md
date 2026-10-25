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
(`bdboscn.bigme.vip` for firmware, `bame.bj.bcebos.com` for apps).

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
| `osName` | Stock model and channel, for example `B651 CN` for the HiBreak Pro Color (CN). |
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
| `msg` | Server note, in Chinese. Seen: `所有设备可升级,差分包升级` ("all devices may upgrade, incremental package") with an offer, and `禁止升级` ("upgrade not allowed") without one. `禁止升级` gives no reason. The same request once got `禁止升级` and weeks later an offer. |
| `otaUrl` | HTTPS download URL of the package, empty without an offer. |
| `otaMd5` | MD5 of the package (lowercase hex). The package file name also ends in it. |
| `osFileSize` | Package size in bytes. |
| `osVersion` | Target OS version, for example `3.4.6`. |
| `wholePackage` | `false` for an incremental package, which needs the exact stock version you sent. `true` would be a full package; none has been seen. |
| `upgradeMsg` | Release notes as HTML, in Chinese. |
| `forceUpgrade`, `status`, `taskId` | Seen as `0`, `0` and `""`. |

Only one package has been seen per request. The 3.4.6 release notes say that the
rollout is staged ("if no firmware is found, try again the next day").

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
different build properties. Take them from the stock system or a stock backup. The examples use the HiBreak Pro Color (CN) on stock 3.3.0.

Query both OTA servers. The script asks for the SN without echoing it:

```sh
./bigme-ota.py --os-name 'B651 CN' --os-version 3.3.0
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

## Known downloads

These official URLs have been returned by the servers above. The size and checksums
are from complete downloads. The servers may move or remove the files.

| File | What it is | Size (bytes) | Checksums |
| --- | --- | --- | --- |
| [B651_CN_3.4.6-3.3.0-inc-3c88ac9adf72de3986f30ee21fba2e99.zip](https://bdboscn.bigme.vip/phone/b651/B651CN/B651_CN_3.4.6-3.3.0-inc-3c88ac9adf72de3986f30ee21fba2e99.zip) | Stock firmware 3.4.6 for `B651 CN`, incremental A/B OTA from 3.3.0. Offered by both the CN and USA servers (identical files). | 127,460,552 | MD5 `3c88ac9adf72de3986f30ee21fba2e99`, SHA-256 `60eef33e073d6b616b4779a746828826dea2157824af3006a88fc5696e416539` |
| [[B651]Settings_v2.8.7_release_2026-08-26.apk](https://bame.bj.bcebos.com/xrzapp/b651/%5BB651%5DSettings_v2.8.7_release_2026-08-26.apk) | Stock Settings `com.android.settings` 2.8.7 (20807), from the app list for `B651 CN` 3.3.0 | 335,220,897 | SHA-256 `e0530deee81c1f6c6c7bc74ef3c9e898fc066976f488aeae5e23b73cabf9f908`; signing certificate SHA-256 `18a2f0efbaf678e3635df0009645a8b2001a82ec5c729afcd79216fcad88887d` (the same as stock Settings 2.7.6) |
| [[Phone]_Launcher3_v1.7.12_release_2026-08-19.apk](https://bame.bj.bcebos.com/xrzapp/b651/%5BPhone%5D_Launcher3_v1.7.12_release_2026-08-19.apk) | Stock launcher `com.android.launcher3` 1.7.12 (10712), listed as "Bigme OS 5.0" | 42,257,925 (listed) | not downloaded |
| [xReaderProV31_V7.1.5.apk](https://bame.bj.bcebos.com/xrzapp/B651CN/xReaderProV31_V7.1.5.apk) | xReaderPro `com.xrz.xreaderV3` 7.1.5 (31) | 121,236,484 (listed) | not downloaded |
| [Phone_BigmeGPT_v1.1.7_release_2026-07-06.apk](https://bame.bj.bcebos.com/xrzapp/B651CN/Phone_BigmeGPT_v1.1.7_release_2026-07-06.apk) | BigmeGPT `com.xrz.ai` 1.1.7 (7) | 17,146,059 (listed) | not downloaded |

"Listed" sizes come from the app list only; those files have not been downloaded and
checked.

### Limits

- **The 3.4.6 package is incremental.** Its A/B payload patches the exact stock 3.3.0
  partitions and checks their hashes, so it applies only to an unmodified stock 3.3.0
  `B651 CN` phone. It is not a full image and cannot restore a phone. The package
  metadata has the same pre- and post-build fingerprint, so the 3.3.0 → 3.4.6 relation
  rests on the server response and the file name.
- **It cannot be applied over the GSI.** A GSI `system` does not match the source
  hashes. Even if it did, the update writes a complete stock 3.4.6 set (system, boot,
  vendor, vbmeta and firmware partitions) to the other slot and boots it, so the phone
  runs stock instead of the GSI. To run 3.4.6 firmware, go
  back to exact stock 3.3.0 first, update there, then flash the GSI again. That path
  has not been tested here.
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
