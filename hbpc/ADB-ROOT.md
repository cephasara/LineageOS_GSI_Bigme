# Native adb root on normal builds

The normal HiBreak GSI is an actual `userdebug` product. Rooted debugging and
Android RSA host authorization remain in place; the optional `--debug-adb` flag
is a separate, unauthenticated diagnostic variant and is not required for this fix.

The inherited GSI personal policy patch removed `permissive su`, assuming the
domain is unused without a su executable. Native AOSP/Lineage adbd nevertheless
switches to `u:r:su:s0` after an allowed `adb root` request. The former normal
policy allowed that transition but denied access to FunctionFS endpoints. The
22.2 baseline and official 23.2 debug policy retain the upstream su behavior.

[0005-compat-native-adb-root-policy.patch](patches/hibreak/device_phh_treble/0005-compat-native-adb-root-policy.patch)
restores only that upstream domain behavior via a separate system_ext policy
directory. The product makefile includes it only for the **actual** `userdebug`
or `eng` build variant. A real `user` build, or an unset variant, does not include
it. This must be a real product-variable check: the inherited GSI policy compiler
forces its own variant to userdebug, making `userdebug_or_eng()` insufficient.
The public build entry point already checks its product is actual userdebug.

No adbd code, init service, auth setting, root permission check, USB trigger,
Magisk module or device-node permission is changed. There is no global
`setenforce 0`, wildcard allow or retry timer. Native su being permissive is a
real privilege boundary, limited to that domain; it must not be confused with
turning off SELinux globally or with unauthenticated ADB. The pre-existing PHH
permissive domains (`ueventd`, `tkcore`, `phhsu_daemon`, `backuptool`) are unchanged.
The image verifier enforces that this fix adds only su to that existing set,
checks the packaged APEX labels, and checks the normal root-setting/auth boundary.

Use USB debugging and approve the computer, enable Rooted debugging in developer
options, then run `adb root`. Enabling the setting alone only grants permission;
it does not itself restart adbd. `adb unroot` restores the normal daemon UID/domain.
Disabling Rooted debugging also clears the request and restarts adbd. Reconnecting
briefly during daemon restart is expected; persistent loss is not.

Build-time checks cannot establish behavior with the device's live vendor policy
(or a Magisk installation): a device test covers root/unroot, refused root when
disabled, RSA authorization, USB replug, reboot and scrcpy while SELinux remains
globally Enforcing. Magisk shells use a separate domain and are not a substitute for
testing native adbd.

This is an independent `native-adb-root` / `compat` entry in the ordered release
series. To revert, revert the corresponding Android source commit and public
feature commit while keeping later source/patch context consistent; do not reset
history or clear output/cache.
