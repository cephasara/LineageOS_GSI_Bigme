#!/usr/bin/env python3
"""Verify the packaged release-preparation GSI, including removed debug behavior."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('image', type=Path)
parser.add_argument('--tree', type=Path, required=True)
parser.add_argument('--out', type=Path, required=True)
parser.add_argument('--keys', type=Path, required=True)
parser.add_argument('--debug-adb', action='store_true')
parser.add_argument('--variant', choices=['vanilla', 'gapps'], default='vanilla')
args = parser.parse_args()
tree, out, keys = args.tree.resolve(), args.out.resolve(), args.keys.resolve()

def run(*cmd, data=None):
    return subprocess.check_output([str(c) for c in cmd], input=data)

with tempfile.TemporaryDirectory(prefix='hibreak-image-') as directory:
    work = Path(directory)
    image = work / 'system.img'
    image.symlink_to(args.image.resolve())
    subprocess.run(['e2fsck', '-fn', str(image)], check=True)
    subprocess.run(['python3', str(tree / 'external/avb/avbtool.py'),
                    'verify_image', '--image', str(image)], check=True)
    def read(path, optional=False):
        r = subprocess.run(['debugfs', '-R', 'cat ' + path, str(image)],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        if not optional and (not r.stdout or b'File not found' in r.stderr):
            raise RuntimeError('missing image file: ' + path)
        return r.stdout
    def apk(path, name):
        dest = work / name
        dest.write_bytes(read(path))
        return dest
    def resources(path):
        return run(tree / 'prebuilts/sdk/tools/linux/bin/aapt2', 'dump', 'resources', path).decode()
    def dex(path):
        with zipfile.ZipFile(path) as archive:
            return b''.join(archive.read(n) for n in archive.namelist() if n.endswith('.dex'))
    props_text = read('/system/build.prop').decode()
    props = dict(line.split('=', 1) for line in props_text.splitlines()
                 if '=' in line and not line.startswith('#'))
    expected = {'ro.secure': '1', 'ro.adb.secure': '1', 'persist.sys.usb.config': 'none',
                'ro.system.build.version.sdk': '36', 'ro.system.build.type': 'userdebug',
                'ro.build.user': 'hibreak', 'ro.build.host': 'local', 'ro.build.tags': 'release-keys',
                'ro.bigme.force_client_composition': 'true',
                'persist.vendor.xrz.fps': '120',
                'ro.vendor.xrz.phy_rotation': '270', 'ro.vendor.xrz.screen_type': '61',
                'debug.sf.nobootanimation': '1', 'ro.surface_flinger.supports_background_blur': '0',
                'persist.accessibility.enabled_service':
                    'net.dianqk.hibreak.eink/net.dianqk.hibreak.eink.A9AccessibilityService'}
    for key, value in expected.items():
        actual = [line.split('=', 1)[1] for line in props_text.splitlines() if line.startswith(key + '=')]
        if not actual or set(actual) != {value}:
            raise RuntimeError(f'wrong image property: {key}={actual}')
    number = props.get('ro.build.version.incremental', '')
    suffix = r'\.debug-adb' if args.debug_adb else ''
    if not re.fullmatch(r'HBPC\.23\.2\.P1\.\d{8}\.\d{6}\.g[0-9a-f]{8}' + suffix, number):
        raise RuntimeError('unexpected build number: ' + number)
    if number not in props.get('ro.build.display.id', '') or 'eng.dianqk' in props_text:
        raise RuntimeError('Settings build number does not use the release identity')
    debug_rc = read('/system/etc/init/hibreak-debug-adb.rc', optional=True)
    # Check the packaged daemon, not just build.prop or the source checkout.
    with zipfile.ZipFile(io.BytesIO(read('/system/apex/com.android.adbd.apex'))) as archive:
        payload = work / 'adbd-apex.img'
        payload.write_bytes(archive.read('apex_payload.img'))
    adbd = run('debugfs', '-R', 'cat /bin/adbd', payload)
    if not adbd.startswith(b'\x7fELF'):
        raise RuntimeError('packaged ADB daemon is missing')
    debug_marker = b'HIBREAK_DEBUG_ADB: host authentication disabled'
    debug_contexts = read('/system/etc/selinux/plat_property_contexts')
    debug_property = b'ro.bigme.debug_adb u:object_r:build_prop:s0 exact bool'
    if args.debug_adb:
        if debug_property not in debug_contexts:
            raise RuntimeError('debug ADB property is not readable as a build property')
        if props.get('ro.bigme.debug_adb') != 'true' or debug_marker not in adbd or \
                b'settings put global adb_enabled 1' not in debug_rc:
            raise RuntimeError('debug ADB image is incomplete')
    elif 'ro.bigme.debug_adb' in props_text or debug_rc or debug_marker in adbd or \
            b'ro.bigme.debug_adb' in debug_contexts:
        raise RuntimeError('opt-in debug ADB leaked into a normal image')
    adbd_rc = run('debugfs', '-R', 'cat /etc/init.rc', payload)
    if b'--root_seclabel=u:r:su:s0' not in adbd_rc or b'seclabel u:r:adbd:s0' not in adbd_rc:
        raise RuntimeError('native adbd domain configuration missing')
    if not args.debug_adb and b'ADB Root access is disabled by system setting' not in adbd:
        raise RuntimeError('normal adbd lost the system root-setting gate')
    policies = [read(p).decode() for p in [
        '/system/etc/selinux/plat_sepolicy.cil',
        '/system/system_ext/etc/selinux/system_ext_sepolicy.cil',
        '/system/product/etc/selinux/product_sepolicy.cil']]
    permissive_domains = set(re.findall(r'\(typepermissive\s+(\S+)\)', '\n'.join(policies)))
    # Four pre-existing PHH compatibility domains; this fix adds only native su.
    expected_permissive = {'ueventd', 'tkcore', 'phhsu_daemon', 'backuptool', 'su'}
    if permissive_domains != expected_permissive:
        raise RuntimeError('unexpected packaged permissive domains: ' + repr(permissive_domains))
    print('PASS: native root domain restored; existing PHH domain set unchanged; ADB flavor checks passed')
    for token in ['ro.bigme.insecure_adbd', 'ro.bigme.boot_diagnostics',
                  'ro.boot.apex.early_adbd', 'persist.logd.logpersistd',
                  'init.svc_debug.no_fatal', 'log.tag=V']:
        if token in props_text:
            raise RuntimeError('diagnostic property retained: ' + token)
    for path in ['/system/bin/bigme-bootdiag', '/system/etc/init/bigme-bootdiag.rc',
                 '/system/etc/bigme-boot-diagnostics',
                 '/system/system_ext/priv-app/BigmeDebugProvision/BigmeDebugProvision.apk',
                 '/system/system_ext/priv-app/SetupWizard/SetupWizard.apk',
                 '/system/system_ext/priv-app/LineageSetupWizard/LineageSetupWizard.apk']:
        if read(path, optional=True):
            raise RuntimeError('retired debug/setup payload retained: ' + path)
    for path in ['/system/bin/qcom-atel-ready', '/system/etc/init/qcom-atel-ready.rc',
                 '/system/app/QcRilAm/QcRilAm.apk', '/system/priv-app/QcRilAm/QcRilAm.apk',
                 '/system/bin/slsi-booted', '/system/etc/init/slsi-booted.rc',
                 '/system/bin/xiaomi-motor', '/system/bin/oneplus-motor', '/system/bin/asus-motor',
                 '/system/bin/hw/android.hardware.biometrics.fingerprint@2.1-service.oppo.compat',
                 '/system/bin/hw/android.hardware.biometrics.fingerprint@2.1-service.oplus.compat',
                 '/system/bin/oplus-alert-slider', '/system/etc/init/oplus-alert-slider.rc',
                 '/system/bin/xiaomi-touch']:
        if read(path, optional=True):
            raise RuntimeError('other-vendor payload installed: ' + path)
    print('PASS: other-vendor helpers (Qualcomm, Samsung LSI, Xiaomi, OnePlus, ASUS, Oppo) absent')
    # The prebuilt TrebleApp declares these as optional uses-library and links their
    # classes directly; a missing class is a NoClassDefFoundError that crashes it.
    interfaces = read('/system/etc/permissions/interfaces.xml').decode()
    for name, jar, cls in [
            ('android.hidl.manager.V1_0', 'android.hidl.manager-V1.0-java', b'Landroid/hidl/manager/V1_0/IServiceManager;'),
            ('vendor.huawei.hardware.biometrics.fingerprint.V2_1', 'vendor.huawei.hardware.biometrics.fingerprint-V2.1-java',
             b'Lvendor/huawei/hardware/biometrics/fingerprint/V2_1/IExtBiometricsFingerprint;'),
            ('vendor.huawei.hardware.tp.V1_0', 'vendor.huawei.hardware.tp-V1.0-java', b'Lvendor/huawei/hardware/tp/V1_0/ITouchscreen;'),
            ('vendor.qti.hardware.radio.am.V1_0', 'vendor.qti.hardware.radio.am-V1.0-java', b'Lvendor/qti/hardware/radio/am/V1_0/IQcRilAudio;'),
            ('vendor.qti.qcril.am.V1_0', 'vendor.qti.qcril.am-V1.0-java', b'Lvendor/qti/qcril/am/V1_0/IQcRilAudio;')]:
        path = '/system/framework/' + jar + '.jar'
        if not re.search(r'<library name="' + re.escape(name) + r'"\s+file="' + re.escape(path) + '"', interfaces):
            raise RuntimeError('TrebleApp library not declared in interfaces.xml: ' + name)
        with zipfile.ZipFile(io.BytesIO(read(path))) as archive:
            if cls not in archive.read('classes.dex'):
                raise RuntimeError('TrebleApp library lacks its classes: ' + path)
    print('PASS: TrebleApp optional HIDL Java libraries (hidl.manager, Huawei, qti am) packaged and declared')
    for path in ['/system/bin/init', '/system/bin/surfaceflinger']:
        if b'BIGME_BOOT_DIAGNOSTICS' in read(path):
            raise RuntimeError('custom boot logger retained in ' + path)
    # P1-2: xperms kept when the kernel's policy version supports them, legacy fallback.
    init_binary = read('/system/bin/init')
    for marker in [b'SELinux: xperms path: ', b'/sys/fs/selinux/policyvers',
                   b'/metadata/hibreak/selinux_legacy_xperms',
                   b'SELinux: policy with xperms rejected; loading it without xperms']:
        if marker not in init_binary:
            raise RuntimeError('SELinux xperms policy-version decision missing: ' + repr(marker))
    print('PASS: SELinux xperms by kernel policy version with legacy fallback')
    rw = read('/system/bin/rw-system.sh')
    subprocess.run(['bash', '-n'], input=rw, check=True)
    if b'ro.bigme.insecure_adbd' in rw or b'ro.keymaster.xxx.security_patch "$spl"' not in rw:
        raise RuntimeError('PHH startup fixes or debug removal are incomplete')
    if hashlib.sha256(read('/system/eink_key')).hexdigest() != '69804441c70e866d81e0a80dfb762a993076c1325e41aee1d604925c20f977a1':
        raise RuntimeError('factory XRZ key mismatch')
    for name in ['elan_ktf', 'fts_ts_pen']:
        if b'touch.orientation = ORIENTATION_270' not in read('/system/usr/idc/' + name + '.idc').replace(b'touch.orientation=', b'touch.orientation = '):
            raise RuntimeError('touch orientation missing: ' + name)
    sf = read('/system/bin/surfaceflinger')
    for marker in [b'BIGME_DISPLAY: forcing client composition',
                   b'BIGME_DISPLAY: preserving client composition',
                   b'Ignoring invalid boot hotplug before Scheduler initialization']:
        if marker not in sf:
            raise RuntimeError('display startup fix missing: ' + repr(marker))
    env = dict(os.environ, JAVA_HOME=str(tree / 'prebuilts/jdk/jdk21/linux-x86'))
    env['PATH'] = env['JAVA_HOME'] + '/bin:' + env['PATH']
    roles = {
        '/system/framework/framework-res.apk': 'platform',
        '/system/system_ext/priv-app/HiBreakProvision/HiBreakProvision.apk': 'platform',
        '/system/system_ext/priv-app/SystemUI/SystemUI.apk': 'platform',
        '/system/system_ext/priv-app/Settings/Settings.apk': 'platform',
        '/system/priv-app/A9AccessibilityService/A9AccessibilityService.apk': 'platform',
        '/system/priv-app/HbpcMtkIms/HbpcMtkIms.apk': 'platform',
        '/system/priv-app/DocumentsUI/DocumentsUI.apk': 'platform',
        '/system/product/app/Aperture/Aperture.apk': 'releasekey',
        '/system/priv-app/ContactsProvider/ContactsProvider.apk': 'shared',
        '/system/product/priv-app/Contacts/Contacts.apk': 'shared',
        '/system/priv-app/DownloadProvider/DownloadProvider.apk': 'media',
        '/system/priv-app/NetworkStack/NetworkStack.apk': 'networkstack',
        '/system/app/BasicDreams/BasicDreams.apk': 'releasekey'}
    certificates = {}
    for role in set(roles.values()) | {'bluetooth', 'nfc', 'sdk_sandbox'}:
        certificates[role] = run('openssl', 'x509', '-in', keys / (role + '.x509.pem'), '-outform', 'DER')
    for path, role in roles.items():
        report = subprocess.check_output([str(out / 'host/linux-x86/bin/apksigner'),
            'verify', '--print-certs', str(apk(path, 'signature.apk'))], text=True, env=env)
        signers = re.findall(r'Signer #\d+ certificate SHA-256 digest: ([0-9a-f]+)', report)
        if signers != [hashlib.sha256(certificates[role]).hexdigest()]:
            raise RuntimeError('APK signature mismatch: ' + path)
    # Android 16 selects the Bluetooth SELinux certificate separately from the
    # other mainline keys. Check both the APEX-contained APK and its policy below.
    with zipfile.ZipFile(io.BytesIO(read('/system/apex/com.android.bt.apex'))) as archive:
        bt_payload = work / 'bluetooth-apex.img'
        bt_payload.write_bytes(archive.read('apex_payload.img'))
    entries = run('debugfs', '-R', 'ls -p /app', bt_payload).decode().splitlines()
    folders = [row.split('/')[5] for row in entries if len(row.split('/')) > 5
               and re.fullmatch(r'Bluetooth(?:@[A-Za-z0-9_.+-]+)?', row.split('/')[5])]
    if len(folders) != 1:
        raise RuntimeError('missing or ambiguous Bluetooth APK in APEX: ' + repr(folders))
    bt_apk = work / 'bluetooth.apk'
    bt_apk.write_bytes(run('debugfs', '-R', 'cat /app/' + folders[0] + '/Bluetooth.apk', bt_payload))
    report = subprocess.check_output([str(out / 'host/linux-x86/bin/apksigner'),
        'verify', '--print-certs', str(bt_apk)], text=True, env=env)
    if re.findall(r'Signer #\d+ certificate SHA-256 digest: ([0-9a-f]+)', report) != \
            [hashlib.sha256(certificates['bluetooth']).hexdigest()]:
        raise RuntimeError('Bluetooth APK signature does not match the local policy identity')
    permissions = read('/system/etc/selinux/plat_mac_permissions.xml').decode()
    for role in ['platform', 'media', 'networkstack', 'bluetooth', 'nfc', 'sdk_sandbox']:
        if certificates[role].hex() not in permissions:
            raise RuntimeError('SELinux signer mismatch: ' + role)
    product = 'lineage_arm64_bgN4' if args.variant == 'gapps' else 'lineage_arm64_bvN4'
    overlay = resources(apk('/system/product/overlay/framework-res__' + product + '__auto_generated_rro_product.apk', 'framework-overlay.apk'))
    if not re.search(r'integer/config_defaultNightMode\n\s+\(\) 1\b', overlay):
        raise RuntimeError('light theme default missing')
    if not re.search(r'integer/config_defaultRefreshRate\n\s+\(\) 40\b', overlay):
        raise RuntimeError('40 Hz default render rate missing')
    for name in ['config_flatWindowAppearance', 'config_staticTouchFeedback',
                 'config_einkStaticTextCursor', 'config_disableTransitionAnimation',
                 'config_opaqueThreeButtonNavigation', 'config_staticSystemGestures']:
        if not re.search(r'bool/' + name + r'\n\s+\(\) true', overlay):
            raise RuntimeError('E-Ink shared UI overlay missing: ' + name)
    if not re.search(r'bool/config_batterySaver_full_enableNightMode\n\s+\(\) false', overlay):
        raise RuntimeError('battery saver light-mode policy missing')
    # Check the packaged product overlays: source XML alone does not prove RRO coverage.
    framework = resources(apk('/system/framework/framework-res.apk', 'framework-res.apk'))
    if re.search(r'resource 0x[0-9a-f]+ bool/config_einkKeyguard\b', framework):
        raise RuntimeError('keyguard policy must remain local to SystemUI, not framework-res')
    # Public framework entries can carry PUBLIC / STAGED_ID suffixes.
    def framework_color(name):
        match = re.search(r'resource (0x[0-9a-f]+) color/' + re.escape(name) + r'\b', framework)
        if not match:
            raise RuntimeError('framework color ID missing: ' + name)
        return '@' + match.group(1)
    def require_value(table, name, value, qualifier=''):
        # A resource may have a default value before its night/other qualified values.
        # Limit the search to this entry so another resource cannot satisfy the check.
        entry = re.search(r'resource 0x[0-9a-f]+ ' + re.escape(name)
                          + r'\n(.*?)(?=\n\s*resource |\Z)',
                          table, re.S)
        if not entry or not re.search(r'^[ \t]+\(' + re.escape(qualifier)
                                      + r'\) ' + re.escape(value) + r'(?=\s|$)',
                                      entry.group(1), re.M):
            raise RuntimeError('packaged E-Ink resource mismatch: ' + name + ' = ' + value)
    require_value(overlay, 'bool/config_predictiveBackAnimation', 'false')
    # Verify that shared disabled-text tokens and the app-owned widget ship in the image.
    settings_resources = resources(apk('/system/system_ext/priv-app/Settings/Settings.apk',
                                       'settings.apk'))
    require_value(settings_resources, 'color/settingslib_text_color_disabled', '#ff606060')
    clock_resources = resources(apk('/system/product/app/DeskClock/DeskClock.apk', 'clock.apk'))
    require_value(clock_resources, 'color/eink_widget_surface', '#ffffffff')
    require_value(clock_resources, 'color/eink_widget_ink', '#ff000000')
    require_value(clock_resources, 'color/eink_widget_secondary_ink', '#ff444444')
    def style_block(table, name):
        match = re.search(r'(?m)^    resource 0x[0-9a-f]+ style/' + re.escape(name)
                          + r'\n([\s\S]*?)(?=^    resource |\Z)', table)
        if not match:
            raise RuntimeError('packaged style missing: ' + name)
        return match.group(1)
    for name in ['Theme.DeskClock', 'Theme.DeskClock.DigitalWidgetConfigurationTheme']:
        block = style_block(clock_resources, name)
        variants = [v for v in re.split(r'(?m)(?=^      \([^\n]*\) \(style\))', block)
                    if '(style)' in v]
        for variant in variants:
            if 'parent=style/Theme.Material3Expressive.DynamicColors.Light.NoActionBar ' not in variant:
                raise RuntimeError('Clock light theme parent missing: ' + name)
            for attr, value in [('windowLightStatusBar', 'true'),
                                ('windowLightNavigationBar', 'true'), ('forceDarkAllowed', 'false')]:
                attr_id = re.search(r'resource (0x[0-9a-f]+) attr/' + attr + r'\b', framework)
                if not attr_id or attr_id.group(1) + '=' + value not in variant:
                    raise RuntimeError('Clock system-bar appearance missing: ' + name + '/' + attr)
    if 'parent=style/Theme.Material3Expressive.DynamicColors.Light.NoActionBar ' not in style_block(
            clock_resources, 'Theme.Toolbar.Settings'):
        raise RuntimeError('Clock secondary toolbar still uses a dark theme')
    on_surface = re.search(r'resource (0x[0-9a-f]+) attr/colorOnSurface\b', clock_resources).group(1)
    for name in ['ic_settings', 'ic_ringtone', 'ic_ringtone_silent']:
        icon = run(tree / 'prebuilts/sdk/tools/linux/bin/aapt2', 'dump', 'xmltree',
                   work / 'clock.apk', '--file', 'res/drawable/' + name + '.xml').decode()
        if not re.search(r':tint\([^)]*\)=\?' + on_surface, icon):
            raise RuntimeError('Clock action icon tint missing: ' + name)
    messaging_apk = apk('/system/product/app/messaging/messaging.apk', 'messaging.apk')
    messaging_resources = resources(messaging_apk)
    require_value(messaging_resources, 'color/eink_ink', '#ff000000')
    require_value(messaging_resources, 'color/eink_paper', '#ffffffff')
    # Resource optimization may coalesce identical day/night entries. Any retained
    # qualifier must resolve to the same app-local role, with a default fallback.
    for name, value in [
            ('color/window_background', '@color/eink_paper'),
            ('color/compose_send_text_background_color', '@color/eink_paper'),
            ('color/attachment_bg_color', '@color/eink_paper'),
            ('color/lineage_accent', '@color/eink_ink'),
            ('color/fab_fg_color', '@color/eink_ink')]:
        require_value(messaging_resources, name, value)
        entry = re.search(r'resource 0x[0-9a-f]+ ' + re.escape(name)
                          + r'\n(.*?)(?=\n\s*resource |\Z)',
                          messaging_resources, re.S).group(1)
        if any(v.strip() != value for v in re.findall(r'^\s+\([^\n]*\) ([^\n]+)',
                                                       entry, re.M)):
            raise RuntimeError('Messaging night/qualified palette mismatch: ' + name)
    for name in ['mediapicker_transition_duration', 'compose_transition_duration',
                 'snackbar_translation_duration_ms', 'swipe_duration_ms',
                 'fab_animation_duration_ms', 'reveal_view_animation_duration']:
        require_value(messaging_resources, 'integer/' + name, '0')
    messaging_theme = style_block(messaging_resources, 'BugleBaseTheme')
    if 'parent=style/Theme.MaterialComponents.Light ' not in messaging_theme:
        raise RuntimeError('Messaging light theme missing')
    for attr, value in [('windowLightStatusBar', 'true'),
                        ('windowLightNavigationBar', 'true'), ('forceDarkAllowed', 'false')]:
        attr_id = re.search(r'resource (0x[0-9a-f]+) attr/' + attr + r'\b', framework)
        if not attr_id or attr_id.group(1) + '=' + value not in messaging_theme:
            raise RuntimeError('Messaging system-bar appearance missing: ' + attr)
    messaging_outline = run(tree / 'prebuilts/sdk/tools/linux/bin/aapt2', 'dump', 'xmltree',
                            messaging_apk, '--file',
                            'res/drawable/msg_bubble_input_rounded.xml').decode()
    ink_id = re.search(r'resource (0x[0-9a-f]+) color/eink_ink\b',
                       messaging_resources).group(1)
    if 'E: stroke' not in messaging_outline or '1.000000dp' not in messaging_outline \
            or '@' + ink_id not in messaging_outline:
        raise RuntimeError('Messaging composer outline missing')
    # The dialog window keeps the native inset (28dp corners) and its edge comes from the
    # framework window border; alerts and popups wrap the native drawables.
    for wrapper, original in [('eink_dialog_background', 'dimen/appcompat_dialog_background_inset'),
                              ('eink_alert_background', 'drawable/abc_dialog_material_background'),
                              ('eink_popup_background', 'drawable/abc_popup_background_mtrl_mult')]:
        wrapped = run(tree / 'prebuilts/sdk/tools/linux/bin/aapt2', 'dump', 'xmltree',
                      messaging_apk, '--file', 'res/drawable/' + wrapper + '.xml').decode()
        native_id = re.search(r'resource (0x[0-9a-f]+) ' + original + r'\b',
                              messaging_resources)
        if not native_id or '@' + native_id.group(1) not in wrapped:
            raise RuntimeError('Messaging native background padding missing: ' + wrapper)
    dialer_apk = apk('/system/product/priv-app/Dialer/Dialer.apk', 'dialer.apk')
    dialer_resources = resources(dialer_apk)
    voice_theme = style_block(dialer_resources, 'Theme.InCallScreen.Eink')
    if 'parent=style/Theme.AppCompat.Light.NoActionBar ' not in voice_theme:
        raise RuntimeError('Dialer voice-call light theme missing')
    for attr, value in [('textColorPrimary', '#ff000000'),
                        ('textColorSecondary', '#ff000000'),
                        ('colorBackground', '#ffffffff'), ('forceDarkAllowed', 'false')]:
        attr_id = re.search(r'resource (0x[0-9a-f]+) attr/' + attr + r'\b', framework)
        if not attr_id or attr_id.group(1) + '=' + value not in voice_theme:
            raise RuntimeError('Dialer voice-call theme mismatch: ' + attr)
    for name in ['incall_eink_button_normal', 'incall_eink_panel',
                 'incall_eink_avatar_outline']:
        outline = run(tree / 'prebuilts/sdk/tools/linux/bin/aapt2', 'dump', 'xmltree',
                      dialer_apk, '--file', 'res/drawable/' + name + '.xml').decode()
        if 'E: stroke' not in outline or '1.000000dp' not in outline or '#ff000000' not in outline:
            raise RuntimeError('Dialer whole-pixel 1dp outline missing: ' + name)
    if not re.search(r'incallStaticUi\(0x[0-9a-f]+\)=true', voice_theme):
        raise RuntimeError('Dialer voice-call static presentation flag missing')
    hd_icon = run(tree / 'prebuilts/sdk/tools/linux/bin/aapt2', 'dump', 'xmltree',
                  dialer_apk, '--file', 'res/drawable/incall_eink_hd_icon.xml').decode()
    if 'E: selector' not in hd_icon or 'E: animated-' in hd_icon:
        raise RuntimeError('Dialer HD state icon still animated')
    audio_theme = style_block(dialer_resources, 'IncallEinkAudioRouteDialog')
    window_animation_attr = re.search(r'resource (0x[0-9a-f]+) attr/windowAnimationStyle\b',
                                      framework).group(1)
    if window_animation_attr + '=@null' not in audio_theme:
        raise RuntimeError('Dialer audio-sheet window animation not disabled')
    voice_layout = run(tree / 'prebuilts/sdk/tools/linux/bin/aapt2', 'dump', 'xmltree',
                       dialer_apk, '--file', 'res/layout/frag_incall_voice.xml').decode()
    voice_theme_id = re.search(r'resource (0x[0-9a-f]+) style/Theme.InCallScreen.Eink\b',
                               dialer_resources).group(1)
    if '@' + voice_theme_id not in voice_layout:
        raise RuntimeError('Dialer voice layout does not apply the paper/ink theme')
    contacts_apk = apk('/system/product/priv-app/Contacts/Contacts.apk', 'contacts.apk')
    print(run('python3', Path(__file__).with_name('verify-dialer-contacts.py'), dialer_apk, contacts_apk,
              '--aapt2', tree / 'prebuilts/sdk/tools/linux/bin/aapt2',
              '--framework', work / 'framework-res.apk').decode(), end='')
    telephony_jar = apk('/system/framework/telephony-common.jar', 'telephony-common.jar')
    telephony_code = dex(telephony_jar)
    for marker in [b'Lcom/android/internal/telephony/data/HiBreakMtkDataRetry;',
                   b'Lcom/android/internal/telephony/data/HiBreakMtkDataSettingsSync;',
                   b'persist.radio.hibreak_mtk_retry', b'persist.radio.hibreak_md_data_sync']:
        if marker in telephony_code:
            raise RuntimeError('retired MTK data retry/sync code still packaged: ' + repr(marker))
    for marker in [b'persist.radio.hibreak_nrm_refresh', b'HBPC_NRM_RECONNECT refresh',
                   b'HBPC_NRM_RECONNECT skip=stale_or_disabled', b'ro.product.vendor.manufacturer',
                   b'ro.product.vendor.model', b'ro.board.platform']:
        if marker not in telephony_code:
            raise RuntimeError('packaged NRM reconnect refresh missing: ' + repr(marker))
    print('PASS: packaged one-shot HiBreak WWAN reconnect refresh and rollback marker')
    for marker in [b'Lcom/android/internal/telephony/HiBreakOosRadioRecovery;',
                   b'persist.radio.hibreak_oos_recovery', b'HBPC_OOS_RECOVERY',
                   b'ril.hibreak.oos_recovery.', b'noteNetworkScan']:
        if marker not in telephony_code:
            raise RuntimeError('packaged out-of-service radio recovery missing: ' + repr(marker))
    # The kill switches (persist.radio.*) and the status property (ril.*) need the
    # existing radio_prop labels the phone process may read and set.
    if not re.search(rb'^persist\.radio\s+u:object_r:radio_prop:s0(?:\s|$)',
                     debug_contexts, re.M):
        raise RuntimeError('telephony kill switches lack the existing radio property label')
    if not re.search(rb'^ril\.\s+u:object_r:radio_prop:s0(?:\s|$)', debug_contexts, re.M):
        raise RuntimeError('out-of-service recovery status property lacks the radio property label')
    print('PASS: packaged out-of-service radio recovery, status and rollback properties')
    # nr-off-on-wifi: runtime NR mask while Wi-Fi is the default network (kill switch above label).
    for marker in [b'Lcom/android/internal/telephony/HiBreakNrOffOnWifi;',
                   b'persist.radio.hibreak_nr_off_on_wifi', b'HBPC_NR_WIFI',
                   b'setHiBreakNrBlockedOnWifi']:
        if marker not in telephony_code:
            raise RuntimeError('packaged NR-off-on-Wi-Fi missing: ' + repr(marker))
    print('PASS: packaged no-NR-while-Wi-Fi-is-default with kill switch')
    documents_apk = apk('/system/priv-app/DocumentsUI/DocumentsUI.apk', 'documentsui.apk')
    print(run('python3', Path(__file__).with_name('verify-documentsui.py'), documents_apk,
              '--aapt2', tree / 'prebuilts/sdk/tools/linux/bin/aapt2',
              '--framework', work / 'framework-res.apk').decode(), end='')
    aperture_apk = apk('/system/product/app/Aperture/Aperture.apk', 'aperture.apk')
    print(run('python3', Path(__file__).with_name('verify-aperture.py'), aperture_apk,
              '--aapt2', tree / 'prebuilts/sdk/tools/linux/bin/aapt2',
              '--framework', work / 'framework-res.apk').decode(), end='')
    sysui_apk = apk('/system/system_ext/priv-app/SystemUI/SystemUI.apk', 'systemui.apk')
    sysui_resources = resources(sysui_apk)
    require_value(sysui_resources, 'bool/config_einkKeyguard', 'false')
    services_jar = apk('/system/framework/services.jar', 'services.jar')
    # Resource shrinking removes legacy implementations disabled by release flags.
    # Require the active 23.2 ringer background; validate any retained legacy pieces too.
    with zipfile.ZipFile(sysui_apk) as archive:
        sysui_files = set(archive.namelist())
    for name in ['volume_dialog_ringer_background', 'volume_dialog_background_joined']:
        if 'res/drawable/' + name + '.xml' not in sysui_files:
            raise RuntimeError('active volume background missing: ' + name)
    for name in ['volume_dialog_ringer_background', 'volume_dialog_background_joined']:
        if 'res/drawable/' + name + '.xml' not in sysui_files:
            continue
        shape = run(tree / 'prebuilts/sdk/tools/linux/bin/aapt2', 'dump', 'xmltree',
                    sysui_apk, '--file', 'res/drawable/' + name + '.xml').decode()
        if 'E: stroke' not in shape or not re.search(r':width\([^)]*\)=1(?:\.0+)?dp', shape):
            raise RuntimeError('Volume top outline missing: ' + name)
        if name in ['volume_dialog_ringer_background', 'volume_dialog_background_joined']:
            edge = 'Bottom' if name == 'volume_dialog_ringer_background' else 'Top'
            corner = 'top' if edge == 'Bottom' else 'bottom'
            # aapt2's XML dumper prints the signed 24-bit mantissa as unsigned.
            if ('E: clip' not in shape or 'E: inset' not in shape
                    or not re.search(r':inset' + edge + r'\([^)]*\)=(?:-2|16777214)(?:\.0+)?dp', shape)
                    or ':' + corner + 'LeftRadius(' not in shape
                    or ':' + corner + 'RightRadius(' not in shape):
                raise RuntimeError('Volume background must have an open join: ' + name)
    systemui_overlay = resources(apk('/system/product/overlay/SystemUI__' + product
        + '__auto_generated_rro_product.apk', 'systemui-overlay.apk'))
    require_value(systemui_overlay, 'bool/config_supportBlurredWallpaper', 'false')
    require_value(systemui_overlay, 'bool/config_einkKeyguard', 'true')
    for name in ['shade_panel_fallback', 'notification_scrim_fallback']:
        require_value(systemui_overlay, 'color/' + name, framework_color('white'))
    # Quiet E-Ink UI defaults: solid black dark icons, no idle/charging animations.
    for name in ['dark_mode_icon_color_single_tone', 'dark_mode_icon_color_dual_tone_fill',
                 'dark_mode_qs_icon_color_single_tone', 'dark_mode_qs_icon_color_dual_tone_fill']:
        require_value(systemui_overlay, 'color/' + name, '#ff000000')
    require_value(systemui_overlay, 'dimen/status_bar_icon_drawing_alpha', '1.000000%')
    require_value(systemui_overlay, 'bool/flag_charging_ripple', 'false')
    require_value(systemui_overlay, 'bool/config_enablePrivacyChipAnimation', 'false')
    require_value(systemui_overlay, 'color/keyguard_shadow_color', '#00000000')
    require_value(systemui_overlay, 'string/clock_component_name', '""')
    require_value(overlay, 'dimen/config_wallpaperMaxScale', '1')
    require_value(overlay, 'bool/config_showBuiltinWirelessChargingAnim', 'false')
    latin_overlay = resources(apk('/system/product/overlay/LatinIME__' + product
        + '__auto_generated_rro_product.apk', 'latin-overlay.apk'))
    for qualifier in ['', 'sw430dp']:
        require_value(latin_overlay, 'bool/config_default_key_preview_popup', 'false', qualifier)
    print('PASS: packaged quiet E-Ink UI overlays (status icons, clock icon, key preview, '
          'wallpaper zoom, charging/privacy animations, shadows)')
    launcher_overlay = resources(apk('/system/product/overlay/Launcher3QuickStep__' + product
        + '__auto_generated_rro_product.apk', 'launcher-overlay.apk'))
    require_value(launcher_overlay, 'bool/config_flatLauncherSurfaces', 'true')
    require_value(launcher_overlay, 'bool/config_swipeOnRelease', 'true')
    require_value(launcher_overlay, 'bool/config_staticSystemGestures', 'true')
    require_value(launcher_overlay, 'bool/config_staticAllApps', 'true')
    require_value(launcher_overlay, 'integer/config_pageSnapAnimationDuration', '1')
    require_value(launcher_overlay, 'string/clock_component_name', '""')
    # HiBreak overrides Launcher icon roles without changing shared Monet colors.
    # AAPT folds v31 into the default/night configurations on this Android 16 product.
    for qualifier, foreground, background in [('', '#ff000000', '#ffffffff'),
                                               ('night', '#ffffffff', '#ff000000')]:
        for name, value in [('themed_icon_color', foreground),
                            ('themed_icon_background_color', background),
                            ('themed_icon_adaptive_background_color', background),
                            ('themed_badge_icon_color', '#ff000000'),
                            ('themed_badge_icon_background_color', '#ffffffff')]:
            require_value(launcher_overlay, 'color/' + name, value, qualifier)
    launcher_apk = apk('/system/system_ext/priv-app/Launcher3QuickStep/Launcher3QuickStep.apk',
                       'launcher.apk')
    launcher_resources = resources(launcher_apk)
    for name, value in [('color/all_apps_static_surface', '#ffffffff'),
                        ('color/all_apps_static_outline', '#ff000000'),
                        ('dimen/all_apps_static_outline_width', '1.000000dp'),
                        ('dimen/static_all_apps_open_distance', '48.000000dp'),
                        ('dimen/static_all_apps_close_distance', '32.000000dp')]:
        require_value(launcher_resources, name, value)
    search_shape = run(tree / 'prebuilts/sdk/tools/linux/bin/aapt2', 'dump', 'xmltree',
                       launcher_apk, '--file',
                       'res/drawable/bg_all_apps_searchbox_static.xml').decode()
    for element in ['solid', 'stroke', 'corners']:
        if 'E: ' + element not in search_shape:
            raise RuntimeError('static drawer search shape missing ' + element)
    for name in ['color/all_apps_static_surface', 'color/all_apps_static_outline',
                 'dimen/all_apps_static_outline_width']:
        match = re.search(r'resource (0x[0-9a-f]+) ' + re.escape(name) + r'\b',
                          launcher_resources)
        if not match or '@' + match.group(1) not in search_shape:
            raise RuntimeError('static drawer search shape does not use ' + name)
    # Themed icons and drawer themed icons start on (apps/Launcher3/0010 + defaults/0014).
    require_value(launcher_resources, 'bool/config_defaultThemedIcons', 'false')
    require_value(launcher_resources, 'bool/config_defaultAllAppsThemedIcons', 'false')
    require_value(launcher_overlay, 'bool/config_defaultThemedIcons', 'true')
    require_value(launcher_overlay, 'bool/config_defaultAllAppsThemedIcons', 'true')
    drawer_default = re.search(r'resource (0x[0-9a-f]+) bool/config_defaultAllAppsThemedIcons\b',
                               launcher_resources).group(1)
    launcher_prefs = run(tree / 'prebuilts/sdk/tools/linux/bin/aapt2', 'dump', 'xmltree',
                         launcher_apk, '--file', 'res/xml/launcher_preferences.xml').decode()
    drawer_pref = [e for e in re.split(r'\n\s*E: ', launcher_prefs)
                   if ':key(' in e and '"pref_allapps_themed_icons"' in e]
    if len(drawer_pref) != 1 or not re.search(r':defaultValue\(0x[0-9a-f]+\)=@' + drawer_default
                                              + r'\b', drawer_pref[0]):
        raise RuntimeError('drawer themed icon switch does not show the resource default')
    print('PASS: themed icons and drawer themed icons default on (resource defaults, '
          'stored choices kept)')

    # Default wallpaper: every non-TV default_wallpaper the framework can resolve is
    # the pure white 824x1648 image, including the densities vendor/lineage overlays.
    def png_is_white(data, size):
        import struct, zlib
        if data[:8] != b'\x89PNG\r\n\x1a\n':
            return False
        pos, chunks = 8, {}
        while pos < len(data):
            length, kind = struct.unpack('>I4s', data[pos:pos + 8])
            chunks.setdefault(kind, []).append(data[pos + 8:pos + 8 + length])
            pos += 12 + length
        width, height, depth, color, _, _, interlace = struct.unpack('>IIBBBBB', chunks[b'IHDR'][0])
        if (width, height) != size or interlace:
            return False
        channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color]
        bpp = channels * depth
        stride, step = (width * bpp + 7) // 8, max(1, bpp // 8)
        raw = zlib.decompress(b''.join(chunks[b'IDAT']))
        rows, previous = [], bytearray(stride)
        for y in range(height):
            kind, line = raw[y * (stride + 1)], bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
            for i in range(stride):
                a = line[i - step] if i >= step else 0
                b, c = previous[i], previous[i - step] if i >= step else 0
                if kind == 1: line[i] = (line[i] + a) & 255
                elif kind == 2: line[i] = (line[i] + b) & 255
                elif kind == 3: line[i] = (line[i] + (a + b) // 2) & 255
                elif kind == 4:
                    p = a + b - c
                    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                    line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
            rows.append(bytes(line))
            previous = line
        if color == 3:
            palette = chunks[b'PLTE'][0]
            alpha = chunks.get(b'tRNS', [b''])[0]
            used = set()
            for row in rows:
                for x in range(width):
                    bit = x * depth
                    used.add((row[bit // 8] >> (8 - depth - bit % 8)) & ((1 << depth) - 1))
            return all(palette[3 * i:3 * i + 3] == b'\xff\xff\xff'
                       and (i >= len(alpha) or alpha[i] == 255) for i in used)
        full = (1 << depth) - 1
        if depth < 8:
            return all(row == bytes([255]) * len(row) or
                       all(((row[(x * depth) // 8] >> (8 - depth - (x * depth) % 8)) & full) == full
                           for x in range(width)) for row in rows)
        return all(row == b'\xff' * stride for row in rows)
    def wallpaper_configs(table):
        entry = re.search(r'resource 0x[0-9a-f]+ drawable/default_wallpaper\n(.*?)(?=\n\s*resource |\Z)',
                          table, re.S)
        return re.findall(r'^\s+\(([^)]*)\) \(file\) (\S+)', entry.group(1), re.M) if entry else []
    framework_wallpapers = {q for q, _ in wallpaper_configs(framework)}
    overlay_wallpapers = dict(wallpaper_configs(overlay))
    lineage_densities = {'hdpi', 'xhdpi', 'xxhdpi', 'xxxhdpi'}
    missing = (framework_wallpapers | lineage_densities) - set(overlay_wallpapers)
    if missing:
        raise RuntimeError('white wallpaper does not cover: ' + ', '.join(sorted(missing)))
    with zipfile.ZipFile(work / 'framework-overlay.apk') as archive:
        for qualifier, path in overlay_wallpapers.items():
            if qualifier == 'television':
                continue
            if not png_is_white(archive.read(path), (824, 1648)):
                raise RuntimeError('default wallpaper is not pure white 824x1648: ' + path)
    require_value(framework, 'string/default_wallpaper_component', '@null')
    require_value(framework, 'drawable/default_lock_wallpaper', '@null')
    for name in ['string/default_wallpaper_component', 'drawable/default_lock_wallpaper']:
        if re.search(r'resource 0x[0-9a-f]+ ' + name + r'\b', overlay):
            raise RuntimeError('product overlay overrides ' + name)
    prop_text = props_text + ''.join(
        read(path, optional=True).decode() for path in
        ['/system/product/etc/build.prop', '/system/system_ext/etc/build.prop'])
    for prop in ['ro.config.wallpaper', 'ro.config.lock_wallpaper', 'ro.config.wallpaper_component']:
        if re.search(r'^' + re.escape(prop) + '=', prop_text, re.M):
            raise RuntimeError('wallpaper property overrides the resource default: ' + prop)
    if read('/system/product/media/wallpaper', optional=True):
        raise RuntimeError('CMF default wallpaper directory present')
    overlay_dir = work / 'overlays'
    for path in ['/system/overlay', '/system/product/overlay', '/system/system_ext/overlay']:
        target = overlay_dir / path.strip('/').replace('/', '_')
        target.mkdir(parents=True)
        subprocess.run(['debugfs', '-R', 'rdump ' + path + ' ' + str(target), str(image)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    own_rro = 'framework-res__' + product + '__auto_generated_rro_product.apk'
    for other in sorted(overlay_dir.rglob('*.apk')):
        if other.name == own_rro:
            continue
        table = resources(other)
        if re.search(r'resource 0x[0-9a-f]+ (?:drawable/default_wallpaper|'
                     r'string/default_wallpaper_component|drawable/default_lock_wallpaper)\b', table):
            raise RuntimeError('another overlay overrides the default wallpaper: ' + other.name)
    require_value(overlay, 'string/config_wallpaperCropperPackage', '"com.android.wallpaper"')
    picker = run(tree / 'prebuilts/sdk/tools/linux/bin/aapt2', 'dump', 'xmltree',
                 apk('/system/system_ext/priv-app/ThemePicker/ThemePicker.apk', 'themepicker.apk'),
                 '--file', 'AndroidManifest.xml').decode()
    if 'package="com.android.wallpaper"' not in picker \
            or 'android.service.wallpaper.CROP_AND_SET_WALLPAPER' not in picker:
        raise RuntimeError('wallpaper cropper package does not handle CROP_AND_SET_WALLPAPER')
    print('PASS: pure white 824x1648 default wallpaper for home and lock (all densities, '
          'no other overlay/property/CMF override); cropper is com.android.wallpaper')

    lineage_settings_overlay = resources(apk('/system/product/overlay/LineageSettingsProvider__'
        + product + '__auto_generated_rro_product.apk', 'lineage-settings-overlay.apk'))
    require_value(lineage_settings_overlay, 'bool/def_qs_show_brightness_slider', 'false')
    print('PASS: Quick Settings brightness slider defaults to Never show')

    require_value(launcher_overlay, 'dimen/deep_shortcuts_elevation', '0.000000dp')
    require_value(launcher_overlay, 'dimen/folder_outline_width', '1.000000dp')
    for name in ['workspaceShadowColor', 'workspaceAmbientShadowColor', 'workspaceKeyShadowColor']:
        require_value(launcher_overlay, 'color/' + name, framework_color('transparent'))
    # AAPT folds v31 into default below this Android 16 product's minimum SDK.
    require_value(launcher_overlay, 'color/popup_color_primary_light',
                  framework_color('system_surface_light'))
    # Pressed popup items (static ripple fill) are a visible light grey.
    require_value(launcher_overlay, 'color/popup_color_tertiary_light', '#ffbdbdbd')
    require_value(launcher_overlay, 'dimen/widget_picker_outline_width', '1.000000dp')
    for name in [f'surface_effect_{n}_color' for n in range(4)] + [
            'shade_panel_fg_color', 'shade_panel_bg_color']:
        selector = run(tree / 'prebuilts/sdk/tools/linux/bin/aapt2', 'dump', 'xmltree',
            work / 'framework-overlay.apk', '--file', 'res/color/' + name + '.xml').decode()
        if (not re.search(r':color\([^)]*\)=#ffffffff', selector)
                or re.search(r':(?:alpha|lStar)\(', selector)):
            raise RuntimeError('surface selector is not opaque white: ' + name)
    provider = resources(apk('/system/priv-app/SettingsProvider/SettingsProvider.apk', 'settings-provider.apk'))
    require_value(provider, 'fraction/def_hibreak_animator_duration_scale', '0.000000%')
    # Window/transition defaults are product RRO values, not the provider APK's
    # upstream 100% fallback. Verify all three developer animation defaults.
    provider_overlay_apk = apk(
        '/system/product/overlay/SettingsProvider__' + product
        + '__auto_generated_rro_product.apk', 'settings-provider-overlay.apk')
    provider_overlay = resources(provider_overlay_apk)
    for name in ['def_window_animation_scale', 'def_window_transition_scale']:
        require_value(provider_overlay, 'fraction/' + name, '0.000000%')
    provider_manifest = run(tree / 'prebuilts/sdk/tools/linux/bin/aapt2', 'dump', 'xmltree',
                            provider_overlay_apk, '--file', 'AndroidManifest.xml').decode()
    if 'com.android.providers.settings' not in provider_manifest or not re.search(
            r':isStatic\([^)]*\)=true', provider_manifest):
        raise RuntimeError('animation-default product overlay is not enabled statically')
    match = re.search(r'string/def_hibreak_theme_customization_overlay_packages\n\s+\(\) "(.*)"', provider)
    if not match:
        raise RuntimeError('default E-Ink palette missing')
    # aapt2 emits the JSON string with quotes escaped for its text output.
    palette = json.loads(match.group(1).replace('\\"', '"'))
    for key, value in {'color_source': 'preset', 'theme_style': 'MONOCHROMATIC',
                       'system_palette': '333333', 'color_index': '13'}.items():
        if palette.get('android.theme.customization.' + key) != value:
            raise RuntimeError('incorrect default palette: ' + key)
    if re.search(r'bool/config_disableLockscreenByDefault\n\s+\(\) true', overlay):
        raise RuntimeError('debug lockscreen bypass retained')
    sf = read('/system/bin/surfaceflinger')
    for marker in [b'Ignoring invalid boot hotplug before Scheduler initialization',
                   b'EinkProfile: mode=', b'ro.bigme.force_client_composition']:
        if marker not in sf:
            raise RuntimeError('essential display adaptation missing: ' + repr(marker))
    rw = read('/system/bin/rw-system.sh')
    if b'setprop ro.keymaster.xxx.security_patch "$spl"' not in rw:
        raise RuntimeError('legacy Keymaster boot SPL producer missing')
    controls_apk = apk('/system/priv-app/A9AccessibilityService/A9AccessibilityService.apk', 'controls.apk')
    print(run('python3', Path(__file__).with_name('verify-eink-hardware-keys.py'), controls_apk,
              '--aapt2', tree / 'prebuilts/sdk/tools/linux/bin/aapt2').decode(), end='')
    controls_dex = dex(controls_apk)
    if b'dither:package:' not in controls_dex:
        raise RuntimeError('per-app dithering controls missing')
    badging = run(tree / 'prebuilts/sdk/tools/linux/bin/aapt2', 'dump', 'badging', controls_apk).decode()
    if not re.search(r"^package: name='net\.dianqk\.hibreak\.eink' ", badging, re.MULTILINE):
        raise RuntimeError('E-Ink settings application ID mismatch')
    if b'package="net.dianqk.hibreak.eink"' not in read('/system/etc/permissions/privapp-permissions-hibreak-eink.xml'):
        raise RuntimeError('E-Ink settings privileged permission package mismatch')
    for requirement in [r"^(?:minSdkVersion|sdkVersion):'35'$", r"^targetSdkVersion:'35'$"]:
        if not re.search(requirement, badging, re.MULTILINE):
            raise RuntimeError('E-Ink settings SDK mismatch: ' + requirement)
    controls = dex(controls_apk)
    for token in [b'Lnet/dianqk/hibreak/eink/A9AccessibilityService;',
                  b'frontlight_auto', b'frontlight_night_start', b'frontlight_day_start',
                  b'frontlight_override_until', b'waveform:package:', b'clean_frequency:package:']:
        if token not in controls:
            raise RuntimeError('E-Ink control feature missing: ' + repr(token))
    policy = read('/system/etc/selinux/plat_sepolicy.cil')
    if b'(allow system_app hibreak_einkd (unix_stream_socket (connectto)))' not in policy:
        raise RuntimeError('E-Ink service policy missing')
    if b'bigme_bootdiag' in policy:
        raise RuntimeError('private diagnostic SELinux policy retained')
    # XRZ anti-ghosting window: dedicated label, system_server sets, composer reads.
    if not re.search(rb'^vendor\.xrz\.check_commit\s+u:object_r:hibreak_xrz_check_commit_prop:s0'
                     rb'\s+exact\s+int$', debug_contexts, re.M):
        raise RuntimeError('vendor.xrz.check_commit lacks its dedicated property label')
    for rule in [b'(allow system_server hibreak_xrz_check_commit_prop (property_service (set)))',
                 b'(allow hal_graphics_composer_server hibreak_xrz_check_commit_prop (file (read getattr map open)))']:
        if rule not in policy:
            raise RuntimeError('XRZ check_commit policy missing: ' + rule.decode())
    services_code = dex(services_jar)
    for marker in [b'Lcom/android/server/power/HiBreakXrzCheckCommit;', b'vendor.xrz.check_commit']:
        if marker not in services_code:
            raise RuntimeError('XRZ check_commit pulse missing: ' + repr(marker))
    print('PASS: XRZ check_commit pulse, dedicated label and composer read access')
    # One-shot GC16 clear through SurfaceFlinger 1113; no daemon force-and-sleep path.
    for marker in [b'EinkClear: armed mode', b'vendor.xrz.force_global_refresh_mode']:
        if marker not in sf:
            raise RuntimeError('SurfaceFlinger GC16 clear missing: ' + repr(marker))
    if b'force_clear' not in controls:
        raise RuntimeError('E-Ink clear actions do not use the SurfaceFlinger clear')
    einkd = read('/system/bin/a9_eink_server')
    print('PASS: one-shot GC16 clear (SurfaceFlinger 1113) used by the E-Ink clear actions')
    # The daemon serves only the app's commands (no raw frontlight or waveform commands
    # that bypass the 220 cap or the SurfaceFlinger profile); no control broadcasts.
    for retired in [b'br_co', b'br_wm', b'Rejected invalid display profile',
                    b'Rejected unsupported XRZ refresh mode']:
        if retired in einkd:
            raise RuntimeError('retired E-Ink daemon command retained: ' + repr(retired))
    for retired in [b'allow_custom_broadcast', b'EINK_REFRESH_SPEED', b'EINK_FORCE_CLEAR']:
        if retired in controls:
            raise RuntimeError('retired E-Ink control broadcast retained: ' + repr(retired))
    print('PASS: E-Ink daemon accepts only the app commands; no control broadcasts')
    # Hyper dithers only for high-rate content, like the stock framework.
    for marker in [b'hyper dither %s (cur_fps=%g fps_high=%g)', b'vendor.xrz.cur_fps',
                   b'persist.vendor.xrz.fps_high']:
        if marker not in sf:
            raise RuntimeError('adaptive Hyper dither missing: ' + repr(marker))
    if b'persist.vendor.xrz.fps' not in controls:
        raise RuntimeError('Hyper minimum refresh rate does not follow persist.vendor.xrz.fps')
    print('PASS: adaptive Hyper dither and Hyper minimum refresh rate')
    # E14: no ColorFade on sleep/wake; property kill switch in DisplayPowerController.
    if not re.search(r'bool/config_displayColorFadeDisabled\n\s+\(\) true', overlay):
        raise RuntimeError('ColorFade-disabled overlay missing')
    if b'persist.debug.hibreak.no_color_fade' not in services_code:
        raise RuntimeError('ColorFade kill switch missing')
    print('PASS: ColorFade disabled with kill switch')
    # E10: WebView flags written by a oneshot shell-user service with its own domain.
    webview_script = read('/system/bin/hibreak-webview-flags.sh')
    if b'--disable-smooth-scrolling --disable-features=ElasticOverscroll' not in webview_script \
            or b'persist.debug.hibreak.webview_flags' not in webview_script:
        raise RuntimeError('E-Ink WebView flags script missing')
    if b'service hibreak_webview_flags /system/bin/hibreak-webview-flags.sh' not in \
            read('/system/etc/init/hibreak-webview-flags.rc'):
        raise RuntimeError('E-Ink WebView flags service missing')
    if b'hibreak_webview_flags_exec' not in read('/system/system_ext/etc/selinux/system_ext_file_contexts') \
            or b'(allow hibreak_webview_flags shell_data_file (file' not in \
            read('/system/system_ext/etc/selinux/system_ext_sepolicy.cil'):
        raise RuntimeError('E-Ink WebView flags SELinux domain missing')
    print('PASS: E-Ink WebView flags service, domain and kill switch')
    # E7: composition-only damage for unchanged layers, with kill switch.
    for marker in [b'EinkDamage: composition-only damage', b'persist.debug.hibreak.composition_damage']:
        if marker not in sf:
            raise RuntimeError('E-Ink composition-only damage missing: ' + repr(marker))
    print('PASS: E-Ink composition-only damage with kill switch')
    # E9: touch-driven scroll detection through a spy gesture monitor, with kill switch.
    for marker in [b'Lnet/dianqk/hibreak/eink/TouchScrollMonitor;', b'HiBreakEinkScroll',
                   b'persist.debug.hibreak.touch_scroll']:
        if marker not in controls:
            raise RuntimeError('E-Ink touch scroll detection missing: ' + repr(marker))
    if b'pilferPointers' in controls:
        raise RuntimeError('E-Ink touch scroll monitor must not pilfer pointers')
    print('PASS: E-Ink touch scroll detection with kill switch')
    # E8: XRZ IME flag on the IME layer via the per-layer mode command, with kill switch.
    for marker in [b'EinkLayerMode: [%s] mode=0x%x', b'persist.debug.hibreak.ime_layer_flag']:
        if marker not in sf:
            raise RuntimeError('XRZ IME layer flag missing: ' + repr(marker))
    print('PASS: XRZ IME layer flag with kill switch')
    # P1-6: E-Ink daemon as system with frontlight nodes chowned on boot; root kill switch.
    einkd_rc = read('/system/etc/init/a9_eink_daemon.rc')
    if not re.search(rb'service a9_eink_server /system/bin/a9_eink_server\n(?:\s+#.*\n|\s+class main\n)*\s+user system\n', einkd_rc) \
            or b'chown system system /sys/devices/platform/11d01000.i2c7/i2c-7/7-0036/lm3630a_cold_light' not in einkd_rc \
            or b'property:persist.debug.hibreak.einkd_root=1' not in einkd_rc:
        raise RuntimeError('E-Ink daemon is not configured as the system user')
    if b'(allow init hibreak_frontlight_sysfs (file (getattr setattr)))' not in policy:
        raise RuntimeError('init cannot hand the frontlight nodes to the E-Ink daemon')
    print('PASS: E-Ink daemon as system user with root kill switch')
    if b'Landroidx/core/animation/PlatformDurationScaleBridge;' not in dex(sysui_apk):
        raise RuntimeError('SystemUI AndroidX animation scale bridge missing')
    print('PASS: SystemUI AndroidX animation scale bridge')
    # E-Ink picture sleep screen: keyguard DOZING section, white sleep scrims, E-Ink app setting.
    sysui_code = dex(sysui_apk)
    for marker in [b'Lcom/android/systemui/keyguard/ui/view/layout/sections/EinkSleepScreenSection;',
                   b'hibreak_sleep_screen_mode', b'EinkSleepScreen']:
        if marker not in sysui_code:
            raise RuntimeError('E-Ink sleep screen missing from SystemUI: ' + repr(marker))
    require_value(sysui_resources, 'string/hibreak_eink_sleep_locked_at', '"Locked')
    require_value(sysui_resources, 'string/hibreak_eink_sleep_locked_at', '"锁定于', 'zh-rCN')
    if 'res/drawable/hibreak_eink_sleep_logo.xml' not in sysui_files:
        raise RuntimeError('E-Ink sleep screen logo missing')
    if b'hibreak_sleep_screen_mode' not in controls:
        raise RuntimeError('E-Ink app sleep screen setting missing')
    print('PASS: E-Ink picture sleep screen (DOZING page, logo, localized lock time, app setting)')
    # Sleep screen reaches the panel: doze dream on sleep (framework, product overlay) and
    # SystemUI screen-off wait (presented + settle, bounded), one kill switch for both.
    require_value(framework, 'bool/config_einkDozeOnSleep', 'false')
    require_value(overlay, 'bool/config_einkDozeOnSleep', 'true')
    for marker in [b'doze on sleep: component=', b'persist.debug.hibreak.sleep_screen_wait']:
        if marker not in services_code:
            raise RuntimeError('E-Ink doze on sleep missing from services: ' + repr(marker))
    for marker in [b'Lcom/android/systemui/doze/EinkSleepScreenGate;',
                   b'screen-off control: waiting', b'page presented +',
                   b', releasing screen off +', b'persist.debug.hibreak.sleep_screen_wait']:
        if marker not in sysui_code:
            raise RuntimeError('E-Ink sleep screen-off wait missing from SystemUI: ' + repr(marker))
    require_value(sysui_resources, 'integer/config_einkSleepSettleMs', '400')
    require_value(sysui_resources, 'integer/config_einkSleepTimeoutMs', '1500')
    print('PASS: E-Ink sleep screen-off wait (doze on sleep, 400 ms settle, 1500 ms timeout, kill switch)')
    # Sleep screen modes: clock (refreshed while dozing), lock screen capture, custom image read
    # through the E-Ink app's provider; the app offers every mode in English and Chinese.
    for marker in [b'Lcom/android/systemui/doze/EinkSleepScreenRefresher;', b'EinkSleepScreen:clock',
                   b'refresh: ', b'lock screen captured',
                   b'content://net.dianqk.hibreak.eink.sleepscreen/image',
                   b'hibreak_sleep_screen_image_time']:
        if marker not in sysui_code:
            raise RuntimeError('E-Ink sleep screen mode missing from SystemUI: ' + repr(marker))
    require_value(sysui_resources, 'integer/config_einkSleepRefreshTimeoutMs', '3000')
    for marker in [b'Lnet/dianqk/hibreak/eink/SleepScreenImageProvider;', b'clock_15',
                   b'lockscreen', b'hibreak_sleep_screen_image']:
        if marker not in controls:
            raise RuntimeError('E-Ink app sleep screen mode missing: ' + repr(marker))
    controls_manifest = run(tree / 'prebuilts/sdk/tools/linux/bin/aapt2', 'dump', 'xmltree',
                            '--file', 'AndroidManifest.xml', controls_apk).decode()
    provider = re.search(r'E: provider .*?(?=\n\s+E: |\Z)', controls_manifest, re.S)
    if not provider or 'net.dianqk.hibreak.eink.sleepscreen' not in provider.group(0) \
            or not all(re.search(kind + r'Permission\(0x[0-9a-f]+\)="android\.permission\.'
                                 r'STATUS_BAR_SERVICE"', provider.group(0))
                       for kind in ('read', 'write')):
        raise RuntimeError('E-Ink sleep screen image provider must require STATUS_BAR_SERVICE')
    controls_resources = resources(controls_apk)
    for name in ['clock_1', 'clock_5', 'clock_15', 'lock_screen', 'custom', 'image_time']:
        entry = re.search(r'resource 0x[0-9a-f]+ string/eink_sleep_' + name
                          + r'\n(.*?)(?=\n\s*resource |\Z)', controls_resources, re.S)
        if not entry or not all(re.search(r'^[ \t]+\(' + q + r'\) "', entry.group(1), re.M)
                                for q in ('', 'zh-rCN')):
            raise RuntimeError('E-Ink app sleep screen string missing: eink_sleep_' + name)
    print('PASS: E-Ink sleep screen modes (clock refresh, lock screen, custom image provider, app strings)')
    # mtk-volte: patched MediaTek IMS service as a platform-signed privileged system app.
    mtk = json.loads((Path(__file__).with_name('mtk-ims') / 'source.json').read_text())
    ims_apk = apk(mtk['system_apk'], 'mtk-ims.apk')
    def code_and_resources(path):
        with zipfile.ZipFile(path) as archive:
            return {n: archive.read(n) for n in archive.namelist() if not n.startswith('META-INF/')}
    ims_entries = code_and_resources(ims_apk)
    if hashlib.sha256(ims_entries.get('classes.dex', b'')).hexdigest() != mtk['patched_classes_dex_sha256'] \
            or ims_entries != code_and_resources(tree / mtk['module_apk']):
        raise RuntimeError('packaged MediaTek IMS APK is not the patched build input')
    def xmltree(path):
        return run(tree / 'prebuilts/sdk/tools/linux/bin/aapt2', 'dump', 'xmltree',
                   '--file', 'AndroidManifest.xml', path).decode()
    ims_manifest = xmltree(ims_apk)
    for marker in ['package="' + mtk['apk']['package'] + '"', ':versionCode(0x0101021b)=' + str(mtk['apk']['version_code']),
                   ':sharedUserId(0x0101000b)="android.uid.phone"', ':directBootAware(0x01010505)=true']:
        if marker not in ims_manifest:
            raise RuntimeError('unexpected MediaTek IMS manifest: ' + marker)
    privileged = set()
    for block in re.split(r'\n\s+E: ', xmltree(work / 'framework-res.apk')):
        name = re.search(r':name\(0x01010003\)="([^"]+)"', block)
        level = re.search(r':protectionLevel\(0x01010009\)=(0x[0-9a-f]+)', block)
        if block.startswith('permission ') and name and level and int(level.group(1), 16) & 0x10:
            privileged.add(name.group(1))
    requested = set(re.findall(r'E: uses-permission .*?\n\s+A: \S+:name\(0x01010003\)="([^"]+)"', ims_manifest))
    allowlist = read('/system/etc/permissions/privapp-permissions-com.mediatek.ims.xml').decode()
    if 'package="com.mediatek.ims"' not in allowlist or \
            set(re.findall(r'<permission name="([^"]+)"/>', allowlist)) != requested & privileged:
        raise RuntimeError('MediaTek IMS privapp allowlist does not match its privileged permissions')
    for key in ['persist.dbg.volte_avail_ovr', 'persist.dbg.allow_ims_off']:
        if [line for line in props_text.splitlines() if line.startswith(key + '=')] != [key + '=1']:
            raise RuntimeError('VoLTE default missing: ' + key)
    for path in ['/system/build.prop', '/system/system_ext/etc/build.prop', '/system/product/etc/build.prop']:
        if b'wfc_avail_ovr' in read(path):
            raise RuntimeError('Wi-Fi Calling override must not be a build default: ' + path)
    print('PASS: patched MediaTek IMS (pinned dex, platform-signed priv-app, privapp allowlist '
          + str(len(requested & privileged)) + ' permissions); VoLTE defaults; no Wi-Fi Calling override')
    google_apps = {
        'product/priv-app/GmsCore/GmsCore.apk': ('arm64', 'com.google.android.gms'),
        'product/priv-app/Phonesky/Phonesky.apk': ('arm64', 'com.android.vending'),
        'system_ext/priv-app/GoogleServicesFramework/GoogleServicesFramework.apk':
            ('common', 'com.google.android.gsf'),
    }
    for path, (arch, package) in google_apps.items():
        payload = read('/system/' + path, optional=True)
        if args.variant == 'vanilla':
            if payload:
                raise RuntimeError('Google app leaked into vanilla image: ' + path)
            continue
        original = tree / 'vendor/gapps' / arch / 'proprietary' / path
        if not payload or payload != original.read_bytes():
            raise RuntimeError('missing or changed presigned Google app: ' + path)
        google = work / 'google.apk'
        google.write_bytes(payload)
        badge = run(tree / 'prebuilts/sdk/tools/linux/bin/aapt2', 'dump', 'badging', google).decode()
        if not re.search(r"^package: name='" + re.escape(package) + "' ", badge, re.MULTILINE):
            raise RuntimeError('Google application ID mismatch: ' + path)
        subprocess.run([str(out / 'host/linux-x86/bin/apksigner'), 'verify', str(google)],
                       check=True, env=env)
    print('PASS: variant=' + args.variant + '; EXT4; Google packages/signatures match flavor; no Setup Wizard')
    adb_mode = 'explicit debug ADB (all hosts)' if args.debug_adb else 'authenticated opt-in ADB; no debug payload'
    print('PASS: EXT4/AVB; ' + adb_mode + '; silent setup; local signatures; display/input/E-Ink defaults')
    print('Build number:', number)
