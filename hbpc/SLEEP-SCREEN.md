# E-Ink sleep screen

The E-Ink panel keeps the last frame shown before the display turns off. With Android
always-on display (AOD) off, that frame is SystemUI's dozing keyguard. Stock Android
draws it on black, with the small clock and the AOD notification icons. On this GSI it is
an opaque page chosen in the E-Ink app: a picture (default), a clock that updates while
asleep, the lock screen as it was, or your own image.

Patches (feature `eink-sleep-screen`):
[`shared/frameworks_base/0025-eink-picture-sleep-screen.patch`](patches/hibreak/shared/frameworks_base/0025-eink-picture-sleep-screen.patch)
(SystemUI and the dream manager, `shared`),
[`device/vendor_a9_services/0005-sleep-screen-setting.patch`](patches/hibreak/device/vendor_a9_services/0005-sleep-screen-setting.patch)
(E-Ink app, `device`) and
[`defaults/device_phh_treble/0012-eink-doze-on-sleep.patch`](patches/hibreak/defaults/device_phh_treble/0012-eink-doze-on-sleep.patch)
(product overlay, `defaults`). Everything in SystemUI is gated by the existing E-Ink
keyguard policy `bool/config_einkKeyguard` (see [LOCKSCREEN.md](LOCKSCREEN.md)). Without
that policy SystemUI behaves as stock.

## Modes

E-Ink settings → Advanced → Sleep screen. The choice is stored per user as
`Settings.Secure` `hibreak_sleep_screen_mode`. Missing or unknown values show the picture.

| Choice | Value | What the panel keeps |
| --- | --- | --- |
| Picture · Logo and lock time (default) | `picture` | White page, LineageOS logo, "Locked at 21:37" ("锁定于 21:37"), the AOD notification icons in black near the top. |
| Clock · Updates every minute / 5 minutes / 15 minutes | `clock_1`, `clock_5`, `clock_15` | White page with a large black time and the date, redrawn while asleep. No notification icons. |
| Lock screen · As shown before sleep | `lockscreen` | The lock screen exactly as it was drawn just before going to sleep: clock, date, notifications, status icons, lock icon. No updates. |
| Custom image | `custom` | Your image, fitted (whole image visible) on white, optionally with "Locked at 21:37" under it. No notification icons. |

The time in "Locked at" is when the device started going to sleep, in the system
12/24-hour format.

In every mode the page is drawn above every other keyguard view (clock, smartspace,
weather, status, shortcuts and views added or rebuilt later), so nothing of the dozing
keyguard shows through. Only in picture mode are the AOD notification icons raised above
the page. In lock screen mode the captured lock screen already contains the notifications.

The page appears as soon as the device starts going to sleep (or when the keyguard
starts the transition into the dozing state, whichever is first) and is removed as soon
as the device starts waking. The display turns off only after the page is on the panel.
Wake, unlock, fingerprint and the PIN screen are unchanged. Animations stay off.

### Clock

The time is redrawn at every wall-clock boundary of the interval (for example 21:40,
21:45, 21:50 with 5 minutes), so the shown time is exact when it is drawn and at most one
interval old. Changing the time or the time zone redraws at once and reschedules.

Each update: a wakeup alarm at the boundary; the page redraws; the display is turned on
(the same doze display state as during the screen-off wait, front light at the doze level);
SystemUI waits until the redrawn page is presented plus the settle time (400 ms) and then
turns the display off again. The update is bounded by
`integer/config_einkSleepRefreshTimeoutMs` (3000 ms from turning the display on). A wake
lock is held only for that window; between updates nothing keeps the CPU awake. Waking
the device cancels the pending update and the alarm.

**Battery:** every update wakes the CPU from suspend and powers the panel path for about
0.5-1 s (display power-on, one frame, 400 ms settle, display off). That is 60 wakeups an
hour with "every minute", 12 with 5 minutes and 4 with 15 minutes, against none for the
other modes. Expect the 1-minute clock to cost noticeably more standby battery than the
picture; 15 minutes is the recommended interval. Measure with
`adb shell dumpsys batterystats` (wakeup alarm `EinkSleepScreen:clock`; the update
holds SystemUI's partial wake lock `Doze`) if in doubt.

### Lock screen

At the very start of going to sleep, before SystemUI reacts to it, SystemUI captures its
own notification shade window (the keyguard) with a SurfaceFlinger layer capture and
shows that capture as the page. The panel therefore keeps exactly the frame that was on
screen. On this GSI the lock screen is the static black-on-white keyguard; the wallpaper
is covered by white paper there too.

This works when the lock screen was shown and settled when sleep started (power key or
timeout on the lock screen). When the device goes to sleep directly from an app, or from
the PIN screen, there is no lock screen frame to keep: the keyguard is drawn for the
first time already dozing. Those sleeps show the picture instead (logged as a fallback).
The capture stays in memory only and is dropped on wake.

### Custom image

Choose Custom image, then pick an image in the document picker. The E-Ink app decodes it,
scales it down to fit the display (portrait) and keeps its own PNG copy in its
device-protected storage, so the sleep screen keeps working if the original file is moved,
deleted or its permission is revoked, and also before the first unlock. "Image" picks a
new one. "Show lock time" (default on) adds "Locked at 21:37" under the image.

SystemUI reads the copy through the E-Ink app's read-only content provider
`content://net.dianqk.hibreak.eink.sleepscreen/image`, which requires the signature
permission `android.permission.STATUS_BAR_SERVICE` (SystemUI). The provider hands over a
read-only file descriptor; no file is shared on disk and no SELinux policy is added.
SystemUI keeps the decoded image ready (reloaded when the image or the mode changes, and on
user switch). If the image is missing or cannot be read, the picture is shown and the
reason is logged.

## Sleep sequence

The E-Ink panel needs about 250 ms after the composer commits a frame to finish the
update, and stock Android turns the display off 20-110 ms after going to sleep. Without
a wait the update is cut short and the panel keeps the previous image. So on this device:

1. Going to sleep: the page is shown.
2. The framework starts SystemUI's doze service on every sleep, also with all ambient
   display features off (`bool/config_einkDozeOnSleep`, product overlay). SystemUI
   controls the screen off: the display stays on while the doze service starts.
3. SystemUI waits until a frame with the visible page has been presented
   (SurfaceFlinger transaction completed callback and present fence), then a settle time
   (`integer/config_einkSleepSettleMs`, 400 ms), and only then requests the display off.
4. The wait never keeps the device awake: after `integer/config_einkSleepTimeoutMs`
   (1500 ms) from its start the display turns off anyway. Waking up during the wait
   cancels it.

While the screen is off the device is in the DOZING state (doze service running, display
OFF) instead of ASLEEP. With all ambient display features off the doze service does not
pulse, show AOD or listen to doze gestures; it only holds the screen-off request and, in
clock mode, schedules the updates. The CPU still suspends: the doze service holds no wake
lock with the display off.

## Changes

- `EinkSleepScreenSection` (keyguard blueprint section, default and split-shade): the
  page, shown only in the keyguard DOZING state (screen off without AOD), with
  translationZ 1000 (kept through constraint set re-application) above all keyguard views.
- `EinkSleepScreenRefresher` (doze machine part): clock-mode updates while dozing.
- `KeyguardService.onStartedGoingToSleep`: calls the page first, for the lock screen
  capture.
- Scrims: in the low-power AOD/OFF scrim states with AOD off, the scrim behind the
  keyguard is opaque white and the front and notification scrims are transparent,
  instead of opaque black. No scrim animation.
- Light reveal scrim: its screen-off end state is white instead of black.
- AOD notification icons: black, without the white doze tint.
- Burn-in protection offsets are zero (no burn-in on E-Ink; shifting would only move
  static content between refreshes).
- Screen-off wait: SystemUI controls the screen off with AOD off; the doze screen state
  requests OFF after the page is presented and settled (bounded by the timeout). Frames
  drawn while the display is off are not counted as presented.
- Doze: pulse and AOD state requests are dropped while every ambient display feature is
  off. If the user enables an ambient feature, doze behaves as stock.
- Framework: the dream manager returns the doze component on sleep with ambient display
  off when `config_einkDozeOnSleep` is set.
- E-Ink app: the six choices, the custom image picker and copy, "Show lock time"
  (`Settings.Secure` `hibreak_sleep_screen_image_time`, 1/0) and the image provider. The
  stored image's version token is `hibreak_sleep_screen_image`.

## Limits

- The wait is bounded: if the page is not presented within 1.5 s (for example the
  keyguard is not shown because of a lock delay), the display turns off with whatever
  the panel shows. A clock update that is not presented within 3 s turns the display off
  again and the next update follows at the next boundary.
- Sleep enters DOZING instead of ASLEEP, and the doze service starts and stops on every
  sleep/wake. Watch standby drain after updating; the kill switch below restores the
  previous behaviour.
- Clock updates need the doze service: with the kill switch off the clock is drawn once
  when going to sleep and not updated.
- Lock screen mode needs a lock screen that was shown when sleep started (see above).
- AOD itself is unsupported on this device and stays off. If it is turned on anyway,
  the light reveal and icons stay white/black but the page and scrim changes do not
  apply (the keyguard is then in the AOD state, not DOZING).
- Ambient pulsing (new-notification wake) keeps stock scrims.

## Checking on the device

```sh
adb logcat -s EinkSleepScreen
# doze on sleep: component=com.android.systemui/.doze.DozeService   (system_server)
# shown locked-at=21:37 mode=picture uptime=123456
# screen-off control: waiting (page shown)
# page presented +60 ms
# settled, releasing screen off +450 ms
# hidden                                                            (on wake)
```

Mode-specific lines:

```sh
# clock:      shown locked-at=21:37 mode=clock every=5min uptime=...
#             clock: every 5 min
#             refresh (tick): display on
#             refresh: page presented +180 ms
#             refresh: settled, releasing screen off +590 ms
#             clock: stopped after 12 updates                       (on wake)
# lockscreen: lock screen captured 824x1648 in 25 ms
#             shown ... mode=lockscreen ...
#             shown ... mode=picture (fallback: lock screen not shown when going to sleep
#                   (keyguard GONE, to GONE)) ...                   (sleep from an app)
# custom:     custom image loaded 824x1236                          (on choosing/boot)
#             shown ... mode=custom ...
#             shown ... mode=picture (fallback: custom image unreadable (...)) ...
```

`timeout, releasing screen off +1500 ms` instead of `settled` means the page was not
presented in time. In the full log the composer `[DRMDEV] [normal commit]` for the page
comes before `settled`, and SurfaceFlinger `Setting power mode 0` after it. Clock alarms
are visible in `adb shell dumpsys alarm | grep EinkSleepScreen`.

## Kill switch

`persist.debug.hibreak.sleep_screen_wait=false` restores the previous sleep path: no
doze service with ambient display off, no screen-off wait and no clock updates (the page
is still drawn, but the display may turn off before the panel shows it). The framework
reads it on every sleep; SystemUI on its next keyguard or configuration change, so reboot
after changing it.

```sh
adb shell setprop persist.debug.hibreak.sleep_screen_wait false   # then reboot
```

## Revert

Choose Picture to drop the clock updates, capture and image. To remove the feature, drop
the four patches from `patches/hibreak/series.json` (or set `bool/config_einkKeyguard` to
false, which also disables the static lockscreen, and `bool/config_einkDozeOnSleep` to
false).
