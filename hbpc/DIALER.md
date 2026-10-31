# Dialer: paper/ink presentation

## Ongoing voice calls

The LineageOS 23.2 ongoing-call page belongs to **Dialer**, not SystemUI or the
Telecom service: `java/com/android/incallui/InCallActivity.java` hosts
`incall/impl/InCallFragment.java` / `frag_incall_voice.xml`.

`patches/hibreak/apps/Dialer/0001-paper-ink-ongoing-call.patch` restyles this page:

- Opaque white background; pure black text/icons in both day and night mode.
- No avatar, control, dialpad or audio-sheet elevation/shadow.
- Hang-up and call-control circles have 1dp (2px) black strokes. Checked controls
  have a 2dp edge; disabled controls have a dashed ring while text stays black. Focus/press feedback is static outlined feedback.
- In-call DTMF keys, the close button, audio routes, held-call banner and emergency
  number panel are white with 1dp outlines. Audio selection retains its existing
  selected state and shows a 2dp edge. There is no audio-sheet dim layer.
- Contact placeholders opt into white tiles/black initials and symbols via a
  local theme attribute. Actual contact photos are preserved, not recolored.
- White status/navigation bars use dark icons, including the keypad and restored
  activity. Leaving the voice screen restores the other call screen's bar policy.

Follows the [E-Ink UI convention](APP-ADAPTATION.md#e-ink-ui-convention): DTMF keys are separate outlined tiles; audio
route rows have no edge at rest inside the outlined sheet, which keeps its 28dp top
corners; white letter tiles get an ink ring.

## Boundaries

View hierarchy, bounds, spacing, icon padding, hit areas and call logic are
unchanged. The control background swap explicitly retains icon padding; inner
rings do not introduce drawable padding. Mute, speaker, hold, recording, DTMF,
Bluetooth routing, conference actions and accessibility semantics stay native.
No call is initiated by the validation tools.

The activity's base theme is unchanged: the paper/ink theme is applied to the
voice fragment and its DTMF instance, and (see below) the incoming voice call page,
not the video/RTT pages. The separate
main-page adaptation below does not broaden the voice patch's scope. The self-contained audio picker/hold banner and emergency-number panel
also keep this appearance when reused by another call screen. Contact-grid icon
tints follow their local text theme, preserving contrast on other call screens.
The static presentation below changes presentation scheduling only; call timers,
proximity handling, service lifecycle, DTMF and action dispatch remain native.

## Static presentation

The static presentation part of `0001-paper-ink-ongoing-call.patch` removes the dialpad
reveal. There were **two** animation paths: a legacy View slide on the whole panel
and `DialpadView.animateShow()` staggering the individual keys. Legacy View
`Animation`, frame drawables and marquee do not automatically obey the three
developer animation scales. Setting those scales to zero is not sufficient.

The voice screen now uses the existing synchronous show/hide branch, even when a
caller requests animation. This is important: the old slide-out completion hid
the fragment, so merely removing `startAnimation()` would leave the keypad open.
The same native visibility/button/proximity notifications still execute. The key
reveal entry point also rejects animation for the voice-call instance; RTT keeps
its original path and completion callback.

Nearby presentation audit:

| Source | Result |
| --- | --- |
| Voice/hold inset `TransitionManager`, contact-row `LayoutTransition` | Immediate final padding/visibility; no relayout tween. |
| Hold fragment slide resources | Removed the animation declaration (upstream placed it after operations, so it did not reliably animate those operations). |
| SIM switch frame animation | Uses the original static first/last frame; delegate called once, no drawable cast/start. |
| HD negotiation spinner + morph/scale | Voice-only static state selector: ringed HD while negotiating, normal HD when established. Other call screens retain their existing icon. |
| Four-second attachment preview auto-scroll | Same content timing/target, immediate page switch. |
| Morphing paginator dots | Static outlined/filled dots reflect the selected page, including restoration. |
| Connection-label marquee | Voice-only end ellipsis; text and accessibility content unchanged. |
| Audio picker enter/exit window animation | Explicitly disabled; native cancellation/route callbacks retained. |
| `ViewAnimator` for timer/text | No in/out animations configured; no change needed. |
| Button elevation/ripple resources | Already unreferenced by the new E-Ink controls; no additional change needed. |

Touch-driven attachment paging (including ViewPager settling), audio-sheet drag /
settling and its predictive-Back gesture remain native. Removing these requires
an interaction-policy change, not dropping visual callbacks. Incoming-answer,
video/RTT screens are not a whole-app motion rewrite. Main-keypad motion is handled
separately below.
Actual photos and the call chronometer are preserved.

## Incoming voice calls

`0004-paper-ink-incoming-call.patch` (feature `eink-dialer-answer`) restyles the
incoming-call (answer) page of a voice call to match the ongoing-call page:

- **Two buttons, no swipe.** Every incoming voice call shows **Decline** and **Answer**
  buttons instead of the swipe-up puck. Answer is a solid black circle with a white call
  icon; Decline is a white circle with a 1dp black ring and a black icon. Both have black
  labels. Pressing or focusing Answer inverts it (white with a 2dp edge); Decline gets the
  2dp edge. Sizes, touch areas and TalkBack descriptions are the stock two-button ones.
- **No motion.** The caller details appear in place (no slide/fade-in); a tap answers or
  declines at once (no shrinking buttons); hint text appears without a fade; the reply
  sheet opens and closes without animation or dimming.
- **Paper and ink.** White page and window, dark status/navigation icons, black text.
  The caller picture gets the ink ring of the ongoing-call page, for letter tiles and real
  contact photos alike; photos are not recoloured.
- **Plain taps for the other actions.** "Reject with message" and, during a call, "Answer
  and end ongoing call" are outlined text buttons below the two main buttons, always
  tappable (not only with TalkBack). They appear under the same conditions as the stock
  swipe icons, which are no longer shown. The message sheet is white and outlined with
  black rows; the custom message dialog uses the white dialog style of the main page.
- **One action per call.** After Answer, Decline, "Answer and end ongoing call" or a
  reply, further taps are ignored; the message sheet cannot open twice. The swipe-worded
  call-waiting hints are not shown (the outlined button names the action).

Incoming voice calls with real-time text (RTT) get this page too. Video calls and video
upgrade requests keep the stock page (swipe or two buttons, with
its camera preview and animations). Answering, declining, the reply flow, call waiting,
ringing, proximity, lock-screen display and the ongoing-call page behave as before.

Limits: a rich-call attachment (message or picture sent with the call, rare) is shown
with its stock styling.

## Main activity, search, favorites, history and keypad

`0003-paper-ink-main-page.patch` adds an independent `MainEink.Root` light theme.
`OldMainActivityPeer` is the active host and no longer reapplies its dark alias.
Day/night launch themes and compatibility aliases remain light. Search, navigation,
keypad controls and list actions use black outlines/static selection; primary FABs
remain black with white icons. Selection bars stay white with black labels.

The outline part of `0003-paper-ink-main-page.patch` corrects component-specific outline geometry
found during physical review. Empty-state actions use a white, black-label 28dp
capsule with 1dp, 2dp focus/press and dashed-disabled states. The collapsed
search bar keeps one resting capsule outline; its 48dp voice, menu, back and clear
targets are transparent at rest and gain a rounded 2dp edge only while focused
or pressed. Call-log foregrounds use the same 28dp radius as `CallLogCardStyle`, so
the `CardView` outline no longer clips rectangular corners. Expanded call-log rows
retain a rounded 2dp edge.

This is **not** a global `ThemeComponent` recoloring. That component is application
scoped and treats -1 (also opaque white) as an unset color sentinel. Shared
`DialpadView`, call-type icon painting and old photo loading opt in through the
main context's `mainEinkUi` attribute. Cached call-type drawables are not recolored
in place. The previous voice/answer/video/RTT behavior stays isolated.

Toolbar/search margins, bottom indicators, main-keypad reveal, row transitions and
FAB motion snap to their existing endpoints. Search start/end focus, keyboard,
query and background callbacks remain intact, including no focus request when
opening the keypad with a physical keyboard. Native fragment transactions, dial
intents, number validation, DTMF, drag/reorder and scrolling remain native. The
pseudo-emergency Easter egg retains its repeat/end-driven **haptic clock** but
suppresses color flashing in the main theme; no call behavior is substituted.

Placeholder tiles are white/black, actual photos are not recolored, and main photo
cross-fades are omitted. Dialog and popup backgrounds retain native AppCompat insets
and nine-patch density/padding/intrinsic metrics instead of replacing those
backgrounds with unpadded shapes; they have no stroke of their own, so the framework
window border draws their edge. Active states are plain shapes and add no padding. Checkbox/radio intrinsic bounds remain 32dp.

`verify-dialer-contacts.py` checks the real packaged resources and DEX class
definitions; it runs alongside the voice checks in image verification.

On-device acceptance still needs day/night, large font/RTL, search/clear/back,
physical-keyboard focus, tab selection, known/unknown photos, favorites drag,
keypad click/long-click/tones, default-dialer/permission transitions and selection
mode. APK checks do not initiate calls or validate Telecom or physical rendering.

Follows the [E-Ink UI convention](APP-ADAPTATION.md#e-ink-ui-convention): rows, borderless icons and tabs have no
frame at rest, so neighbours do not double their edges; dialpad keys are separate tiles;
the dialpad sheet keeps its 28dp top corners; the selected tab is a pill with a
double-width edge; the call-with-a-note card and its subject list are outlined.
Secondary screens (call details, settings) are not restyled.

## Verification / acceptance

The image verifier checks the installed Dialer theme, voice-layout theme binding,
static cues and outline units, plus the three packaged
[animation defaults](QUIET-UI.md#animation-scale-defaults).

The incoming-page check confirms the packaged two-button layout, button styles without
state animators, the static Answer circle, the outlined secondary actions, the avatar
outline and that the code uses the paper/ink layout, sheet and dialog themes.

Physical acceptance still needs a device: active incoming/outgoing voice calls,
unknown/known/conference contacts, mute/hold/speaker on/off, unavailable controls,
DTMF/close, Bluetooth route selection, call waiting and return to voice, activity
recreation, night mode, large font and proximity blank/unblank. Compilation and
resource checks do not prove actual call behavior or E-Ink raster quality.
