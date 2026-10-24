# Contacts: app-local paper/ink presentation

`com.android.contacts` is pinned at `02bbe49b4ed8e8094d9573ff52747ff8050d9813`.
`patches/hibreak/apps/Contacts/0001-paper-ink-contacts.patch` adapts list/search,
selection/drawer, editor and QuickContact presentation without redesigning their
layout or changing contact data operations.

## Appearance and boundaries

- Explicit platform/AppCompat light roots, including the full `values-v27` theme
  duplicates and night palette; white system bars with dark icons.
- Black text/icons, white backgrounds, 1dp (2px) control/row outlines, a 2dp edge
  for selected/pressed/focused and dashed disabled outlines. Existing primary FAB is black/white.
  Checkbox/radio intrinsic bounds stay 32dp; inset outlines add no padding.
- Native popup nine-patch padding/density/intrinsic dimensions are retained. The
  app's existing custom dialog background had no padding; that remains unchanged.
  Dialogs and popup menus have no stroke of their own: the framework window border
  draws their edge.
- Photo-derived palette no longer colors toolbar/status bar/actions. White toolbar
  backing and black action tint are separate roles. Real photos keep their native
  decode/cache/crop path without filters or cross-fades; only built-in placeholder
  artwork is inked. Toolbar/title backing stays within the original view bounds.

No contacts are created, saved, imported, deleted or called by verification.
Providers, save/import/export services, preferences, permission/manifest policy,
editor save dispatch and PeopleActivity navigation are preserved. Layout XML
keeps its hierarchy, IDs, dimensions, padding, constraints, text and accessibility
attributes. Two XML tags use subclasses of their original widgets solely for the
presentation bridges below; they do not introduce or remove hierarchy nodes.

Follows the [E-Ink UI convention](APP-ADAPTATION.md#e-ink-ui-convention): rows, list items, drawer items and
borderless icons have no frame at rest; the search back arrow is ink; the call-with-a-note
card and subject list, the navigation drawer (1px end line) and the empty-state buttons
(outlined pills) are outlined; QuickContact cards use a 28dp edge that matches their clip;
white letter tiles get an ink ring.

## Motion and callbacks

| Path | Presentation change / retained behavior |
| --- | --- |
| Search/selection action bar, FAB | Existing final visibility/position and completion work, no tween. |
| Editor/card expansion/removal | Zero child delay/duration; listeners installed before start, guarded end. Removal/focus cleanup still completes. |
| QuickContact entrance | Same native scroll target, completion once at the final value. |
| Back/background-tap dismissal | Zero-duration native animator, dismissal-start notification before potentially synchronous finish. |
| Finger-driven scroll/dismiss/fling | Native input and release physics, not replaced by jump or synthetic gestures. |
| Header pinning, masking, call-subject history | Static decoration; original coordinates/visibility and completion callbacks. |
| Drawer | App-local `EinkDrawerLayout` forces programmatic open/close to native nonanimated branches; drag/release and native drawer callbacks remain. |
| Swipe refresh | App-local same-package bridge finishes the native image-view animation at zero duration, preserving `onRefresh`; only the spinning drawable stops and shows one static arc. |
| Other indeterminate progress | Static `Animatable` drawable, avoiding ProgressBar's otherwise implicit infinite AlphaAnimation fallback. Real progress/loading completion is not frozen. |

The swipe bridge intentionally depends on bundled AndroidX
`swiperefreshlayout 1.2.0-alpha01` (`mCircleView`, `mProgress`), and the drawer on
`drawerlayout 1.3.0-alpha01`. Keep rules and the APK verifier check actual class and
field definitions and versions. Re-review on library updates; string presence in
DEX alone is not an ABI check.

## Verification / physical acceptance

- `verify-dialer-contacts.py`: actual APK identity, resources, night/API parents,
  outlines/choice bounds/native wrappers, reflective progress class, bridge fields.
  Integrated into `verify-hibreak.py`; Contacts must retain the shared signing key.

These are not on-device UI, provider, permission or rendering tests. Physical
acceptance needs day/night, RTL/large fonts, real/placeholder photos, search and
selection, drawer open/close and drag, refresh/error/completion, QuickContact back/
entrance/fling, editor add/remove/save/cancel, account/permission changes and import
flows. Do not infer data safety or exact E-Ink appearance solely from compilation.
