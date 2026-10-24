# HiBreak WWAN registration-service reconnect refresh

## Purpose / limits

Stock MTK checks a disconnected registration service and polls after reconnection.
This is a narrower event-driven counterpart, added after a SIM stayed unregistered
from the mobile network: **one additional native state-change notification after a
successful service reconnection/rebinding**. This is not a demonstrated root-cause fix.

Only `frameworks/opt/telephony/.../NetworkRegistrationManager.java` changes.
No stock class/JAR transplant, periodic service checks, radio/modem/RIL reset,
new AIDL operation, poll coalescing, APN/RAT/selection policy, IMS policy or data
setup retry change. It does not initiate rebinding or fix a service that never
reconnects. It cannot force a modem that still reports no registration to camp.

## Exact scope and lifetime

- Exact exported identity: vendor manufacturer `Bigme`, model `HiBreak`, board
  `mt6877`, checked by the patch itself. WWAN only; IWLAN and other devices retain
  native behavior.
- Record a successful current binding only after `linkToDeath`, provider creation
  and callback registration calls return without `RemoteException`.
- **First successful binding is unchanged**. A later successful binding or reconnect
  posts a one-shot action to the manager Handler, which notifies the existing
  registration-state registrants; ServiceStateTracker then performs its native poll.
- Duplicate connection/binder/disconnect-generation callbacks do not add another
  notification. A disconnect advances the connection generation; reconnecting the
  same Binder is still recognized. Explicit unbind/rebind uses a new connection.
- At dispatch, check current connection, disconnect generation, current/live Binder,
  device/transport scope and enable switch again. Queued obsolete work is skipped.
- Normal provider indications and request completion callbacks remain untouched.
  They are not coalesced with the synthetic notification, so a nearby genuine
  indication can still produce its own native poll. No timers or retry budget.
- Binding bookkeeping is updated on the Context ServiceConnection callback thread;
  the disconnect generation is volatile for the manager Handler's dispatch guard.

## Ordering and what “successful” means

`INetworkService` is a oneway Binder interface. Its calls on the same Binder node
are ordered; local calls enter the same wrapper directly. The framework
`NetworkService.INetworkServiceWrapper` enqueues provider creation, indication
registration and registration-info requests onto its one Handler.

The additional poll is requested only after the creation and registration calls,
so its queries follow those operations in that service queue. **There is no new
provider-ready acknowledgement**: return from oneway registration means the call
was submitted, not proof of a valid provider or modem readiness. Custom carrier
services and failed provider creation retain their native completion/failure
behavior. No guessed delay or private MTK command is used to work around it.

## Diagnostic / rollback

Event-based, non-identifying radio log markers (slot/transport already in NRM tag):

- `HBPC_NRM_RECONNECT refresh`: one synthetic notification dispatched.
- `HBPC_NRM_RECONNECT skip=stale_or_disabled`: queued work invalidated before dispatch.

These are **not** proof of restored service or internet. Correlate subsequent WWAN
registration, data setup and validation using the existing host cellular collector.
The marker is not expected on first binding or on ordinary coverage changes that
never disconnect/rebind NetworkService.

`persist.radio.hibreak_nrm_refresh=true` enables the added notification on the exact
target device/WWAN; absent or `false` means **disabled (default)**, because the refresh
is not a demonstrated fix. It uses the existing `persist.radio`
SELinux property type; privileged property-write access is required. No property is
set on the device by this task. Binding history is still observed while disabled,
so enabling applies to a later reconnect without requiring a synthetic disconnect.
The switch is checked before queueing and dispatch. Queries already handed to the
native tracker are not cancelled.

## Verification and packaging

- `verify-hibreak.py` checks the packaged `telephony-common` markers; marker presence
  is a packaging check, not a behavioral proof. The radio property-type gates remain.
- Kernel Binder scheduling, Context rebinding, real carrier providers, modem behavior
  and phone calls need a device test.
- Ordered device patch:
  `patches/hibreak/device/frameworks_opt_telephony/0002-refresh-registration-after-reconnect.patch`.
  Apply the maintained full series, not this category as an independent switch.
