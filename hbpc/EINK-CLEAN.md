# E-Ink ghost cleaning

How the GSI drives the XRZ composer's full-screen cleans on HiBreak Pro Color.

## Clean frequency after user input

Patches (feature `xrz-anti-ghosting`, category `device`):
[`device/frameworks_base/0001-xrz-check-commit-pulse.patch`](patches/hibreak/device/frameworks_base/0001-xrz-check-commit-pulse.patch),
[`device/system_sepolicy/0001-xrz-check-commit-property.patch`](patches/hibreak/device/system_sepolicy/0001-xrz-check-commit-property.patch),
[`device/vendor_a9_services/0003-reading-scene-clean-frequency.patch`](patches/hibreak/device/vendor_a9_services/0003-reading-scene-clean-frequency.patch).

The vendor composer runs a full clean after *N* large updates (at least 40% of the
screen, at least 800 ms apart), where *N* is the per-app "Ghost-clean interval"
(`vendor.xrz.clean_frequency`, 0 = off). It counts only while
`vendor.xrz.check_commit` is 1. The stock system sets that property for 800 ms after
each touch or button press; this GSI never did, so the interval had no effect.

- `PowerManagerService` now sets `vendor.xrz.check_commit=1` on touch or button user
  activity and back to `0` 800 ms after the last one, on its own thread, writing only on
  changes. Active only when `ro.bigme.force_client_composition` is true.
- SELinux: the property has its own type `hibreak_xrz_check_commit_prop`
  (system-restricted): `system_server` may set it, the vendor composer may read it.
  The broader `vendor_xrz_prop` is not widened.
- The E-Ink app's Reading scene now sets a clean interval of 8 (other scenes 0).
  Apps that had Reading selected before show "Custom" until Reading is chosen again.

Check on the device:

```sh
adb shell getprop -Z vendor.xrz.check_commit   # hibreak_xrz_check_commit_prop
adb shell getprop vendor.xrz.check_commit      # 1 while touching, 0 ~0.8 s later
adb logcat | grep -E 'threshold=|dirty_area='  # composer counting toward a clean
```

Revert: remove the three patches; the interval then has no effect again.

## Manual full clear (GC16)

Patches (feature `eink-gc16-clear`, category `device`):
[`device/frameworks_native/0001-one-shot-gc16-clear.patch`](patches/hibreak/device/frameworks_native/0001-one-shot-gc16-clear.patch),
[`device/vendor_a9_services/0004-gc16-clear-actions.patch`](patches/hibreak/device/vendor_a9_services/0004-gc16-clear-actions.patch).

The composer reads `vendor.xrz.force_global_refresh_mode` as a one-shot request: a
nonnegative waveform applies to the next commit, after which the composer writes `-1`.
SurfaceFlinger transaction `1113` (system UID only, XRZ panel only; argument `4` =
GC16, the default, or `180` = Regal) sets it, repaints the whole screen and, after the
next presented frame (or 1 s if none), releases a request the composer did not consume.
The clear key action and the Clear Screen tile use it through the E-Ink app's worker
thread. The previous black/white overlay frames (drawn in the app's waveform) and the
daemon's `r` and `c` commands (set the property for 200 ms without a repaint, or select
Regal) are removed.

The composer suppresses a GC16 within 400 ms of the previous one, so rapid repeated
presses produce one clear.

```sh
adb logcat -s SurfaceFlinger | grep EinkClear   # "armed mode 4" then "consumed (presented)"
adb shell getprop vendor.xrz.force_global_refresh_mode   # -1 when idle
```
