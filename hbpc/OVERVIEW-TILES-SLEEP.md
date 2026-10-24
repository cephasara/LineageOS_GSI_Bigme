# Overview feedback, outlined tiles and sleep

Patches: Overview-ready haptics in
[`apps/Launcher3/0008-static-system-home-and-overview-gestures.patch`](patches/hibreak/apps/Launcher3/0008-static-system-home-and-overview-gestures.patch),
task chip and menu styling in
[`apps/Launcher3/0006-outline-overview-on-opaque-white-paper.patch`](patches/hibreak/apps/Launcher3/0006-outline-overview-on-opaque-white-paper.patch),
quick-settings tiles in
[`shared/frameworks_base/0018-static-black-white-quick-settings-tiles.patch`](patches/hibreak/shared/frameworks_base/0018-static-black-white-quick-settings-tiles.patch).

## Overview and quick settings

Overview readiness uses the existing motion-pause detector and its once-per-gesture
callback. The home-screen static path handles readiness before checking for an
animation controller, since that controller is optional when motion is disabled.
Feedback uses the same low-tick primitive, scale and texture-tick fallback as
scrolling task cards, through Launcher’s preference-aware vibrator wrapper. No
additional distance threshold or acceptance change is introduced. Cancelling a
gesture after the tick still follows the ordinary cancellation path.

The task-card chip and both task menu implementations use white surfaces, black
text/icons and one physical-pixel black outlines. App artwork remains app artwork.
Menus open/close at their endpoints while retaining completion callbacks. Menu
scrims, thumbnail dimming, decorative arrow shadow, elevation shadows and chip
reveal/focus motion are removed under the existing flat Launcher policy.

The 23.2 release enables `qs_ui_refactor_compose_fragment`, so quick-settings tiles use
the Compose `infinitegrid/Tile.kt` path (the View tiles never run and are not patched).
Compose's shared `TileExpandable` passes a `BorderStroke` to its native expandable
controller: a whole-pixel edge (about 1dp) in the theme ink, grey for unavailable tiles.
The toggle target of dual-target tiles (Internet, Bluetooth) is ringed. Edit mode
outlines the edit tiles, the available-tiles list and its menu; the footer pills and
icon buttons and the Modes dialog tiles are outlined too. Dialogs opened from tiles
open as plain floating windows (no launch animation), framed by the window border, and
the tile keeps drawing. Fills, labels, layout, state cues, clicks, secondary targets and
long-clicks retain native behavior. Notification cards keep their theme-dependent 1dp
outline.

## Sleep

The custom sleep keyguard of September 2026 (display-off gates, a centered sleep page
and wallpaper worker, `ro.bigme.eink_sleep_keyguard`) is not part of the series. The
current sleep page is the [E-Ink sleep screen](SLEEP-SCREEN.md); the
[static black/white keyguard and PIN](LOCKSCREEN.md) is unchanged by it.
