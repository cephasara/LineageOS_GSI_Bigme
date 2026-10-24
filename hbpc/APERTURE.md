# Aperture: static light paper/ink camera

Applies the [app adaptation rules](APP-ADAPTATION.md) to `org.lineageos.aperture`,
preserving layout and camera behavior.

## Maintained implementation

[App-owned patch](patches/hibreak/apps/Aperture/0001-static-light-paper-ink-camera.patch),
feature `eink-aperture`, on Aperture `1120b49b7f24e7ef04213db14a6f2e5e52b4f11c` (the
manifest pin).
The regular Soong `Aperture` module builds the source and signs it with the existing
release key; no prebuilt APK substitution, shared-library change or global setting write.

- Declare `Theme.Material3.Light.NoActionBar`; camera and settings inherit the same
  paper/ink base. Remove dynamic wallpaper-color application. Both activities explicitly
  request light system-bar appearance (dark icons); preserve the camera's native hidden
  status bar and existing edge-to-edge/inset handling. No forced dark mode.
- White ordinary surfaces, black text/icons, black outlines within native bounds.
  Control, card and surface outlines are 1dp (2px); vector icons retain viewport
  strokes; grid and leveler guide lines stay 1px.
  Disabled plain controls use dashed outlines instead of unreadable gray text.
  Current camera mode and selected lens use paired black fill/white text, retaining
  the native disabled-mode and selected-lens semantics. Recording time is inverse.
- Outlined secondary controls, gallery/QR cards, sliders, settings controls and permission
  panel. Slider shadows/gradient are removed. Focus/grid lines have black ink with a
  white keyline so they remain visible over unmodified preview content. The unaligned
  horizon target is dashed and the aligned target solid; sensor thresholds are unchanged.
- Static photo/video/stop and pause/play/flip icons; immediate mode highlight, focus-ring
  size, orientation compensation, secondary-panel visibility and status-chip updates.
  Island empty-list submission and visibility work formerly deferred to fade completion
  now runs on the immediate path, with no stale listener that could hide newer items.
- Countdown digits remain visible for each real second, black on a white text backing.
  Capture completion, cancellation/restart, recording time and all scheduling remain real.
  Discrete zoom uses the original zero-duration update/end path, retaining zoom clamping,
  gesture mutex gating/release and actual camera-controller calls.
- No decorative capture blackout or thumbnail crossfade. **CameraX screen flash is
  retained**: it affects exposure and is not a decorative animation. Native freeze/blur
  while rebinding a camera is retained; preview, saved media, image processing and playback
  pixels are not recolored. Error/warning red and the distinct buffered-progress gray
  remain semantic exceptions, not ordinary UI surfaces.
- Material motion tokens and window/scrim animations are zero; ripples are transparent
  with static control boundaries. Settings switches jump their native thumb to its final
  position after `super.setChecked`, retaining callbacks. RecyclerView item/overscroll
  effects are disabled. Media3 controller animation is off; its controls use white/black
  chrome, while playback, seeking, buffering and controller timeout behavior stay native.

Follows the [E-Ink UI convention](APP-ADAPTATION.md#e-ink-ui-convention): preference rows, toolbar icons and
secondary bar buttons have no frame at rest (selected inverted, pressed outlined, focused
dashed); the shutter has no square frame around its round glyph; the gallery and QR cards
use edges matching their 8dp and 12dp clips; the snackbar keeps its edge under its white
tint; the QR sheet strokes the shape drawable that BottomSheetBehavior installs.

## Library completion adapters

The bundled Material **1.14.0-alpha02** and CustomView **1.2.0-alpha03** have no public
sheet-settle/appbar-snap duration controls. App-local declared subclasses fill those gaps:

- `EinkBottomSheetBehavior` finishes only an already-settling `OverScroller` at the
  **native target** before drawing. `ViewDragHelper.continueSettling(true)` still moves
  the child, dispatches slide updates and defers IDLE; Material's own tracker then
  performs the final state/dismissal callback. No guessed destination, helper abort,
  fabricated dismissal or pointer cancellation. Native retargeting wins over stale work.
- `EinkAppBarLayout` ends only the native automatic offset animator before drawing,
  retaining its final offset/update path. `EinkCollapsingToolbarLayout`, compiled inside
  this app in Material's package, uses the package-private title helpers to show native
  expanded/collapsed endpoints at their native threshold instead of fading/scaling text.
- Attach/detach registration is bounded. The three reflected fields are retained through
  R8 and checked as actual packaged DEX definitions/types. Unexpected library mismatch
  logs and falls back to native completion rather than breaking navigation. An upgrade
  must be re-reviewed; neither the fallback nor a version string alone proves compliance.

These are presentation adapters, not a gesture rewrite. Finger scrolling/dragging,
input-driven fling physics, camera preview, sensor feedback and real progress remain.
OS-owned permission dialogs, external gallery/Lens/chooser activities are outside this
app patch; the GSI's existing shared no-shadow/static policy remains in force.

## Verification and limitations

- `verify-aperture.py`: packaged package identity,
  explicit light parent chain, semantic roles/bars, 16 zero durations, outlines/static
  icons, layout bindings and actual R8 field definitions/types. The full image verifier
  invokes this check and checks the existing release-key signing identity.

Actual camera availability, front/rear capture, flash, recording pause/resume,
focus/zoom, secure/single-capture intents, QR dismissal, settings scrolling, system bars
and physical E-Ink contrast need a device test; APK checks do not establish them.

Rollback the app patch, series entry and corresponding verifier requirements together.
The source pin may remain; no shared patch depends on this adaptation.
