# Static Launcher drawer

A Launcher drawer interaction and appearance change, separate from the static system
navigation. Home ↔ All Apps opens and closes statically; workspace page swipes
([release-only](LAUNCHER-SWIPE.md)) and system Home/Overview gestures keep their
behavior.

## Threshold and completion

`config_staticAllApps` defaults false; the HiBreak Launcher overlay enables it.
The shipped Quickstep portrait controller (including its navigation subclass) and
the non-Quickstep All Apps controller share recognition in
`AbstractStateChangeTouchController`.

| Action | Additional travel after touch slop |
| --- | --- |
| Open | 48dp upward |
| Close | 32dp downward |

`static_all_apps_open_distance` and `static_all_apps_close_distance` are density-scaled
resources. Recognition uses the detector's signed pixel displacement directly, so
screen height, orientation and sheet height do not multiply the required distance.
The original touch slop is still subtracted before the detector reports displacement.

The first static version reused the native release-distance gates (phone 40%/60%,
tablet 30%). Those originally worked alongside a release-velocity shortcut. Without
that shortcut, a sheet-height-relative mandatory distance made the drawer harder
to trigger, so fixed 48dp/32dp distances are used. With static drawer mode disabled the
native animated drawer keeps its original fractions.

List-origin closing is eligible only if the list is already at offset zero when
the touch starts. Scrolling to the top stays a list-scroll gesture; lift and pull
down again to close with the lower 32dp threshold. The search/header-area and
scrollbar exceptions keep their native behavior.

Before the threshold, keep the original state and do not prepare an animation,
change the drawing controller, emit animation-preparation haptics, or drive overscroll.
On the first MOVE reaching it, switch immediately through the ordinary StateManager
start/set/end callbacks. Consume the remainder of the touch stream: holding,
retreating, UP or CANCEL cannot trigger a second action or hit a newly visible app.
UP/CANCEL before the threshold leaves the source unchanged. Release velocity does
not bypass the distance threshold. The app-list scroll interception rule is unchanged.

Programmatic state transitions involving All Apps also use direct state application,
including button/keyboard entry and committed Back. Launcher-owned predictive drawer
scale is skipped; normal Back dispatch and search/IME action selection remain.
This policy is specific to the Launcher drawer, not application navigation.

## Appearance

- White opaque drawer panel; transparent scrim outside a sheet. In the no-sheet
  layout the scrim itself is the drawer surface, so it is white rather than absent.
- Zero drawer depth and disabled Launcher All Apps background blur.
- A local light content context keeps drawer labels readable on white independently
  of the home theme. Layout, Insets, navigation safe area and touch targets are retained.
- Search apps uses a white rounded rectangle with a 1dp opaque black outline.
  The initial inflation and header-scroll background-reset paths both select it.

This covers the Home Launcher drawer state machine. The separate large-screen
Taskbar slide-in controller is not a new threshold gesture implementation.

## Verification

The image verifier checks the packaged activation flag, surface/outline values and
search shape. Event delivery, drawing and the feel of the thresholds need a device test.
