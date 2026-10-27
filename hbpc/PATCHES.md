# Patch categories

Scope: maintained HiBreak changes on `lineage-23.2`, including the
[opaque UI iteration](OPAQUE-UI.md). The builder applies the complete release series in its established order;
categories are not independently selectable build variants.

## Classification rules

App changes follow [E-Ink app adaptation constraints](APP-ADAPTATION.md):
**不改布局，只改样式，不改逻辑，避免 Bug。** Keep layout and behavior changes
separate from application restyling.

| Category | Meaning | Examples |
| --- | --- | --- |
| `compat` — compatibility fixes | Correct startup, presentation or legacy vendor compatibility failures. Preserve these when moving the device baseline. | Early SurfaceFlinger guard, explicit HWC damage rectangles, vendor CIL compatibility. |
| `shared` — shared implementation | Reusable framework/SystemUI behavior or E-Ink presentation, without a HiBreak hardware protocol dependency. | Flat windows, static feedback/cursor, Monet roles, respecting Animator-off. |
| `defaults` — product configuration | Choose policy, initial values, overlays or build packaging. May need a small framework hook to initialize a setting. | Default light theme/preset, Animator=0, silent provisioning, Battery Saver night-mode policy. |
| `apps` — application presentation | Change an application's own theme, layouts or widgets. Reuse inside one application does not make it a platform-wide change. | DeskClock light theme and its RemoteViews clock widget; Launcher-owned menus and folders. |
| `device` — HiBreak-specific implementation | Depends on this panel, input mounting, vendor properties, privileged hardware service or protocol. | XRZ waveform contract, forced GPU composition, rotation, frontlights and E-Ink controls. |
| `debug` — optional diagnostics | Debug-only behavior explicitly selected with `--debug-adb`. | Unauthenticated USB ADB payload and automatic-enable attempt. |

Use a primary category for each functional change and secondary categories where
needed. Record baseline importance separately: a device workaround can also be
essential to boot/display; a shared behavior fix need not be boot-critical.
An XML file is not automatically `defaults`, and a change in `frameworks/base`
is not automatically `shared`. Classify by behavior and dependencies.

“Shared” describes reuse, not universal coverage or validation on other devices.
SystemUI is a system component: changing its common lockscreen code is distinct
from adding a package-name workaround for a third-party app. The GSI remains
supported only on HiBreak Pro Color.

## Directory convention for new patches

New feature patches use physical category directories, in addition to the
`category` field in `series.json`:

```text
patches/hibreak/
  compat/<source_project>/NNNN-description.patch
  shared/<source_project>/NNNN-description.patch
  defaults/<source_project>/NNNN-description.patch
  device/<source_project>/NNNN-description.patch
  apps/DeskClock/NNNN-description.patch
  apps/Launcher3/NNNN-description.patch
```

For non-app directories, encode the Android source project with underscores
(for example `frameworks_base`). For apps, use the owning app directory name.
The series entry's `project` still contains the real Android checkout path,
such as `packages/apps/DeskClock`. Optional diagnostics remain under the
separate `patches/debug-adb` series.

Clock widgets belong to `apps/DeskClock`, even when Launcher hosts them.
Shared disabled-text selectors belong to `shared/frameworks_base`; a product
overlay enabling a navigation policy belongs to `defaults/device_phh_treble`,
separate from that policy's framework implementation. Split these changes into
independent commits and patches; document dependencies when they must ship
together. Patch application order comes only from `series.json`, never directory
sorting.

Existing baseline bundles and previously published feature paths remain at
their recorded locations. This convention applies to new patches; it does not
claim the historical bundles have been split or relocated. Historical Launcher
entries described as shared below refer to reuse within Launcher, not coverage
of other applications.

See [navigation, disabled text and Clock follow-ups](UI-FOLLOWUPS.md) for the
first implementations using these directories and their rollback dependencies.

See [Launcher swipe-on-release](LAUNCHER-SWIPE.md) for the separately requested
interaction change and its dedicated app/configuration patches.

See [static system gesture navigation](STATIC-GESTURES.md) for the separately requested
Home/Overview/Back behavior and transparent-safe-area handle styling.

See [static Launcher drawer](LAUNCHER-DRAWER.md) for distance-triggered opening/closing,
flat white presentation and the outlined search field.

See [black/white themed icon colors](THEMED-ICON-COLORS.md) for the Launcher-only
product color overrides, separate from the existing shared icon contour patch.

See [static black/white lockscreen and PIN](LOCKSCREEN.md) for the explicit unlock
button, deferred swipe presentation, clock colors and static credential controls.

See [E-Ink sleep screen](SLEEP-SCREEN.md) for the page kept on the panel while the
screen is off: picture (logo and lock time), clock, lock screen or a custom image.

See [custom hardware keys and Page Up/Down](HARDWARE-KEYS.md) for the device-scoped
F1/F2 consumption fix, repeat-safe gestures and bounded standard page-key actions.
This is functional device work, separate from application restyling.

See [Aperture static light camera](APERTURE.md) for explicit light themes/bars,
outlined controls, inverse selected states and app-local static presentation while
retaining capture, recording, focus, QR, permissions and native geometry.

See [DocumentsUI paper/ink presentation](DOCUMENTSUI.md) for app-local white/black
surfaces, whole-pixel outlines and static presentation while retaining file actions.

See [WWAN service reconnect refresh](NRM-RECONNECT.md) for the separate one-shot,
device-gated native registration query after reconnection. No radio reset or poll loop.

See [out-of-service radio recovery](OOS-RECOVERY.md) for the device-gated, backed-off
radio power cycle of a SIM that stays unregistered while its home network is visible.

## Functional index

Locations below are relative to the named Android source project. Each project
links to its actual patch in the project index below.

| Change | Primary category / secondary | Location and dependency | Baseline importance |
| --- | --- | --- | --- |
| Boot-derived Keymaster security patch level | `compat` | Already in the upstream PHH `rw-system.sh` patch chain; do not duplicate in HiBreak series. | Retained boot compatibility. |
| Guard early display hotplug before Scheduler exists | `compat` | `frameworks/native`: `SurfaceFlinger.cpp`. | Retained startup fix. |
| Force GPU/client composition and prevent later resets | `device` / `compat`, `defaults` | `SurfaceFlinger.cpp` plus `device/phh/treble/bigme-display/display.mk`, controlled by `ro.bigme.force_client_composition`. | Known black-screen workaround; not a universal Android rendering policy. |
| Explicit full-layer damage | `compat` / `shared` | `frameworks/native`: `CompositionEngine/src/OutputLayer.cpp` and its tests. | Fixes independent SurfaceView/Flutter updates with the retained composer; no app check or timer. Partial/empty damage remains intact. |
| Explicit full client-target damage | `compat` / `shared` | `FramebufferSurface`, `HWComposer`, `HWC2`, both Android 16 virtual-display implementations and test/mocks. | Retained presentation compatibility; keep buffer-size API changes together, including cached slots. |
| Restore vendor CIL ordered declarations | `compat` | `external/selinux`: upstream `0012-Fix-secilc-on-Moto-One-Action.patch` is not applied ([removed](UPSTREAM-DELTA.md)); no HiBreak patch needed. | Retained compatibility with the current vendor policy; not an E-Ink visual feature. |
| SELinux ioctl xperms by kernel policy version | `compat` | [`init/selinux.cpp`](patches/hibreak/compat/system_core/0001-selinux-xperms-by-policy-version.patch); [scope](SELINUX-XPERMS.md). | Keeps `allowx` rules when `/sys/fs/selinux/policyvers` >= 30 (this 4.19 kernel) instead of stripping below 5.4; boot params via cmdline/bootconfig; automatic legacy retry; switch file `/metadata/hibreak/selinux_legacy_xperms`. |
| TrebleApp doze-suspend toggle | `compat` | [`DisplayPowerController`](patches/hibreak/compat/frameworks_base/0001-doze-suspend-toggle-accepts-true.patch). | `persist.sys.phh.disable_display_doze_suspend` accepts TrebleApp's `true` as well as `1`; the TrebleApp switch itself turns it off again. |
| Waveform key, XRZ properties and SELinux access | `device` / `compat` | `device/phh/treble/bigme-display`, `system/sepolicy` live and frozen API policy. Proprietary key is supplied outside Git. | Basic panel integration. |
| Touch/pen and physical rotation | `device` / `defaults` | `elan_ktf.idc`, `fts_ts_pen.idc`, physical display properties. | Basic input/display alignment. |
| E-Ink app, shortcut panel, tile, daemon, frontlight scenes | `device` | `vendor/a9_services/a9_accessibility_service` and product/policy wiring; [daemon user](EINK-DISPLAY.md). | Device controls; includes per-app preferences but no Flutter app-specific repaint workaround. Daemon runs as `system` (frontlight nodes chowned on boot); `persist.debug.hibreak.einkd_root=1` restores root. |
| Waveform profiles, Hyper/HD256, dithering and manual repaint | `device` | App/daemon plus SurfaceFlinger profile transactions and XRZ properties; [scope](EINK-DISPLAY.md). | Depends on the hardware contract; do not transplant raw mode IDs into a generic framework. Hyper dithers only while `vendor.xrz.cur_fps` >= `persist.vendor.xrz.fps_high` (stock behaviour) and never applies ink/paper adjustments; composer at 120 Hz, default render 40 Hz, Hyper `min_refresh_rate` = `persist.vendor.xrz.fps`; Video scene = Fast + auto-clean + anti-flicker. |
| XRZ clean frequency after user input | `device` | [PowerManagerService pulse](patches/hibreak/device/frameworks_base/0001-xrz-check-commit-pulse.patch), [dedicated SELinux label](patches/hibreak/device/system_sepolicy/0001-xrz-check-commit-property.patch), [Reading scene interval](patches/hibreak/device/vendor_a9_services/0003-reading-scene-clean-frequency.patch); [scope](EINK-CLEAN.md). | `vendor.xrz.check_commit` 1 for 800 ms after touch/button, so per-app clean intervals take effect. |
| One-shot GC16 clear | `device` | [SurfaceFlinger transaction 1113](patches/hibreak/device/frameworks_native/0001-one-shot-gc16-clear.patch) and [clear key and tile](patches/hibreak/device/vendor_a9_services/0004-gc16-clear-actions.patch); [scope](EINK-CLEAN.md). | One full clear of the current image per request, released after present; no overlay frames. |
| No ColorFade on sleep/wake | `defaults` / `device` | [overlay](patches/hibreak/defaults/device_phh_treble/0010-disable-color-fade.patch) `config_displayColorFadeDisabled`; [kill switch](patches/hibreak/device/frameworks_base/0002-no-color-fade-property.patch) `persist.debug.hibreak.no_color_fade`; [scope](EINK-DISPLAY.md). | No screenshot fade or black cover frames on sleep/wake. |
| E-Ink WebView flags | `defaults` | [oneshot shell-user service, script and SELinux domain](patches/hibreak/defaults/device_phh_treble/0011-eink-webview-flags.patch); kill switch `persist.debug.hibreak.webview_flags`; [scope](EINK-DISPLAY.md). | `/data/local/tmp/webview-command-line`: no smooth scrolling or elastic overscroll; a user's own file is kept. |
| E-Ink composition-only damage | `device` | [`Output`/`OutputLayer`](patches/hibreak/device/frameworks_native/0002-composition-only-damage.patch); kill switch `persist.debug.hibreak.composition_damage`; [scope](EINK-DISPLAY.md). | Removed/moved/faded layers: unchanged layers below send the exposed area as damage, so the composer updates it. |
| E-Ink touch scroll detection | `device` | [gesture-monitor spy in the E-Ink service](patches/hibreak/device/vendor_a9_services/0006-touch-scroll-detection.patch); kill switch `persist.debug.hibreak.touch_scroll`; [scope](EINK-DISPLAY.md). | Scroll optimization also in Chrome/WebView/Flutter: finger drags > 10 px; never pilfers; opted-in apps only. |
| XRZ IME layer flag | `device` | [OutputLayer per-layer mode (opcode 0x800 via setLayerClass)](patches/hibreak/device/frameworks_native/0003-ime-layer-flag.patch); kill switch `persist.debug.hibreak.ime_layer_flag`; [scope](EINK-DISPLAY.md). | Keyboard visible: composer uses input waveform 137, as stock. IME only (HOME/LOGO later). |
| Text ink, Paper white, Dark ink GPU processing | `device` / `shared` | `frameworks/native`: `EinkShader.h`, render-engine/profile integration; controlled by the device app. | Optional reading enhancement. Math may be reusable; current integration is device-bound. The profile property is re-read only when it changes and parsed once per change; an active profile composes into a scratch surface and one shader pass writes the output buffer (no full-frame copy); a neutral profile adds no pass. Transaction 1111 writes only changed properties, on the binder thread. |
| No dim/shadow and outlined floating windows | `shared` | `frameworks/base`: `WindowState`, `ThreadedRenderer`, `DecorView`, `PopupWindow`, `FlatWindowBorder` (whole-pixel edge in the window theme ink, round-rect and path outlines), toasts, SystemUI dialogs opened from views; the chooser outline lives in `IntentResolver`. Convention: [APP-ADAPTATION.md](APP-ADAPTATION.md#e-ink-ui-convention). | E-Ink presentation, not required to boot. Product activation uses resource defaults. |
| Static press feedback and cursor | `shared` | `RippleDrawable`, `RippleForeground`, `Editor`, resource symbols; product overlays enable the policy. | Shared Android View paths; does not cover every independently drawn app effect. |
| Static black/white lockscreen and PIN | `shared` / `defaults` | [SystemUI implementation](patches/hibreak/shared/frameworks_base/0014-static-black-white-lockscreen-and-pin.patch), including the SystemUI-local resource policy, and [SystemUI product activation](patches/hibreak/defaults/device_phh_treble/0007-enable-static-black-white-keyguard.patch); [behavior and verification scope](LOCKSCREEN.md). | Explicit circular unlock action, deferred swipe presentation, white keyguard surfaces, black clock/text and static outlined PIN controls. Authentication and gesture acceptance gates are retained. |
| Color E-Ink palette and high-contrast pages/controls | `shared` / `defaults` | `external/libmonet` 2021/2025 roles; DeviceDefault, SettingsLib v36/Expressive, Settings and control overlays. | Monochromatic light-theme policy; pure white pages, black main text, separated grays and error red. |
| Preset naming, preview, selected-category visibility | `shared` | ThemePicker plus WallpaperPicker2 picker surfaces. | System personalization integration; not a third-party app workaround. |
| Opaque surfaces, custom shade roles and shared container outlines | `shared` / `defaults` | Monet, Android custom colors, QPR2 resource overlays, SystemUI and SettingsLib; [ordered stage index](OPAQUE-UI.md). | White ordinary containers, paired black/white states. |
| Themed icon contour | `shared` | `frameworks/libs/systemui` iconloader: [dedicated patch](patches/hibreak/shared/frameworks_libs_systemui/0001-outline-only-themed-icons.patch). A 1 dp black inner stroke follows the normalized adaptive mask only when the actual delegate is themed; covers monochrome/generated and themed clock delegates. Clips themed shadows, preserves alpha/disabled filters and badges. Standard icons and theme preferences are unchanged. | Optional icon styling; no hardware protocol, layout or interaction change. |
| Themed icons on by default | `apps` / `defaults` | [Launcher resource defaults](patches/hibreak/apps/Launcher3/0010-themed-icon-defaults-from-resources.patch) for the Themed icons preference and "Use themed icons in drawer", [enabled by the product overlay](patches/hibreak/defaults/device_phh_treble/0014-enable-themed-icons.patch); [scope](THEMED-ICON-COLORS.md#on-by-default). | Applies while no value is stored; a stored choice wins. |
| Quick Settings brightness slider hidden | `defaults` | [LineageSettingsProvider overlay](patches/hibreak/defaults/device_phh_treble/0015-hide-qs-brightness-slider.patch); [scope](OVERVIEW-TILES-SLEEP.md#overview-and-quick-settings). | `qs_show_brightness_slider` 0 (Never show) in a new settings database. |
| Flat Launcher shared presentation | `shared` / `defaults` | Resource shadow colors, common ArrowPopup, folder shapes and SysUiScrim; [ordered stage index](OPAQUE-UI.md). | No package-name workaround; existing animation-scale support retained. |
| Thin power/volume/media panel outlines | `shared` | SystemUI drawable resources. | Component-scoped presentation; native Android 16 day/night colors remain. Dynamic tint/custom shapes can limit outline coverage. |
| Keyguard reveal follows Animator-off | `shared` | `LightRevealScrimRepository` and tests: bridge platform animation-enabled state to AndroidX animator duration. | Behavior/accessibility fix; not HiBreak-specific and not a boot requirement. Covers this reveal path, not every animation in Android. |
| E-Ink sleep screen | `shared` / `device` / `defaults` | [SystemUI sleep page (picture, clock refreshed while dozing, lock screen capture, custom image), white sleep scrims/reveal, black AOD icons, no burn-in shift, screen-off wait in the doze path](patches/hibreak/shared/frameworks_base/0025-eink-picture-sleep-screen.patch) under `config_einkKeyguard`, including the doze dream on every sleep (`config_einkDozeOnSleep`), [enabled by the product overlay](patches/hibreak/defaults/device_phh_treble/0012-eink-doze-on-sleep.patch); kill switch `persist.debug.hibreak.sleep_screen_wait`; [E-Ink app setting and image provider](patches/hibreak/device/vendor_a9_services/0005-sleep-screen-setting.patch) `hibreak_sleep_screen_mode`; [scope](SLEEP-SCREEN.md). | While the screen is off (AOD off) an opaque page above every keyguard view: centered LineageOS logo and "Locked at hh:mm" with the notification icons (default), a black clock updated every 1/5/15 min, the lock screen as shown before sleep, or a chosen image; hidden on wake. The display turns off only after the page is on the panel (400 ms settle after presentation, 1.5 s timeout). Sleep is DOZING with the display off; no pulsing or AOD. |
| Quiet E-Ink UI resources | `defaults` | [Product overlays](patches/hibreak/defaults/device_phh_treble/0008-quiet-eink-ui-resources.patch); [scope](QUIET-UI.md). | Solid black dark status icons, static Clock icon, no key preview, wallpaper zoom, charging/privacy animations or layer shadows. |
| Animations-off frame leaks | `shared` | [View/widget/SystemUI gates](patches/hibreak/shared/frameworks_base/0023-animations-off-frame-leaks.patch); [scope](QUIET-UI.md). | Scrollbar fade, marquees, programmatic scrolls, AnimationDrawable icons and Compose cursor blink stop at animator scale 0. Flings unchanged. |
| SystemUI animation scale bridge | `shared` | [AndroidX core-animation scale bridge](patches/hibreak/shared/frameworks_base/0024-systemui-androidx-animation-scale.patch) and [mechanics spring snap](patches/hibreak/shared/frameworks_libs_systemui/0002-snap-mechanics-springs-animations-off.patch); [scope](QUIET-UI.md). | SystemUI chips, keyguard fades and notification expansion follow the animator scale; QS/shade springs settle at once when it is 0. |
| Initial animation scales, preset and AOD policy | `defaults` | SettingsProvider resources/DatabaseHelper and product overlays. | Animator/window/transition defaults 0, preset index 13, unsupported Android AOD off. Existing user settings are not continuously overwritten. |
| Light theme, white wallpaper, no automatic Battery Saver dark theme | `defaults` | `device/phh/treble` resource overlays. | Product choices. The pure white 824x1648 default wallpaper is overlaid wherever the framework or LineageOS ships one (nodpi, sw600dp/sw720dp-nodpi, hdpi to xxxhdpi), so home and lock screen are white until a wallpaper is chosen. To restore it, open Wallpaper & style > More wallpapers > On-device wallpapers and pick its first tile (the built-in default). `config_wallpaperCropperPackage` names the installed picker (`com.android.wallpaper`). The default wallpaper is unrelated to the [sleep screen](SLEEP-SCREEN.md) image. |
| No other-vendor helpers | `defaults` | [base.mk package removal](patches/hibreak/defaults/device_phh_treble/0009-skip-other-vendor-packages.patch); `verify-hibreak.py` checks the binaries, apps and init scripts are absent and the HIDL Java libraries TrebleApp loads are present. | TrebleDroid helpers for hardware this MediaTek phone lacks are not installed: Qualcomm `qcom-atel-ready` (runs only with `vendor.qcrild`) and the `QcRilAm` in-call audio app, Samsung LSI `slsi-booted`, the Xiaomi/OnePlus/ASUS camera motor helpers, the Oppo/OnePlus fingerprint compat services, `oplus-alert-slider` and `xiaomi-touch`. MTK helpers stay. TrebleDroid module sources are kept, just not installed. The two qti am HIDL Java libraries (built from `packages/apps/QcRilAm`, which stays in the manifests) and their `interfaces.xml` entries stay installed: the prebuilt TrebleApp links them as optional libraries and crashes without them. |
| VoLTE with the MediaTek IMS service | `device` / `defaults` | [Preinstalled platform-signed `com.mediatek.ims` priv-app and privapp allowlist](patches/hibreak/device/device_phh_treble/0001-preinstall-patched-mediatek-ims.patch), built by `build-hibreak.py` from the pinned TrebleDroid APK and [`mtk-ims/ims-mt-ecpi.patch`](mtk-ims/ims-mt-ecpi.patch); [VoLTE defaults](patches/hibreak/defaults/device_phh_treble/0016-make-volte-available.patch) `persist.dbg.volte_avail_ovr=1`, `persist.dbg.allow_ims_off=1`; [scope](MTK-VOLTE.md). | Incoming VoLTE calls ring although `rw-system.sh` disables the modem's call approval (`AT+EAIC=3`); Wi-Fi Calling is not forced. |
| EXT4-only products | `defaults` | [AndroidProducts.mk and the removed EROFS product makefiles](patches/hibreak/defaults/device_phh_treble/0013-ext4-only-products.patch); [delta](UPSTREAM-DELTA.md). | Only `lineage_arm64_bgN4`/`bvN4` remain selectable; the upstream EROFS products are deleted. |
| Silent setup, package selection, normal USB defaults | `defaults` | `HiBreakProvision`, `hibreak-common.mk`, GApps/Vanilla product makefiles. | Requested release policy, not a debug-only setup bypass. |
| Signing, build identity and image publication | `defaults` | `build-hibreak.py`, manifest pins and `verify-hibreak.py`, outside the source patch series. | Preserve signing identity and out/cache reuse; only systemimage is built. |
| Native authenticated adb root domain | `compat` / `defaults` | [Separate policy patch](patches/hibreak/device_phh_treble/0005-compat-native-adb-root-policy.patch), [scope](ADB-ROOT.md); actual product variant gate. | Restores upstream su behavior on normal userdebug/eng; auth/root-setting checks unchanged. |
| Opt-in permissive ADB authentication | `debug` | Separate `patches/debug-adb/series.json`, adbd and device init patches. | Excluded from normal builds; for diagnostics only. Automatic enabling is not reliable; enable USB debugging by hand if it does not come up. Native root policy is handled separately in the release series. |

## Project index

The original ten patches below are **mixed project bundles**. New opaque-UI
work uses separate ordered feature patches with category metadata in
[series.json](patches/hibreak/series.json); see [stage/rollback index](OPAQUE-UI.md).
Tests stay with the behavior they verify.

| Android project / patch | Categories |
| --- | --- |
| [device/phh/treble](patches/hibreak/device_phh_treble/0001-HiBreak-Pro-Color.patch) | `device`, `defaults`, `shared`, `compat` |
| [system/sepolicy](patches/hibreak/system_sepolicy/0001-HiBreak-Pro-Color.patch) | `device`, `compat` |
| [frameworks/native](patches/hibreak/frameworks_native/0001-HiBreak-Pro-Color.patch) | `compat`, `device`, `shared` |
| [frameworks/base](patches/hibreak/frameworks_base/0001-HiBreak-Pro-Color.patch) | `shared`, `defaults` |
| [vendor/a9_services](patches/hibreak/vendor_a9_services/0001-HiBreak-Pro-Color.patch) | `device`, `defaults` |
| [external/libmonet](patches/hibreak/external_libmonet/0001-HiBreak-Pro-Color.patch) | `shared` |
| [packages/apps/Settings](patches/hibreak/packages_apps_Settings/0001-HiBreak-Pro-Color.patch) | `shared` |
| [packages/apps/ThemePicker](patches/hibreak/packages_apps_ThemePicker/0001-HiBreak-Pro-Color.patch) | `shared` |
| [packages/apps/WallpaperPicker2](patches/hibreak/packages_apps_WallpaperPicker2/0001-HiBreak-Pro-Color.patch) | `shared` |
| [packages/modules/IntentResolver](patches/hibreak/packages_modules_IntentResolver/0001-HiBreak-Pro-Color.patch) | `shared` |
| [debug packages/modules/adb](patches/debug-adb/packages_modules_adb.patch) | `debug` |
| [debug device/phh/treble](patches/debug-adb/device_phh_treble.patch) | `debug` |

## Provenance, ordering and maintenance

`trebledroid`, `trebledroid-staging` and `personal` describe **upstream provenance**,
not necessity or reuse. They contain GSI compatibility and other-device changes;
do not label every inherited patch necessary for HiBreak without evidence.
This index classifies the maintained HiBreak work rather than re-auditing every
inherited patch's necessity.

Current application order remains upstream TrebleDroid → staging → personal →
[HiBreak release series](patches/hibreak/series.json) → optional
[debug ADB series](patches/debug-adb/series.json). In particular:

- Resource symbols/framework implementations and their enabling overlays belong
  together. A configuration file alone cannot implement flat windows/static UI.
- App profile controls depend on the native bridge, daemon, properties and policy.
- Monet roles, picker presentation and the initial preset form one coherent theme.
- Compatibility fixes and device activation may touch the same source file.

For subsequent work, use descriptive commit subjects such as `shared: ...`,
`compat: ...`, `defaults: ...`, `apps: ...`, `device: ...` or `debug: ...`; update the functional
index when behavior or dependencies change. Prefer one functional change per
commit, preserving a clear revert point.

The builder now checks ordered same-project chains before mutation, supports
already-applied prefixes, and applies missing patches in series order. New work
must use feature patches after the frozen baseline bundles. Replaying all files
and modes verifies export completeness while reusing the current checkout/out.
Feature/category metadata is an index, not a set of independent build switches.
See [OPAQUE-UI.md](OPAQUE-UI.md) for dependencies and source-checkout rollback.

The retired retained sleep keyguard (custom wallpaper/text page, display-OFF gate and
presentation-fence hold) is not in the series; the current sleep page is the
[E-Ink sleep screen](SLEEP-SCREEN.md). Follow-up fixups are squashed into their feature
patches (tree-identical). See [Overview, tiles and sleep](OVERVIEW-TILES-SLEEP.md).
Static E-Ink keyguard/PIN, Overview feedback, menus and quick-settings outlines remain.
The old Regal-through-unlock policy was already retired and is not restored.
The index itself does not activate or disable patches.

See [Messaging E-Ink presentation](MESSAGING.md) for the app-owned ink/paper
palette, outlined bubbles/composer/widgets and static visual feedback.
See [Dialer ongoing calls](DIALER.md) for the voice page's white/black theme,
outlined controls, DTMF keypad and audio route picker (`apps`,
`eink-dialer-incall`). The independent [Dialer main-page](DIALER.md#main-activity-search-favorites-history-and-keypad)
feature (`eink-dialer-main`) preserves that voice/RTT boundary. See
[Contacts](CONTACTS.md) for its pinned app-local light/static presentation,
callback-preserving drawer/refresh bridges and native background metrics
(`eink-contacts`). Both are `apps` patches; neither changes providers or call policy.
