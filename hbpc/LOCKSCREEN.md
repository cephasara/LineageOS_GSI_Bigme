# Static black/white lockscreen and PIN

HiBreak SystemUI product policy `bool/config_einkKeyguard` enables a static
high-contrast keyguard. The resource belongs to `SystemUICustomizationLib` so
SystemUI and its clock implementations share it; the library default is false
and the HiBreak SystemUI overlay fixes it to true. It is not a user setting.
There is no added framework resource or public API. PIN and the fingerprint sensor
keep their existing Android credential checking and biometric authorization paths.

## Interaction

- The existing bottom device-entry icon becomes an ordinary clickable unlock
  action. It retains the system `ic_lock` / `ic_unlocked` vector states, with a
  white circular background and a black whole-pixel outline (about 1dp, 2px). Native
  positioning and hit area remain; no new navigation-bar background is added.
  Accessibility exposes the unlock action. Tap falsing, screen/keyguard state
  checks and ordinary View click cancellation apply. No long press is required.
- A secure lockscreen swipe keeps its visible panel at the initial endpoint
  while recording native gesture position. Both initial touch ownership and
  later interception use this policy. On release, native distance/velocity,
  falsing and cancellation rules select the endpoint. Only an accepted gesture
  opens the complete primary bouncer. It does not provisionally display the
  PIN page during MOVE. Fingerprint completion while tracking cannot request a
  new PIN page after authentication has taken over.
- This iteration does **not** lower swipe thresholds. The visible button gives
  an alternative that does not require swipe distance or velocity. It still
  enters the normal security-mode selection; it does not dismiss a secured
  keyguard without authentication.
- PIN entry and return to lockscreen use static endpoints. Existing tracking,
  fling completion, bouncer state, focus and authentication callbacks remain.

## Presentation

- Keyguard/bouncer scrim surfaces are opaque white. This is a presentation
  override, not a change to the stored wallpaper preference. The existing
  navigation safe area gets no extra background layer.
- Default and Flex clock faces use black instead of wallpaper/seed-derived
  lockscreen colors. Clock style, format and layout choices remain. Date,
  smartspace text, status icons and keyguard indications receive compatible
  black text/tint. Third-party clock plugin rendering is not rewritten.
- PIN digit/action keys use white backgrounds, black text/icons and whole-pixel
  outlines (about 1dp, 2px), retaining their existing layout. Press feedback swaps black/white
  immediately; there is no radius morph, text stretch or delayed contraction.
  The PIN entry field and emergency button also have black outlines.
- Six-slot auto-confirm hints use white outlined empty circles and filled black
  circles. Other PIN lengths append/delete black circles immediately. Clearing
  does not stagger dots or queue later additions. Input values, auto-confirm
  selection and accessibility text-change events use the existing input model.
- PIN container drag distance is recorded without translating the keyboard;
  release preserves retry/dismiss callbacks and cancellation, with no spring.
- PIN appearance/disappearance, key/error motion, dot animation, message fades,
  clock charge/fidget effects, keyguard transition animators and unlock ripples
  are made static in the covered paths. Original completion callbacks are kept.
  The product's existing Animator/window/transition scales of zero remain.
- Wrong-PIN and timed-lockout instructions remain explicit black text. Attempt
  accounting, lockout, emergency actions and actual credential checks are not
  changed by the styling.

## Verification

Source regression cases cover immediate key feedback without morphing, hinted
and non-hinted PIN updates/reset, accepted swipe release, cancellation and
falsing rejection, and stationary PIN drag with release/cancel callbacks. Build/test results are recorded with the delivered image;
source tests alone do not imply execution or device validation.

The initial focused `SystemUiRoboTests` attempt did not execute tests: existing
screen-recording, system-event, battery and Wi-Fi test fixtures fail to compile
against their current interfaces. Production SystemUI compilation succeeded.
These unrelated fixture repairs are outside this change.

The packaged-image verifier requires the SystemUI default-false resource and
enabling SystemUI product overlay, and rejects a framework copy of the resource.
Export SystemUI/framework behavior and product activation as separate ordered
patches and replay the full series before the normal GApps build.
Shared patch 0015 follows 0014 to preserve native message alpha behavior when
the product policy is disabled; patch 0016 removes container drag/spring motion
while preserving logical gesture distance. Shared 0017 and defaults 0008 move
the policy from framework-res to SystemUI; retain the complete feature chain.

The initial framework location shifted 382 private bool resource IDs compared
with the previous accepted image (public IDs stayed stable). Standard overlays
map by name, but prebuilt vendor code using private numeric IDs cannot be
excluded offline. Localizing the policy avoids that unnecessary compatibility
exposure. Transition code uses injected SystemUI resources rather than global
`Resources.getSystem()`, and the common clock library uses its host resources.

A device test covers: tap versus drag-out on the lock button; short/long/cancelled upswipes; PIN typing,
delete/clear/confirm; incorrect PIN feedback; returning to lockscreen; fingerprint
from lockscreen and PIN, including while an upswipe is in progress; repeated
sleep/wake; notification, large-font, landscape and accessibility layout. The
source/build checks cannot establish physical E-Ink refresh quality.

While the screen is off, the [E-Ink sleep screen](SLEEP-SCREEN.md) covers the dozing
keyguard; it uses the same `config_einkKeyguard` policy and leaves the static keyguard
and PIN behavior documented here unchanged.
