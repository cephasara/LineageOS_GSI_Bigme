# E-Ink display profiles and refresh rate

How the GSI drives the XRZ composer's waveforms, GPU processing and frame rate on
HiBreak Pro Color.

## Hyper: dither only for high-rate content

Patch: [`frameworks_native/0001-HiBreak-Pro-Color.patch`](patches/hibreak/frameworks_native/0001-HiBreak-Pro-Color.patch)
(`Output.cpp` `currentEinkRenderProfile()`, `SurfaceFlinger::applyEinkDisplayProfile`).

Hyper (waveform 183) can binarize the frame with an ordered 1-bit dither (GPU profile 5).
Like the stock framework, the dither runs only while the composer reports high-rate
content: `vendor.xrz.cur_fps` (the composer's average commit rate over windows of at
least 10 s) at or above `persist.vendor.xrz.fps_high` (default 50). Slower content, such
as 24-30 fps video, is sent in continuous tone and the composer chooses its own low-rate
Hyper waveform. Both properties are cached (re-read only when they change).
Hyper never applies contrast, Text ink, Paper white or Dark ink. Other profiles are
unchanged.

```sh
adb logcat -s EinkRender            # "hyper dither off (cur_fps=30 fps_high=50)" / "on"
adb shell getprop vendor.xrz.cur_fps
adb shell getprop vendor.xrz.gsi_render_profile   # Hyper: "5 0 <gray> 0 0 0"
```

## Refresh rate

Patches: [`device_phh_treble/0001-HiBreak-Pro-Color.patch`](patches/hibreak/device_phh_treble/0001-HiBreak-Pro-Color.patch),
[`vendor_a9_services/0001-HiBreak-Pro-Color.patch`](patches/hibreak/vendor_a9_services/0001-HiBreak-Pro-Color.patch).

- `persist.vendor.xrz.fps=120` (stock 3.4.6 value, was 90). The composer reads it once
  at display initialization and reports a single 120 Hz mode, so a change needs a reboot.
  A value set with `setprop` persists in `/data` and overrides the build default.
- Default render rate 40 Hz (`config_defaultRefreshRate`, 120 / 3). Each frame is a full
  GPU client composite; 40 Hz is close to the previous 45 Hz (90 / 2) at less GPU cost.
  A minimum refresh rate setting above 40 (`settings put system min_refresh_rate 60`)
  overrides it; a peak setting can only lower it.
- Hyper sets `min_refresh_rate` to `persist.vendor.xrz.fps` (default 120), as stock does,
  and restores the previous value when the app leaves Hyper.

```sh
adb shell dumpsys display | grep -E 'renderFrameRate|mDefaultRefreshRate|fps='
adb shell settings get system min_refresh_rate   # 120.0 in a Hyper app
```

## Video scene

Patch: [`vendor_a9_services/0001-HiBreak-Pro-Color.patch`](patches/hibreak/vendor_a9_services/0001-HiBreak-Pro-Color.patch)
(`ImageProfile.kt`).

The E-Ink app's Video scene follows the factory video preset: Fast (179) with auto-clean
and anti-flicker, no GPU processing. The factory preset's contrast and brightness 20
are its baseline for every app (our neutral 0), and it ignores colour enhancement in
Fast. Hyper remains a manual waveform choice. Apps that had the old Video scene
(Hyper) selected keep Hyper and show "Custom" until Video is chosen again.

Revert: restore the previous values in the patches above.

## Kill switches

Each item below has a runtime switch, a `persist.debug.hibreak.*` property (settable with
`adb shell setprop` on this userdebug build, kept across reboots). Unset means enabled;
`false` or `0` disables the item (the daemon switch is inverted: `1` restores root).

| Item | Property | Takes effect |
| --- | --- | --- |
| No ColorFade on sleep/wake | `persist.debug.hibreak.no_color_fade` | next boot |
| WebView flags | `persist.debug.hibreak.webview_flags` | at once (newly started WebView processes) |
| Composition-only damage | `persist.debug.hibreak.composition_damage` | next frame |
| Touch scroll detection | `persist.debug.hibreak.touch_scroll` | next app switch |
| IME layer flag (waveform 137) | `persist.debug.hibreak.ime_layer_flag` | next keyboard show |
| E-Ink daemon as system user (`1` = back to root) | `persist.debug.hibreak.einkd_root` | from boot completion (set, then reboot) |
| Sleep screen wait (doze on sleep, see [SLEEP-SCREEN.md](SLEEP-SCREEN.md)) | `persist.debug.hibreak.sleep_screen_wait` | reboot |

## No ColorFade on sleep/wake

Patches (feature `eink-no-color-fade`):
[`defaults/device_phh_treble/0010-disable-color-fade.patch`](patches/hibreak/defaults/device_phh_treble/0010-disable-color-fade.patch),
[`device/frameworks_base/0002-no-color-fade-property.patch`](patches/hibreak/device/frameworks_base/0002-no-color-fade-property.patch).

`config_displayColorFadeDisabled=true`: screen off/on no longer takes a screenshot and
fades it through a black cover layer. On E-Ink each such frame is a full refresh, and
the black cover could stay on the panel as the sleep image. The display simply turns
off with the last drawn frame (the keyguard or sleep screen).

```sh
adb shell dumpsys display | grep mColorFadeEnabled   # false
```

## WebView flags

Patch: [`defaults/device_phh_treble/0011-eink-webview-flags.patch`](patches/hibreak/defaults/device_phh_treble/0011-eink-webview-flags.patch)
(feature `eink-webview-flags`).

WebView on a userdebug build reads extra command-line flags from
`/data/local/tmp/webview-command-line`. After boot (and whenever the kill switch
changes), the oneshot service `hibreak_webview_flags` (user shell, SELinux domain
`hibreak_webview_flags`) writes

```
_ --disable-smooth-scrolling --disable-features=ElasticOverscroll
```

so WebView pages jump instead of animating each scroll step and overscroll. A file with
other content is treated as the user's and kept. Apps read the file when their WebView
starts, so restart an app to apply a change. Only regular (untrusted) apps can read
`/data/local/tmp`; privileged system apps using WebView keep the default behaviour.

```sh
adb shell cat /data/local/tmp/webview-command-line
adb logcat -s HiBreakWebView      # "flags written: ..." / "flags removed"
```

## Damage for composition-only changes

Patch: [`device/frameworks_native/0002-composition-only-damage.patch`](patches/hibreak/device/frameworks_native/0002-composition-only-damage.patch)
(feature `eink-composition-damage`).

Even with forced client composition, the XRZ composer decides which part of the panel to
update from the layers' surface damage. When a toast, popup or scrim disappeared (or a
layer moved or faded), the layers underneath had no new buffer and sent empty damage, so
the composer could skip the update and leave the old pixels on the panel.

SurfaceFlinger now computes the composition-only dirty region: the frame's dirty region
minus the visible area of every layer that has new content. An unchanged buffer layer
that shows part of it sends that part as damage, mapped into buffer coordinates through
its display frame, source crop and buffer transform. Layers with new content keep their
own (possibly partial) damage, so a launcher redraw does not damage the wallpaper.

```sh
adb logcat -s SurfaceFlinger | grep EinkDamage   # at most one line per 5 s
```

## Touch scroll detection

Patch: [`device/vendor_a9_services/0006-touch-scroll-detection.patch`](patches/hibreak/device/vendor_a9_services/0006-touch-scroll-detection.patch)
(feature `eink-touch-scroll`).

The per-app scroll optimization (fast waveform while scrolling) used only accessibility
scroll events, which Chrome, WebView and Flutter do not send. While the foreground app
has scroll optimization enabled, the E-Ink service also holds an input gesture monitor.
It is a spy: events still reach the app and pointers are never taken over. A finger drag
beyond 10 px (the stock threshold) enters scroll mode; each move feeds the existing
velocity-based settle delay, so a fling keeps scroll mode briefly after the finger lifts.
Stylus and mouse input are ignored; accessibility scroll events still work. Apps without
scroll optimization get no monitor. A drag over the keyguard or the notification shade, or
with the screen off, does not enter scroll mode: at the start of each drag the service
checks that the screen is interactive, the keyguard is not locked and no SystemUI system
window is active or focused (from the accessibility windows list).

```sh
adb logcat -s HiBreakTouchScroll   # "touch scroll monitor started" / "stopped"
```

## Keyboard waveform (IME layer flag)

Patch: [`device/frameworks_native/0003-ime-layer-flag.patch`](patches/hibreak/device/frameworks_native/0003-ime-layer-flag.patch)
(feature `eink-ime-layer-flag`).

The stock window manager marks the IME window with the XRZ mode word `0x60400089`
(input-method flag `0x400000`, input waveform 137, PICTURE2 dither bits). While such a
layer is visible, the composer updates the panel with waveform 137, a fast low-gray
waveform made for typing. The composer receives per-layer modes through command-buffer
opcode `0x800` with one word, which is what the existing `setLayerClass` sends.
SurfaceFlinger now sends the word for layers named `InputMethod` together with the
layer geometry; the composer keeps it per layer. Other layers are unchanged. The exact
look of waveform 137 still needs on-device evaluation.

```sh
adb logcat -s SurfaceFlinger | grep EinkLayerMode   # "[InputMethod#...] mode=0x60400089" when the mode changes
```

## E-Ink daemon user

Patches: [`vendor_a9_services/0001-HiBreak-Pro-Color.patch`](patches/hibreak/vendor_a9_services/0001-HiBreak-Pro-Color.patch)
(`a9_eink_daemon.rc`), [`system_sepolicy/0001-HiBreak-Pro-Color.patch`](patches/hibreak/system_sepolicy/0001-HiBreak-Pro-Color.patch).

`a9_eink_server` only sets `vendor.xrz.*` properties (through the property service) and
writes the two `lm3630a` frontlight nodes, so it runs as `system` instead of `root`.
init hands it the nodes (`chown system system`, mode 0660) at `post-fs-data`; SELinux
lets init change their attributes. It still accepts only uid 1000 clients, and only the
commands the E-Ink app sends: `lights` (each lamp 0-220), `au_br0/1`, `an_fl0/1`,
`clean<N>` and `scroll0/1`. Waveform profiles, repaints and clears go to SurfaceFlinger.
With `persist.debug.hibreak.einkd_root=1`, the system instance is replaced by the
previous root instance once boot completes.

```sh
adb shell ps -A -o USER,NAME | grep a9_eink_server     # system
adb shell ls -l /sys/devices/platform/11d01000.i2c7/i2c-7/7-0036/lm3630a_*_light
adb logcat -s HiBreakEinkService                      # errors only (rejected commands, node writes)
```
