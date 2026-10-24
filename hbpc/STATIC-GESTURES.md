# Static system gesture navigation

This is an explicitly requested system interaction change for reflective displays.
It is separate from style-only application adaptations and does not modify app-owned
Back callbacks, progress generation or app-internal navigation animations.

## Configuration

- Framework `config_staticSystemGestures` defaults false: enables a pure opaque
  black/white gesture handle and fixed-position, discrete SystemUI Back feedback.
- Framework `config_predictiveBackAnimation` defaults true: HiBreak sets false to
  prevent WM from preparing system remote Back previews (Home, cross-task,
  cross-activity and dialog-close). The native callback/target-selection path remains.
- Launcher `config_staticSystemGestures` defaults false: HiBreak enables it for
  Home/Overview gestures and the Launcher-owned handle.

The product overlays enable these policies together. They do not change gesture
navigation backgrounds, navigation dimensions or Insets. Only the handle itself
is made opaque; its underlying safe area keeps Android's transparent treatment.
The existing three-button opaque policy remains scoped to three-button mode.

## Interaction

- Back: retain edge eligibility, gesture exclusions and input interception in
  EdgeBackGestureHandler. After inward travel reaches the larger of the native
  16dp activation resource and edge slop, show the glyph instantly at the originating
  screen edge's vertical midpoint. Keep fixed size/position and black/white fill.
  Retreat below a separate slop-based threshold or a predominantly vertical move
  hides the glyph. Release commits exactly once; ACTION_CANCEL never commits.
  Static mode uses distance-based arming instead of animation delays/fling-only
  feedback states. Lineage's optional long-swipe action retains its threshold and
  Shell dispatch path, with no ordinary Back executed ahead of it.
- App → Home/Overview: retain native distance, velocity, pause and target selection.
  Keep the running task visually stationary during the gesture. On release, finish
  through the existing navigation callbacks at the selected endpoint; the Home
  rectangle publishes a final frame without starting springs. No workspace reveal.
- Home → Overview: preserve pause recognition, show Overview on release when still
  paused; otherwise stay on Home. ACTION_CANCEL keeps Home. No hint-state movement
  or overview drag/stretch occurs while waiting for release.
- Overview/All Apps → Home: preserve target recognition with deferred visual
  progress and immediate completion/cancellation. Split cleanup still runs.
- Handle: choose only pure white or pure black based on the existing appearance /
  background-sampling source, without color interpolation, partial alpha or a
  long-press pulse. Keep the parent container opaque in low-profile mode and use
  zero tint-transition duration. Do not paint a matching floor behind it.

## Verification and maintenance

Export framework/SystemUI, Launcher and enabling product overlays as separate
ordered feature patches. The normal image verifier checks both packaged policies
and product activation. Host tests exercise the production static Back recognizer;
Android compilation checks SystemUI, Launcher and window-manager integration.
Actual touch, task switching, rotation, IME, PiP and physical E-Ink feedback need a
device test; offline checks do not establish those results.
