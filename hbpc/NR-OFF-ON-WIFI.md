# No 5G while on Wi-Fi

Feature id `nr-off-on-wifi`, category `device`:
[patch](patches/hibreak/device/frameworks_opt_telephony/0005-no-nr-while-wifi-is-default.patch)
to `frameworks/opt/telephony`.

## Why

In testing on the HiBreak Pro Color, on 5G standalone (SA) with Wi-Fi connected,
incoming calls stopped reaching the phone after a few idle minutes: the modem showed no
sign of the call at all. With Wi-Fi off, or on LTE, incoming calls kept arriving, also
with the screen off for a long time. The cause has not been established.

## What it does

- While Wi-Fi has been Android's default network for 10 seconds, the phone does not use
  5G (NR) and stays on LTE (4G). This covers 5G SA and 5G NSA, on every SIM.
- As soon as Wi-Fi is no longer the default network (Wi-Fi off or out of range), 5G is
  allowed again at once; in testing the modem was back on 5G SA about a second later.
- Neither change is made during a call: it waits until no call is active.
- Your network preference in Settings is not changed and still applies: the feature only
  removes 5G from what is allowed while on Wi-Fi. Nothing is stored, so after a reboot
  the phone starts with 5G allowed until Wi-Fi is connected again.
- It is not applied when the remaining allowed types would not include LTE, and it does
  not change the network during an emergency call or emergency callback mode.
- The radio log (`adb logcat -b radio`) shows `HBPC_NR_WIFI` once per change, with no
  network names.

## Turning it off

As root on a userdebug build:

```sh
adb shell setprop persist.radio.hibreak_nr_off_on_wifi false
```

5G is allowed again at the next default network update (Wi-Fi updates its state often;
toggling Wi-Fi forces one). Set it back to `true`, or remove it, to turn the feature on.

## Limits

- On Wi-Fi the phone uses LTE, so a 5G-only cell or a 5G-only plan gives no mobile
  service while Wi-Fi is the default network.
- Mobile data used while Wi-Fi is the default (for example by apps that request mobile
  data) runs over LTE.
- Only the system default network counts. While Android keeps mobile data as the
  default network (for example when a Wi-Fi network has no internet and Android switched
  back to mobile data), 5G stays allowed.

See also [VoLTE with the MediaTek IMS service](MTK-VOLTE.md).
