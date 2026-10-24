#!/usr/bin/env python3
"""Check the packaged E-Ink custom-key filter and paging configuration (not input delivery)."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import zipfile

spec = importlib.util.spec_from_file_location('dex_fields', Path(__file__).with_name('verify-documentsui.py'))
dex_fields = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dex_fields)


def verify(apk, aapt2):
    def dump(*args):
        return subprocess.check_output([str(aapt2), 'dump', *map(str, args)], text=True)

    def require(condition, message):
        if not condition:
            raise RuntimeError('E-Ink hardware keys: ' + message)

    resources = dump('resources', apk)
    manifest = dump('xmltree', apk, '--file', 'AndroidManifest.xml')
    permissions = re.findall(r'E: uses-permission[^\n]*\n\s+A: [^\n]*:name\([^)]*\)="([^"]+)"', manifest)
    require('android.permission.INJECT_EVENTS' in permissions, 'missing signature injection permission')
    service_headers = re.findall(r'E: service[^\n]*\n((?:\s+A:[^\n]*\n)+)', manifest)
    service_header = next((s for s in service_headers if
                           '="net.dianqk.hibreak.eink.A9AccessibilityService"' in s), '')
    require(re.search(r':permission\([^)]*\)="android.permission.BIND_ACCESSIBILITY_SERVICE"', service_header),
            'unprotected accessibility service')
    require(re.search(r':sharedUserId\([^)]*\)="android.uid.system"', manifest), 'unexpected service identity')
    require("package: name='net.dianqk.hibreak.eink'" in dump('badging', apk), 'package identity')
    config = dump('xmltree', apk, '--file', 'res/xml/accessibility_service_config.xml')
    require(re.search(r'canRequestFilterKeyEvents[^\n]*=true', config), 'missing key-filter capability')
    flags = re.search(r'accessibilityFlags[^\n]*=0x([0-9a-f]+)', config)
    require(flags and int(flags.group(1), 16) & 0x20, 'key-filter flag not requested')

    def arrays(name):
        match = re.search(r'    resource 0x[0-9a-f]+ array/' + re.escape(name) +
                          r'\s*\n(.*?)(?=    resource |\Z)', resources, re.S)
        require(match, 'missing array '+name)
        result = {}
        for qualifier, count, contents in re.findall(
            r'\(([^)]*)\) \(array\) size=(\d+)\s*\[(.*?)\]', match.group(1), re.S
        ):
            values = json.loads('['+contents+']')
            require(len(values) == int(count), 'invalid array '+name)
            result[qualifier] = values
        return result

    old_values = ['clear', 'previous_track', 'next_track', 'toggle_music', 'back', 'home',
                  'recents', 'open_menu', 'toggle_night_light', 'toggle_backlight', 'dummy']
    values = arrays('button_action_values')
    require(values == {'': old_values+['page_up', 'page_down']}, 'stored values/order changed')
    labels = arrays('button_action_entries')
    require(labels.get('', [])[-2:] == ['Page Up', 'Page Down'], 'English page labels')
    require(labels.get('zh-rCN', [])[-2:] == ['上一页（Page Up）', '下一页（Page Down）'], 'Chinese page labels')
    require(all(len(v) == 13 for v in labels.values()), 'label/value count mismatch')
    require(arrays('button_action_values_screen_off') ==
            {'': ['clear', 'previous_track', 'next_track', 'toggle_music', 'dummy']},
            'screen-off values changed')
    require(all(len(v) == 5 for v in arrays('button_action_entries_screen_off').values()),
            'screen-off labels changed')

    classes = {}
    with zipfile.ZipFile(apk) as archive:
        for name in archive.namelist():
            if name.endswith('.dex'):
                classes.update(dex_fields.dex_declared_fields(archive.read(name)))
    prefix = 'Lnet/dianqk/hibreak/eink/'
    contracts = {
        prefix+'A9AccessibilityService;': {
            'hardwareKeyFilter': prefix+'HardwareKeyFilter;',
            'hardwareKeyHandler': 'Landroid/os/Handler;'},
        prefix+'HardwareKeyFilter;': {'presses': 'Ljava/util/Map;'},
        prefix+'HardwareGestureDetector;': {'pendingSingle': 'Z'},
        prefix+'button_mapper/PageButtonAction;': {'keyCode': 'I'},
    }
    for owner, fields in contracts.items():
        for name, field_type in fields.items():
            require(classes.get(owner, {}).get(name) == field_type,
                    'packaged filter/paging field definition missing: '+owner+name)
    print('PASS: packaged E-Ink device-key filter/deferred handler, page actions/labels, preserved values and permissions')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('apk', type=Path)
    parser.add_argument('--aapt2', type=Path, required=True)
    args = parser.parse_args()
    verify(args.apk, args.aapt2)
