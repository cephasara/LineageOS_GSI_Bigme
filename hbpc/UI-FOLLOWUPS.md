# Navigation, disabled text and DeskClock

This ordered follow-up to the opaque UI iteration separates framework behavior,
product defaults and application presentation into physical patch directories.
The series remains cumulative; categories are not independent build switches.

| Feature | Patches |
| --- | --- |
| Opaque three-button navigation | [`shared/frameworks_base/0001-opaque-three-button-navigation.patch`](patches/hibreak/shared/frameworks_base/0001-opaque-three-button-navigation.patch), [`defaults/device_phh_treble/0001-enable-opaque-three-button-navigation.patch`](patches/hibreak/defaults/device_phh_treble/0001-enable-opaque-three-button-navigation.patch), phone Taskbar [`apps/Launcher3/0003-pair-phone-taskbar-opaque-ink-and-background.patch`](patches/hibreak/apps/Launcher3/0003-pair-phone-taskbar-opaque-ink-and-background.patch) |
| Readable disabled text | [`shared/frameworks_base/0002-readable-disabled-preference-text.patch`](patches/hibreak/shared/frameworks_base/0002-readable-disabled-preference-text.patch), [`defaults/device_phh_treble/0002-readable-disabled-framework-text.patch`](patches/hibreak/defaults/device_phh_treble/0002-readable-disabled-framework-text.patch) |
| Outlined volume panel | [`shared/frameworks_base/0004-outline-volume-top-sections.patch`](patches/hibreak/shared/frameworks_base/0004-outline-volume-top-sections.patch) |
| Opaque DeskClock widget | [`apps/DeskClock/0001-opaque-readable-clock-widget.patch`](patches/hibreak/apps/DeskClock/0001-opaque-readable-clock-widget.patch) |
| Light Clock application | [`apps/DeskClock/0003-light-clock-app.patch`](patches/hibreak/apps/DeskClock/0003-light-clock-app.patch) |
| Overview close action and white outlined Overview | [`apps/Launcher3/0005-add-current-task-close-action.patch`](patches/hibreak/apps/Launcher3/0005-add-current-task-close-action.patch), [`apps/Launcher3/0006-outline-overview-on-opaque-white-paper.patch`](patches/hibreak/apps/Launcher3/0006-outline-overview-on-opaque-white-paper.patch) |

## Navigation policy

`config_opaqueThreeButtonNavigation` defaults false in the framework, true in
this product. Visible three-button navigation follows the system's icon appearance:
white paper/black buttons for light navigation, black paper/white buttons for dark
navigation, without gray tint interpolation or lights-out dimming. This changes
appearance only: Android's native inset ownership is preserved.
Edge-to-edge apps receive navigation Insets and own their content avoidance; legacy
`decorFitsSystemWindows`, IME and floating-window behavior remains upstream.
Applications that ignore Insets can draw controls behind the opaque bar; no content
margin is forced.
Status-bar layout, gesture navigation and explicit immersive hiding stay unchanged.
Both navigation ink endpoints and the source glyph theme are fully opaque under
this product policy. The source theme is local to navigation icon inflation.

This is a product-specific choice of a generic framework policy, with no app
name checks, polling or draw-tree scans. It does not claim compatibility with
every manually computed layout or independently managed SurfaceControl window.

## Disabled text

SettingsLib View preference selectors use opaque `#606060` disabled text in light
mode (`#BDBDBD` in night mode). Framework light primary/secondary selectors use
`#606060` as well. Black enabled primary text and disabled semantics remain.
No SIM controller logic changed. The white-background contrast is about 6.3:1.
This covers shared View selectors, not independently bundled Compose themes or
arbitrary app-level alpha. SPA's existing disabled opacity is unchanged.

## Clock and widget

DeskClock owns the default Launcher digital clock. The old widget used
`colorPrimaryContainer` as text, so the shared white-container palette exposed
white-on-white digits. Both host-background layouts now use an explicit white
surface with paired black ink and dark secondary text. Existing widget mode
preferences map to **Plain** and **Outlined**, both opaque; the original default
selection remains unchanged (Plain). Both actual layouts and day/night picker previews are covered.
The outline belongs to the drawable, with no whole-background tint to erase it.

The main app and widget configuration use the light Material theme. Main clock,
world clock, city picker, stopwatch labels, alarm hints/confirmation and tab
labels now resolve matching content roles. Analog hands and ringing controls
are adapted too. The explicitly black Android screensaver keeps its own dark
view theme so the shared date styles remain readable. Alarm schedules/actions are
unchanged.

Follows the [E-Ink UI convention](APP-ADAPTATION.md#e-ink-ui-convention): alarm, world clock and timer cards and
the timer keys are outlined; stopwatch and timer rings use the light grey track; the
selected bottom tab is inverted above a 1px line; the snackbar uses the dark inverse
surface; the analog widget dial and hands are ink and the picker previews the live layout.

## Verification and rollback

Image verification checks the navigation overlay, packaged SettingsLib disabled text
and DeskClock widget color tokens, in addition to the other release checks.

Revert a feature by removing all of its patches in reverse dependency order. Remove the
navigation enabling overlay before its framework resource.

## Volume, navigation ink and Clock bars

Volume top pieces retained their own drawables and shape geometry but lacked the
stroke previously added to the main panel. All four top variants now have 1 dp
on-surface outlines. The navigation appearance fix preserves the then-current layout policy;
it consumes the existing system appearance decision without inspecting app names
or guessing from pixels. DecorView uses the window appearance for its background;
SystemUI applies its effective icon intensity to both background and ink, including
existing IME, shade and keyguard overrides. Both endpoint colors are opaque.

Clock's root parent was already Light, but secondary Toolbar explicitly inherited
Dark, several standalone icons were fixed white, and legacy system-UI flag writes
could override light bar appearance. Correct these styling entry points; keep
layout, preferences, alarms/timers and immersive hiding unchanged. Widget setup
declares light bars in both day/night resource variants. The intentionally dark
screensaver view retains its own dark styling. Packaged verification now checks
Clock theme parents/bar flags/action tints and the active volume outline drawable (plus any retained legacy variants).
Release-flag resource shrinking can remove disabled legacy layouts/drawables;
the verifier requires the active 23.2 ringer background, not dead resources.

## Phone Taskbar and volume cap follow-up

The 23.2 phone uses Launcher TaskbarDelegate. Its separate navigation path kept
60%-alpha dark ink, lights-out dimming and an independently black bar background.
The opaque navigation policy now covers that phone path as well: binary ink and
opposite paper, without auto-dimming. SystemUI honors light navigation appearance
also in opaque modes and sends immediate tint changes. Gesture/tablet paths retain
their existing policy.

The ringer cap keeps only upper corners; a clipped lower stroke joins it to the
slider. The Kotlin binder updates the same upper corners when the drawer opens.

The optional debug-adb flavor uses the same build-time-or-runtime debug gate as
native adb root, because Lineage masks ro.debuggable on userdebug. Its read-only
marker receives the existing build_prop label; no SELinux allow rule is added.
Normal builds exclude both the daemon override and this optional property label.


## White outlined overview and close action

Overview has an icon-only Close action beside Screenshot in the existing centered
single-task action row. It ends live rendering and dismisses the captured task id
through the same RecentsView task-removal path used by card dismissal. It does not
force-stop a package. The existing disabled/visibility states and grouped-task
operation layout remain in control; Close has a 48dp touch target and accessible name.

Overview draws static 1dp black task outlines outside the existing thumbnail bounds,
white overview paper without wallpaper blur, and white/black outlined action states
for Screenshot, Close and Clear all. Task geometry, Screenshot spacing and snapshot
pixels are preserved. No snapshot filter, additional render layer or timer is added.

A navigation-colored strip inside a task preview is part of the full task snapshot:
Android excludes navigation buttons but retains the window's navigation background.
The upstream preview position helper does not generally crop system-bar content
Insets. The strip is not a second navigation window or an extra app content margin;
the patch does not cosmetically crop or stretch snapshots to remove it.

### Snapshot-not-ready edge case

If a background task snapshot is invalidated (for example by a theme change), the
action row disables Screenshot until a new snapshot is ready. Close ignores thumbnail
readiness (and rotation, which dismissal does not need), keeps the scrolling guard and
refreshes its captured task callback even without a bitmap. This edge case has not
been tested on the device.
