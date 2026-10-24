# Launcher workspace swipes commit on release

This is an **interaction change**, separate from the
[default style-only app adaptation rule](APP-ADAPTATION.md).

Patches (feature `launcher-swipe-on-release`):

- [`apps/Launcher3/0001-commit-workspace-swipes-on-release.patch`](patches/hibreak/apps/Launcher3/0001-commit-workspace-swipes-on-release.patch)
- [`defaults/device_phh_treble/0003-enable-launcher-swipe-on-release.patch`](patches/hibreak/defaults/device_phh_treble/0003-enable-launcher-swipe-on-release.patch)
  sets `config_swipeOnRelease` (false upstream) to true.

Workspace page swipes keep their initial visual state while the finger moves. On
release, the original distance/velocity target selection is used, and the result is
displayed without a settling animation. Retreating below the distance threshold keeps
the current page unless the existing fling rule selects another target. Cancellation
keeps the current page. No edge pull is drawn.

PagedView still records total motion and velocity. Only the normal Workspace opts in;
folder paging, Overview, icon dragging and generic keyboard/mouse navigation keep their
existing behavior. Release and cancel use the existing immediate page snap, so page
callbacks and bookkeeping still run.

Home ↔ All Apps uses the [static drawer](LAUNCHER-DRAWER.md) (`config_staticAllApps`),
which opens and closes at a distance threshold. The patch also provides the deferred
state playback that the [static system gestures](STATIC-GESTURES.md) use: progress is
recorded without applying it to child animations, transition-start callbacks wait for
release, and a zero-duration endpoint animation runs through the normal completion
path. This does not alter Android predictive-back or application navigation gestures.

The patch adds tests for deferred playback and the workspace page thresholds, retreat,
cancellation, fling selection and the first-page boundary. They are not part of the
image build and have not been run.

To revert, set `config_swipeOnRelease` back to false (drop the defaults patch). The app
patch must stay while static system gestures are enabled, since they use its deferred
playback.
