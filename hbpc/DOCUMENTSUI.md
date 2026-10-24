# DocumentsUI: static paper and ink

`com.android.documentsui` with no animation or shadows, pure white surfaces, pure black
text and **1 physical pixel** emphasis borders. The Dialer call adaptation is not
changed here.

## App-local implementation

[Ordered app patch](patches/hibreak/apps/DocumentsUI/0001-static-paper-ink-documentsui.patch)
on pinned DocumentsUI `860ac584e6b4c8b99a9ba9777d4784e076bc9e5b`.
The same patch completes the static drawer paths and draws visible list separators.
The additional `res-eink` resource directory overrides only DocumentsUI resources;
no framework, shared library, product theme or stored setting is changed.
The paper/ink theme is applied after native dynamic colors. Matching day/night,
API and Material 3 resource variants prevent wallpaper/night palettes returning.

- White pages, navigation/search surfaces, rows, menus, dialogs, buttons and job
  panels; black text, hints and semantic control tints. Thumbnails, provider-supplied
  icons, launcher artwork and the native editor selection treatment remain content.
- Static 1px outlines for focused/selected/pressed/hovered rows and controls.
  Native selected checkmarks remain. Disabled file rows/tabs use dashed outlines;
  primary inactive action buttons omit their emphasis border rather than gray labels.
  Keyboard type-to-focus matches use underlining, not black-on-black highlight fills.
- Drawer boundary is a **foreground** 1px black line at logical END (right in LTR,
  left in RTL), so white child backgrounds cannot cover it. Main file-list rows
  have permanent black 1px separators, not full item frames or grid stripes. The decoration paints inside row bounds above backgrounds,
  skips synthetic header/spacer rows and the final item, clips to the viewport and
  allocates no layout offsets. Existing row padding, selection and hit areas stay.
- Native widget parents, view hierarchy, dimensions, spacing and touch targets
  are retained. Material popup 4dp corners and 8dp vertical padding are retained.
  Styling dimensions (elevation/stroke) are the only dimension-token changes.
- Material dialog builder only wraps the existing background: native shape,
  padding/insets and action callbacks remain. App-owned drawables avoid the
  shared renderer's extra density-scaled window outline, and draw their own 1px
  stroke. Their empty platform outline also prevents a shadow; no shared policy
  is changed. XML-inflated drawable constructors are retained through R8.

Follows the [E-Ink UI convention](APP-ADAPTATION.md#e-ink-ui-convention): on-colours on black (primary,
secondary, tertiary, error, success) are white, so the grid check mark and the drag copy
badge show; list rules skip selected or focused rows and their neighbours; the current
breadcrumb is plain (it is disabled by design, not unavailable); checked filter chips are
inverted; the snackbar keeps its edge under its white tint; the sort sheet strokes the
shape drawable that BottomSheetBehavior installs.

## Motion and behavior boundaries

Directory transitions preserve state-restoration arguments without fragment
animations. RecyclerView item animations are disabled; list/grid/photo checkmarks
use the existing immediate final-state branches. Thumbnail and inspector images
appear at their intended final alpha without crossfade. Sort arrows finish their
native vector state immediately; layout tweens and chip-reorder tweens are removed.
Chip ordering, accessibility notifications and search callbacks remain.

All public drawer open/close overloads now converge on native immediate paths.
If a prior peek/release is still settling, native zero-distance settling discards
that stale target without adding new opening/closing flags or cancelling a live
finger drag. This prevents a subsequent frame undoing an explicit immediate open.

Outside-tap close, edge peeking and release/cancel paths can bypass those public
methods. Three existing DrawerLayout nodes use the app-local direct subclass
`DocumentsDrawerLayout`: before drawing it finishes only settling scrollers at
**their native destinations**, then lets `super.computeScroll()` move the actual
children, update offsets and defer native IDLE/open/close/accessibility/back
callbacks out of drawing. No fabricated callbacks, guessed fling destination,
reflection into framework classes, gesture rewrite or shared AndroidX patch.
Finger-following dragging remains; the drawer's automatic settling motion does not.

The bundled library has no public duration control: this adapter reads only its
`mLeftDragger`, `mRightDragger` and `mScroller` fields, cached at construction.
R8 keeps those fields; the APK verifier checks actual DEX **definitions/types** and
DrawerLayout 1.3.0-alpha01 / CustomView 1.2.0-alpha03 version metadata. A library
upgrade must be re-reviewed, not silently accepted based on matching strings.
Unexpected runtime incompatibility logs a warning and falls back to native
completion rather than breaking file access. Do not replace scroller completion
with `ViewDragHelper.abort()` (pointer cancellation / no child movement), or
`continueSettling(false)` from drawing (premature callbacks).

The sidebar and breadcrumb RecyclerViews also disable their previously retained
default item animators; those and the main file list suppress decorative overscroll
stretch without disabling ordinary scrolling. Immediate keyboard scroll transfers
its focus callback from the now-absent scroll-IDLE event to a one-shot post-layout
pre-draw callback, including the missing-item and failed-focus cases.

Material duration tokens, window animations and popup transitions are static.
Progress uses Material's native animator-off path, including the indeterminate-to-
determinate callback. Task progress, errors, cancellation, timeout and completion
remain real; a static busy cue does not assert task completion. Pull-to-refresh
retains its native drag/settle-completion machinery, but replaces the rotating
glyph. Ordinary scrolling and sheet/refresh gestures remain native; the drawer change
specifically removes drawer automatic settling, not every other gesture mechanism.
File-service scheduling is untouched.

The shipping flags are Material3=true, Peek=false and search-v2=false. Material 3 is
switched on at runtime by Lineage's static DocumentsUIOverlay (`force_material3`), and
the app maps every legacy layout, style and drawable to its M3 twin, so the patch only
overrides resources the M3 path uses. This patch neither enables nor claims coverage
for the compiled-out Peek preview/new search UI.
No global animation scale is changed. Existing files, grants, preferences and
selection models are unchanged.

## Verification

- `verify-documentsui.py` (run by the image verifier) checks the packaged APK: theme
  colors, all 16 zero motion tokens, day/night surfaces, 1px static outlines, popup
  padding, the XML-inflated drawable and the optimized library field definitions in
  the packaged DEX, the drawer bindings and the foreground edge.
- Layouts only substitute the direct DrawerLayout subclass tag; hierarchy and
  nonvisual attributes remain unchanged.

Actual provider operations, keyboard/navigation, dialog appearance and E-Ink raster
quality need a device test; compilation and resource inspection do not prove them.

Rollback app patches, their series entries and corresponding verifier requirements together.
The manifest pin may remain; no shared patch or call adaptation depends on this app.
