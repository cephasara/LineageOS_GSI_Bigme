# Out-of-service radio recovery

Patch: [`device/frameworks_opt_telephony/0004-recover-out-of-service-radio.patch`](patches/hibreak/device/frameworks_opt_telephony/0004-recover-out-of-service-radio.patch)
(category `device`, feature `wwan-oos-radio-recovery`).

## Problem

A SIM on this phone can stay out of service for hours: the modem reports voice and
data as not registered and keeps rejecting the attach (MediaTek `+ECCAUSE: 112`),
although it still measures strong cells of the SIM's own network. Turning airplane
mode on and off always brings service back. The stock firmware has no automatic
recovery for this.

## What it does

`HiBreakOosRadioRecovery` (in `frameworks/opt/telephony`) watches each SIM separately
and does what airplane mode does for the radio, for that SIM only.

A SIM is considered stuck while all of these hold:

- the radio is on and should be on (no airplane mode, no other radio-off reason, the
  phone is not shutting down);
- the SIM is loaded and has an active subscription;
- cellular (WWAN) voice and data are both not registered. Emergency-only counts as not
  registered; Wi-Fi calling or data over Wi-Fi does not hide the outage.

When a SIM becomes stuck, a timer starts. It is a non-wakeup alarm: it never wakes the
phone, and runs at the next wakeup once it is due.

| Radio cycle | Waits after the SIM became (or stayed) stuck |
| --- | --- |
| first | 5 min |
| second | 10 min |
| third | 30 min |
| each later one | 60 min |

The waits start again from 5 min as soon as voice or data registers on that SIM.

When the timer fires, every condition is checked again, and in addition:

- no call on any SIM (ringing, active or held, including VoLTE/Wi-Fi calls), no
  emergency call, emergency callback mode or emergency SMS mode;
- no network scan (manual network search) started in the last 10 minutes and not
  stopped;
- the latest cell list (one request, answered from cache if a request was just made)
  contains a cell of the SIM's home network (the SIM's MCC/MNC, EHPLMN or HPLMN list).
  In a real dead zone, the radio is not cycled.

If any check fails, the cycle is skipped and the timer starts again with the same wait.
Otherwise the radio of that SIM is powered off the same way Android's data stall
recovery restarts the radio (data is torn down normally first) and, because the radio is
still meant to be on, Android powers it on again right away. The other SIM, airplane
mode, user settings, network selection and the modem configuration are not touched.

Only the Bigme HiBreak (vendor manufacturer `Bigme`, model `HiBreak`, platform
`mt6877`) runs this; other devices are unaffected.

## Logs and status

Radio log buffer, tag `HBPC_OOS_RECOVERY`:

```
phone 1 WWAN voice and data not registered, arm 300s (step 0)
phone 1 skip: no_home_cell
phone 1 cycle radio #1 after step 0
phone 1 cancel: radio_off
phone 1 registered, reset backoff (step 1)
```

Skip reasons: `registered`, `disabled`, `radio_off`, `radio_not_desired`, `shutdown`,
`sim_not_loaded`, `no_sub`, `call`, `emergency`, `network_scan`, `no_home_cell`.

The non-persistent property `ril.hibreak.oos_recovery.<phoneId>` holds
`<last action> <cycles> <uptime-ms>` for the last reset, skip or cycle, for example
`cycle 1 8123456` or `skip:call 1 8423456`. It is cleared on reboot.

```sh
adb shell getprop | grep hibreak.oos_recovery
adb logcat -b radio -s HBPC_OOS_RECOVERY
```

## Disable

```sh
setprop persist.radio.hibreak_oos_recovery false   # applies to new decisions
setprop persist.radio.hibreak_oos_recovery true    # or remove it to re-enable
```

## Limits

- It treats the symptom: each cycle drops data on that SIM for a few seconds and does
  not fix why the modem stopped attaching.
- A network scan is assumed to run for up to 10 minutes after it starts unless it is
  stopped; a radio cycle can wait that long after a manual network search.
- Detection relies on the modem's cell list; if the modem reports no home cell while
  stuck, nothing happens.
