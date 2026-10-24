# HiBreak custom keys: consume F1/F2; configurable Page Up/Down

The two remapped case buttons no longer also send F1/F2 to foreground apps (a fix in the
E-Ink accessibility service), and Page Up/Page Down are available as button actions.

## Cause and boundary

The previous `A9AccessibilityService.onKeyEvent` recognized scan codes 59/60, invoked
the gesture detector, then returned `super.onKeyEvent(event)` (**false**). Its custom
action therefore did not consume the original key. The service already declares both
`canRequestFilterKeyEvents` and `flagRequestFilterKeyEvents`.

This explains the leak in this GSI. Kernel `getevent` output still containing
`KEY_F1`/`KEY_F2` is expected: this fix consumes Android delivery, not raw driver events.

The device-owned patch is
[Consume built-in custom keys and add page actions](patches/hibreak/device/vendor_a9_services/0001-consume-built-in-custom-keys.patch)
(feature `hardware-keys`).

It follows the `vendor/a9_services` baseline patch. No kernel, keylayout, InputReader
or framework key-policy changes. The case buttons come from `mtk-kpd`, an internal
keyboard; its Android device ID varies between boots and is not hard-coded.

## Key routing and gesture behavior

- Only scan 59/60 from the **internal, non-virtual, non-external `mtk-kpd` keyboard**
  are consumed. Other keys, unknown devices, external keyboards' F1/F2 and injected
  virtual keys retain their normal dispatch. Scan 59 keeps the existing bottom-button
  mapping and scan 60 the top-button mapping; no preference renaming.
- Ownership follows `(deviceId, scanCode, downTime)` through UP, including when the
  device lookup disappears. A reused device ID with another downTime does not inherit
  ownership. Orphan UP/repeat/MULTIPLE events from the case keys are swallowed without
  creating gestures. Fresh DOWN after a lost UP cancels that stale gesture first.
- Return `true` for recognized streams, including “Nothing”. Copy accepted events before
  queuing them on a dedicated main-thread handler; the framework recycles the original.
  Action/socket calls do not run inline in the key-filter callback. There is no
  overlay-permission prompt: the app runs as the system uid and its panel is an
  accessibility overlay.
- Preserve platform single/double/long timeout values and action preference dispatch.
  Repeated/duplicate DOWN never resets a gesture. A first press near boot is not a
  phantom double; a third rapid press starts another gesture; holding the second press
  of a recognized double does not additionally fire a long action. A short press after
  a long press is not a double. `FLAG_CANCELED`, interrupt and destruction cancel pending
  work. Cancellation cannot undo an action that has already been dispatched.
- Top/bottom detectors and all twelve existing screen-on/off preference keys/defaults
  remain independent. Existing screen-state selection at gesture dispatch is retained.
- Defaults for both buttons: with the screen on, single press clears the screen and double
  press opens the E-Ink menu; long press and every screen-off press do nothing. The service
  and the settings page read the same table (`ButtonActionManager.default`).

**Service-layer limitation:** Android's accessibility key-filter deadline is 500 ms.
Deferring action work avoids spending that deadline inside this callback, but a disabled,
crashed or already-unresponsive service can still miss filtering or time out. This is
not an unconditional system-layer interception guarantee; that would be separate work.

## Page Up / Page Down

The new values `page_up` and `page_down` are **appended** to the screen-on action list;
all old values, positions, defaults and persisted choices are retained. English and
Simplified Chinese labels are provided. Both buttons' single/double/long-press slots
can select either action. Screen-off options are unchanged, like existing navigation
actions (Back/Home/Recents); no preference migration or automatic selection is added.

`PageButtonAction` accepts only `KEYCODE_PAGE_UP` / `KEYCODE_PAGE_DOWN` (92/93). It sends
one ordinary DOWN/UP pair with matching downTime, zero repeat/meta/scan code and virtual
keyboard identity/source. Native `InputManager` **asynchronous** injection avoids waiting
for dispatch back through accessibility; the injected keys cannot match the physical
filter. No shell commands, daemon extension, media-key substitution or forced swipe.

The app explicitly requests the signature-only `INJECT_EVENTS` permission using its
existing platform signature/system UID. No new exported component or arbitrary-key
injection endpoint is added; the privileged-permission allowlist is unchanged because
this is not a signature|privileged permission. Injection rejection/security failure is
logged without retrying an action or falling back to F1/F2. A DOWN is always balanced:
if its UP is not accepted, a cancelled UP is sent at once, or else before the next page
action and when the service is interrupted or destroyed, so the key never stays pressed.

At action dispatch the device must be interactive and keyguard unlocked; missing system
services fail closed. A lock/sleep occurring during the double-tap wait therefore skips
the page action. This action does not wake or unlock the device. As with a normal keyboard,
subsequent focus changes and actual Page Up/Down handling belong to Android/the focused
app. **Apps must support these keys**; no universal page-turn behavior is promised.

## Verification

The normal image check (`verify-eink-hardware-keys.py`, run by `verify-hibreak.py`)
inspects the packaged APK: package, accessibility capabilities, the signature
permission, the filter and handler classes, and the paired localized action arrays.
It does not test input delivery or latency on a device.

To check on the phone, use a foreground key logger or terminal and a reader that
supports Page Up/Page Down: case-key single/double/long/Nothing must not deliver
F1/F2; page mappings deliver one balanced page-key pair; USB/Bluetooth keyboard F1/F2
stay available. Also try repeats, both buttons at once, service interruption, lock and
sleep transitions and the screen-off actions.

Rollback the corresponding patches, series entries and verifier requirements together.
