# SELinux ioctl extended permissions

Patch: [`compat/system_core/0001-selinux-xperms-by-policy-version.patch`](patches/hibreak/compat/system_core/0001-selinux-xperms-by-policy-version.patch)
(feature `selinux-xperms`, category `compat`).

The inherited TrebleDroid init changes strip every ioctl extended-permission rule
(`allowx`, `auditallowx`, `dontauditx`, `neverallowx`) and cap the compiled policy at
version 29 on any kernel older than 5.4. That includes this phone's 4.19 kernel, which
supports them (policy version 30, Linux 4.3 and later), so the ioctl restrictions of
the platform and vendor policy were silently dropped.

init now decides from the kernel's maximum policy version: `/sys/fs/selinux/policyvers`
of 30 or more keeps the full policy. Only if that file cannot be read does it fall back
to the kernel-version heuristic. If the full policy fails to compile or load, init
retries once on the legacy path (strip and cap to 29), so the device still boots.

Switches (read before properties exist, so they are files or boot parameters):

- `/metadata/hibreak/selinux_legacy_xperms` (any content, needs root) forces the legacy
  path at the next boot; delete it to return to the full policy.
- `androidboot.selinux_no_xperms=1` / `androidboot.selinux_xperms_supported=1` on the
  kernel command line or in bootconfig. The inherited code read these with `getenv()`
  and never saw them.

```sh
adb shell dmesg | grep 'SELinux: '   # "kernel policyvers 31, xperms supported",
                                     # "xperms path: full"; no "stripped N xperms"
adb shell cat /sys/fs/selinux/policyvers
```
