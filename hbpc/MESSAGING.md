# Messaging E-Ink presentation

The maintained `com.android.messaging` app uses an app-local ink/paper palette.
Its list, conversation, composer, contact picker, menus, settings and provider
widgets retain their existing layout and actions. This follows the
[style-only app adaptation constraint](APP-ADAPTATION.md).

- Light and night configurations both use opaque white surfaces, black text and
  black controls. Force-dark is disabled on the app themes, system-bar icon
  appearance stays dark, and the action bar keeps its explicit white background.
  The app's primary control role is black, independently of its white app bar.
- Text bubbles retain their original shapes/positions and receive a one physical-
  pixel outline. Selected bubbles use a three-pixel outline. Runtime styling
  changes fill/stroke separately, since tinting the entire drawable would erase
  the black border. Incoming/outgoing alignment, sender/status labels, unread
  bold type and selection/checkmark semantics are retained.
- The composer, send button, start-chat button, contact chips, popups and snackbar
  use white/outlined styling. Pressed/focused/selected controls have direct border
  feedback. Invalid contact chips use a dashed outline. Native text selection
  uses an opaque light-gray highlight so black glyphs remain readable; native
  disabled-state affordances and media-selection tint are preserved.
- Generated avatars use white circles, black letters/glyphs and a one-pixel
  border. Actual contact photos and image/video content are unchanged. SIM names
  are black; the existing SIM icon/identifier and selected-state inversion remain.
  Neither the chosen SIM nor saved contact-color options/values are changed.
- Media-picker tabs use black glyphs and an outlined selected state; audio controls
  retain their native state inversion and timers. Shared photo-viewer action
  glyphs resolve their own theme's foreground role to stay readable there.
- App popups/ripples, widget title/avatar shadows, and decorative elevation are
  flattened. Provider widget bubbles and contact popups wrap their original
  nine-patches, retaining intrinsic sizing/content padding while adding an outline.
  Ordinary AppCompat/Material menus also retain their native background insets/padding
  beneath the new outline, including the original popup nine-patch. Dialog windows keep
  their native insets with 28dp corners and take their edge only from the framework
  window border (no second outline). Former shadow gradients (compose and chips
  dividers) are single 1px lines; audio progress tracks are light grey under the black
  progress. Raster assets are not rewritten.
- Existing resource-driven compose, media-panel, snackbar, swipe-settle, FAB and
  reveal durations finish at zero through the same Animation/Animator completion
  paths. Swipe thresholds, scrolling, callbacks, media recording/playback, GIFs,
  SMS/MMS dispatch, read marking, permissions and lifecycle are not rewritten.
  This does not claim every animation inside external media components is removed.

No framework/product capability or user-facing switch is added. The feature is
owned by `patches/hibreak/apps/Messaging/`; retain the preceding personal Messaging
patches in the public ordered chain.

Offline verification checks resource XML, unchanged view hierarchy/geometry and
non-style attributes, preserved data/action/preferences and raster source files,
production `messaging` compilation, full source replay and the normal packaged
GApps image. The image verifier requires the ink/paper roles, day/night white
surfaces, light system bars, composer outline and zero visual durations.

A device test should cover unread/read and
selected lists; new SMS, reply, MMS attachments, failure/status display and links;
text selection/copy; valid/invalid recipients and contact suggestions; dual-SIM
labels/selection; menus, settings and dialogs; widget list/conversation views;
large fonts, RTL and media playback. Offline checks do not establish E-Ink refresh
quality or actual sending/receiving on the device.
