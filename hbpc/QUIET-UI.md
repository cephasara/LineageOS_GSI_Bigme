# Quiet E-Ink UI

Small changes that remove refreshes the panel does not need (idle animations,
decorative effects) and raise icon contrast. No layout or interaction changes.

## Resource defaults

Patch: [`defaults/device_phh_treble/0008-quiet-eink-ui-resources.patch`](patches/hibreak/defaults/device_phh_treble/0008-quiet-eink-ui-resources.patch)
(category `defaults`, feature `quiet-eink-ui`). Product overlays in
`device/phh/treble/bigme-eink/overlay`:

| Resource | Value | Effect |
| --- | --- | --- |
| SettingsLib `dark_mode_icon_color_single_tone`, SystemUI `dark_mode_icon_color_dual_tone_fill`, `dark_mode_qs_icon_color_single_tone`, `dark_mode_qs_icon_color_dual_tone_fill` | `#ff000000` | Dark status bar / QS icons are solid black instead of 50–70% grey. The dual-tone background (empty signal bars) stays light. White icons (dark backgrounds) are unchanged. |
| SystemUI `status_bar_icon_drawing_alpha` | `100%` | Status bar icons are not drawn at 90% alpha. |
| iconloader `clock_component_name` | empty | The Launcher Clock icon is static instead of redrawing every second. The icon cache may keep the live icon until Launcher refreshes the Clock entry (e.g. clear Launcher cache or reinstall/update Clock). |
| LatinIME `config_default_key_preview_popup` | `false` | No key preview popup by default (two partial updates per key press). Users can re-enable it in the keyboard settings; an explicit earlier choice is kept. |
| framework `config_wallpaperMaxScale` | `1` | No wallpaper zoom on Launcher state changes; the wallpaper is not resampled at 110%. |
| SystemUI `flag_charging_ripple`, framework `config_showBuiltinWirelessChargingAnim` | `false` | No charging ripple / wireless charging animation window when a charger is connected. |
| SystemUI `config_enablePrivacyChipAnimation` | `false` | Camera/microphone privacy chip appears without animation. |
| SystemUI `keyguard_shadow_color` | transparent | No soft shadow behind keyguard text. |
| Launcher `config_pageSnapAnimationDuration` | `1` | Home page snaps (Home button on Home, drag page flips, drops) finish in one frame. |

Elevation shadows (View and Compose) are off through flat windows: `frameworks_base/0001`
sets the HWUI light source alpha to 0 (`ThreadedRenderer`), so no shadow overlay is needed.

To revert one value, remove its line from the overlay file and rebuild.
`verify-hibreak.py` checks the packaged values.

## Animations-off leaks

Patch: [`shared/frameworks_base/0023-animations-off-frame-leaks.patch`](patches/hibreak/shared/frameworks_base/0023-animations-off-frame-leaks.patch)
(category `shared`, feature `animations-off`). These effects ignored the animator
duration scale and kept redrawing with animations off. Each change applies only while
`ValueAnimator.areAnimatorsEnabled()` is false (animator duration scale 0, the HiBreak
default); with animations on nothing changes.

| Effect | Change |
| --- | --- |
| View scrollbars | Hidden in one frame after the usual delay instead of a 250 ms fade. |
| `TextView` marquee (carrier names, keyguard messages, QS footer) | Not started; the text stays ellipsized. |
| `Scroller` / `OverScroller.startScroll` | Programmatic scrolls (page keys, `smoothScrollBy`, page snaps, list `smoothScrollBy`) land on the first frame. Flings are unchanged. |
| Compose QS tile labels | No `basicMarquee` pass. |
| SystemUI `AnimationDrawable` icons (download/upload in the status bar and notification rows) | First frame shown instead of a 5 Hz loop. |
| Compose text cursor in Settings (`SettingsTheme`) and SystemUI (`PlatformTheme`) | Does not blink (`LocalCursorBlinkEnabled`). |

## SystemUI animation scale bridge

Patches (category `shared`, feature `animations-off`):
[`shared/frameworks_base/0024-systemui-androidx-animation-scale.patch`](patches/hibreak/shared/frameworks_base/0024-systemui-androidx-animation-scale.patch),
[`shared/frameworks_libs_systemui/0002-snap-mechanics-springs-animations-off.patch`](patches/hibreak/shared/frameworks_libs_systemui/0002-snap-mechanics-springs-animations-off.patch).

- `androidx.core.animation` (a prebuilt) keeps its own duration scale at 1.0, so status
  bar event chips, the keyguard status bar fade, notification drag-expand, remote input
  and lockscreen shortcut animations ran full length. SystemUI now copies the platform
  animator duration scale into it at startup and on every change
  (`androidx.core.animation.PlatformDurationScaleBridge`, a class in SystemUI that uses
  the library's package-private setter).
- The `mechanics` spring library (Compose QS/shade motion) settles springs immediately
  while animations are off.

## Animation scale defaults

All three **fresh-data initialization** scales are already **0**:

- Window / transition: `device/phh/treble/bigme-eink/overlay/.../SettingsProvider`
  overrides `def_window_animation_scale` and `def_window_transition_scale`.
- Animator: provider-local `def_hibreak_animator_duration_scale`, loaded together
  with the other two by `DatabaseHelper.loadDefaultAnimationSettings()`.
- The image contains an enabled static SettingsProvider product RRO for the first
  two. The provider APK itself retains upstream 100% fallbacks; inspecting only
  that APK would give a false result. The GApps provider overlay does not replace
  these defaults.

**Defaults are not a reset of existing data.** Existing saved values can differ.
Also, the three Settings development controllers still have `DEFAULT_VALUE = 1`
for **disabling the Developer options master switch**. That action writes 1, not
our initialization default 0. This inspection does not change that reset policy,
force existing users' values or periodically write their settings.
