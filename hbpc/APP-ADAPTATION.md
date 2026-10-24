# E-Ink app adaptation constraints

Rule:

> 不改布局，只改样式，不改逻辑，避免 Bug。 (Do not change layout, only style; do not
> change logic; avoid bugs.)

Application adaptation defaults to **style changes only**. Preserve layout and
behavior to limit regressions. This applies to maintained system applications,
including DeskClock and its widgets, Launcher and the E-Ink settings app.

## E-Ink visual policy

- Use pure white ordinary surfaces and pure black text/icons. Delineate
  interactive components with pure black outlines, not shadows or translucent
  fills. Draw within existing bounds without changing padding or touch targets.
- Pure black fills with pure white text/icons may distinguish emphasis, selection
  and other special states. Pair foreground and background consistently.
- Dashed black outlines are also available where appropriate (for example disabled
  controls); preserve readable, distinguishable states and native enabled semantics.
- Disable all decorative UI animation: window/element transitions, fades, scaling,
  rotation tweens, ripples, animated icons, scrolling/settling effects and spinners.
  Show the intended static state. Preserve required completion callbacks, visibility,
  accessibility and action ordering; never just cancel a behavior-driving animator.
  Actual content updates (camera preview, recording time, task progress, countdown)
  are not decorative animation and must retain their real timing and meaning.
- Prefer declaring an explicitly light app theme; do not actively switch the app
  to dark mode. Keep dialogs, settings, launch windows and system bars consistent:
  light status/navigation-bar appearance means dark icons on a light background.
  Review runtime edge-to-edge/bar calls as well as XML and night/API variants.
- Media, camera preview and other user content are not UI surfaces to recolor.
  Keep camera exposure/flash, capture and other functional effects intact.

This policy authorizes presentation-only removal of motion, not changes to gesture
acceptance, navigation destinations, scheduling or application state machines.

## E-Ink UI convention

Why it is needed: the E-Ink palette makes every tonal surface white
([`external_libmonet/0001`](patches/hibreak/external_libmonet/0001-HiBreak-Pro-Color.patch)),
and flat windows remove shadows, dim and blur
([`frameworks_base/0001`](patches/hibreak/frameworks_base/0001-HiBreak-Pro-Color.patch)).
A surface that used to stand out by tone or shadow now needs an explicit edge. The
framework draws one only for floating windows and popups (`FlatWindowBorder`).

- **R1 One edge, one owner.** Floating windows (dialogs, popups, menus) get their edge
  only from `FlatWindowBorder`; do not stroke their window background too. In-window
  surfaces carry their own stroke, or a Compose `border`. Windows, cards and controls
  use a whole-pixel edge of about 1dp: `1dp` in XML (2px at 300dpi), `round(density)`
  px in code and Compose. Only dividers are 1px. The colour is the ink of the
  surface's own theme (`colorForeground`, `colorOnBackground`, `onSurface`), never
  derived from the system night mode.
- **R2 Selection** is shown by inversion (black fill, white ink) or a double-width edge,
  never by a container tone. Disabled stays grey or dashed.
- **R3 Tracks.** Inactive slider and progress tracks use one light grey (`#BDBDBD`);
  active tracks are black.
- **R4 Corners.** 28dp for windows and sheets, 20dp for in-page cards and groups, 12dp
  for small controls, a pill for buttons, chips and tiles, 0 for full-bleed bars. A
  stroke always follows the clip shape. Children of a stroked container are unstroked
  or inset by the stroke width.
- **R5 No stacked lines.** Adjacent edges must not double up into 2+2px seams, and an
  edge must not sit right next to another edge.
- **R6 Strokes survive tinting.** If code tints or colour-filters a background, put the
  stroke in an untinted layer, or skip the tint on flat devices.
- **R7 Bars** (app bars, bottom bars, sheets' fixed headers) get a single 1px line on
  the side that faces content.
- **R8 Feedback.** Press shows a visible grey or an inversion; focus is a ring that
  follows the shape; no permanent square frames on targets that are not containers.

Decisions: Dialer's secondary screens (call details, settings) are not restyled.
Colour overrides that are no-ops under the default palette stay. Grey container tones
are not brought back.

## Allowed scope

- Adjust semantic surface/content colors and disabled-state contrast.
- Replace translucent fills and shadows with opaque fills and thin outlines.
- Correct icon/text tint and theme inheritance; retain readable state distinctions.
- Change drawable styling and visual feedback without changing action dispatch,
  state transitions or required animation-completion side effects.
- Update a style option's label only when necessary to describe its new appearance;
  retain option count, order, stored values and selection behavior.

Prefer resources, styles and theme tokens. Small Java/Kotlin changes that resolve
or apply a visual color are still styling; the rule concerns behavior, not file
extensions. Keep strokes and tints from obscuring content or altering touch areas.

## Preserved boundaries

- Keep view hierarchy, positioning, dimensions, padding, spacing, touch targets,
  scrolling, expansion and navigation structure unchanged.
- Keep click/gesture handling, selection semantics and enabled/disabled state.
- Keep preferences, defaults, persistence, initialization and migrations unchanged.
- Keep alarms, timers, refresh scheduling, permissions, services and lifecycle
  behavior unchanged. When removing an animation whose completion drives application
  behavior, retain its final state and required completion side effects on the native
  execution path; verify ordering, interruption and repeated use.

A requested layout or behavior feature is separate work with an explicit scope
and its own patch. Do not bundle it into E-Ink restyling. Already authorized
functional changes remain authorized; this rule is not an extra approval gate.
For example, the separately requested framework navigation-inset policy is not
a Clock application styling change.

## Patch ownership and review

Maintain application patches under `patches/hibreak/apps/<App>/`, such as
`apps/DeskClock`. A widget belongs to its provider, even when another app hosts it.
Shared framework/library changes and their enabling product overlays belong in
`shared/` and `defaults/` respectively; see [PATCHES.md](PATCHES.md).

Use separate commits and ordered patches for independently reviewable changes.
Review light/dark resource variants, existing widgets and saved selections,
disabled states and adjacent screens that reuse a changed style. Build and
resource checks do not prove physical E-Ink quality; record device validation
separately. Avoid generic view-tree rewriting or app-name branches in shared code.

The DeskClock widget patch keeps the original widget preference default. Existing and
new widgets keep their original selection logic; Plain and Outlined describe the two
restyled appearances. No preference migration is added.

See [Aperture](APERTURE.md) for the camera application of this policy,
including library-completion boundaries and device acceptance checks.
