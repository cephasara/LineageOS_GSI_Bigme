# Opaque E-Ink UI iteration

Shared opaque UI for Android 16 QPR2 on the HiBreak Pro Color. It does not change
waveforms, GPU processing, lock/unlock timing or Flutter damage handling.

## Patches

| Feature in `series.json` | Patches | Changes |
| --- | --- | --- |
| `opaque-colors` | [`frameworks_libs_systemui/0001`](patches/hibreak/frameworks_libs_systemui/0001-shared-opaque-android-colors.patch), [`device_phh_treble/0002`](patches/hibreak/device_phh_treble/0002-defaults-opaque-system-surfaces.patch); the libmonet roles are in [`external_libmonet/0001`](patches/hibreak/external_libmonet/0001-HiBreak-Pro-Color.patch) | White standard MD3 containers, paired Android shade roles, opaque QPR2 surface effects and blur fallbacks. |
| `outlined-containers` | [`frameworks_base/0002`](patches/hibreak/frameworks_base/0002-shared-opaque-outlined-containers.patch) | Notification/QS independent outlines, SettingsLib preference groups and SPA cards, no tonal elevation in SPA/SystemUI, opaque notification tint. |
| `flat-launcher` | [`packages_apps_Launcher3/0001`](patches/hibreak/packages_apps_Launcher3/0001-shared-flat-launcher-surfaces.patch), [`device_phh_treble/0003`](patches/hibreak/device_phh_treble/0003-defaults-flat-launcher-surfaces.patch) | Resource-driven label shadow removal, no top/bottom gradient masks, shared popup shape outlines and folder surfaces; the product overlay sets the folder outline width. |

Each new source patch is a separate entry in the ordered
[release series](patches/hibreak/series.json), with `feature` and `category`
metadata, applied after the ten baseline `0001-HiBreak-Pro-Color.patch` bundles.

Ordinary MD3 surfaces and accent containers become white with black primary text.
Explicit selected QS states are black/white; inactive states white/black. Disabled
and supporting roles retain distinction, and error red is retained. We do not
infer selection from `primaryContainer`: it also colors large ordinary cards.
Standard role changes are limited to the light monochrome scheme. Product overlay
policies are device-wide. Existing native night resources remain where provided;
this does not constitute a complete dark-theme redesign.

SettingsLib/SystemUI Compose themes disable tonal elevation at their existing
entry points. Borders reuse shape strokes or separate drawable layers so dynamic
background tints cannot erase them. Existing radii, clipping, notification color,
focus and touch targets remain. Disabled-content opacity is retained rather than
making disabled controls appear enabled.

Launcher preserves wallpaper-dependent label foreground colors. Shadow colors
are exposed as resources and set transparent by the product overlay, activating
its existing fast path. Popup shape styling reuses the existing construction
pass; folder outlines reuse the existing shape with a product-overridable width
(the attributes stay inside Launcher; the overlay sets only the width). Long-press
popups draw one edge per surface and have no arrow (a fill-only wedge cannot carry the
outline); pressed items show a light grey; the widget picker search box and rows are
outlined. This does not outline arbitrary third-party widgets.

## Motion findings and cost

The checked-in AndroidX `dynamicanimation` 1.1.0-alpha04 already reads platform
Animator duration scale on Android 13+, and advances directly to equilibrium at
scale zero. Launcher `RectFSpringAnim` uses this implementation. Its popup
animators also already respect the platform setting. No additional spring
completion/cancel patch is justified by this audit; gesture tracking is retained.
The folder preview's RadialGradient shadow code is behind `DRAW_SHADOW=false` and
was already inactive. Removing it would not improve the display.

There is no view-tree scan, package-name check, timer, full-screen filter or new
service. Color adaptation runs during palette generation, and resource decisions
run in existing theme/container setup. Simple border drawing is not literally
free, but no new continuous processing is introduced. Per-frame performance and
physical waveform quality have not been measured.

## Verification and rollback

The normal GApps image verifier reads effective APK values: AAPT folds
lower-than-minSdk version qualifiers into default configurations and labels framework
entries PUBLIC / STAGED_ID. It also checks all six compiled surface selectors for
opaque white without alpha/lStar.

Public patches and the Android checkout must agree: removing a series entry alone does
**not** undo already-applied source commits. Remove a feature's patches together, in
reverse order; `outlined-containers` and `flat-launcher` rely on the white surfaces of
`opaque-colors`. Do not leave an enabling overlay when removing its resource or
implementation.

On the device, check the notification shade (active/inactive/disabled tiles,
media/colorized rows), View and Compose Settings, launcher menus/folders/app drawer,
wallpaper text contrast, navigation, font scaling and lock/unlock. A screenshot cannot
establish physical E-Ink quality.
