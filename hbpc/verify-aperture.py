#!/usr/bin/env python3
"""Verify shipped Aperture styling and bundled-library contracts, not camera operation."""
import argparse
import importlib.util
from pathlib import Path
import re
import subprocess
import zipfile

# Reuse the existing definition/type parser, rather than checking DEX string presence.
spec = importlib.util.spec_from_file_location('documents_dex', Path(__file__).with_name('verify-documentsui.py'))
dex_reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dex_reader)


def verify(apk, aapt2, framework):
    def dump(*args):
        return subprocess.check_output([str(aapt2), 'dump', *map(str, args)], text=True)

    app = dump('resources', apk)
    fw = dump('resources', framework)

    def resource(text, name):
        match = re.search(r'    resource (0x[0-9a-f]+) ' + re.escape(name)
                          + r'(?=\s)([^\n]*\n.*?)(?=    resource |\Z)', text, re.S)
        if not match:
            raise RuntimeError('Aperture missing resource: ' + name)
        return match.group(1), match.group(2)

    def require(condition, message):
        if not condition:
            raise RuntimeError('Aperture: ' + message)

    white = '@' + resource(fw, 'color/white')[0]
    black = '@' + resource(fw, 'color/black')[0]
    theme_id, theme = resource(app, 'style/Theme.Aperture')
    for attr, expected in [('colorBackground', white), ('windowBackground', white),
                           ('textColorPrimary', black), ('textColorSecondary', black),
                           ('windowLightStatusBar', 'true'), ('windowLightNavigationBar', 'true'),
                           ('forceDarkAllowed', 'false'), ('windowAnimationStyle', '@null')]:
        key = resource(fw, 'attr/' + attr)[0]
        require(key + '=' + expected in theme, 'platform light/static theme ' + attr)
    for attr, expected in [('colorSurface', white), ('colorSurfaceContainer', white),
                           ('colorSurfaceContainerHighest', white), ('colorOnSurface', black),
                           ('colorOnSurfaceVariant', black), ('colorPrimary', black),
                           ('colorOnPrimary', white)]:
        require(re.search(re.escape(attr) + r'\(0x[0-9a-f]+\)=' + re.escape(expected), theme),
                'Material paper/ink role ' + attr)
    durations = re.findall(r'motionDuration\w+\(0x[0-9a-f]+\)=(\d+)', theme)
    require(len(durations) == 16 and set(durations) == {'0'}, 'Material motion durations')
    for name in ['Theme.Aperture.Camera', 'Theme.SettingsLib']:
        require('parent=style/Theme.Aperture ('+theme_id+')' in resource(app, 'style/'+name)[1],
                'light parent for '+name)
    light_id = resource(app, 'style/Theme.Material3.Light.NoActionBar')[0]
    require('parent=style/Theme.Material3.Light.NoActionBar ('+light_id+')' in theme, 'explicit light base parent')
    for name in ['Widget.Aperture.Eink.Button', 'Widget.Aperture.Eink.TextButton']:
        block = resource(app, 'style/'+name)[1]
        require(re.search(r'strokeWidth\(0x[0-9a-f]+\)=1\.0+px', block), '1px stroke '+name)
        require(re.search(r'strokeColor\(0x[0-9a-f]+\)='+re.escape(black), block), 'black stroke '+name)
    require('org.lineageos.aperture.ui.views.EinkBottomSheetBehavior' in
            resource(app, 'string/bottom_sheet_behavior')[1], 'static bottom-sheet binding')
    require("package: name='org.lineageos.aperture'" in dump('badging', apk), 'package identity')

    with zipfile.ZipFile(apk) as archive:
        names = set(archive.namelist())
        classes = {}
        for name in names:
            if name.endswith('.dex'):
                classes.update(dex_reader.dex_declared_fields(archive.read(name)))
        versions = {
            'META-INF/com.google.android.material_material.version': b'1.14.0-alpha02',
            'META-INF/androidx.customview_customview.version': b'1.2.0-alpha03',
        }
        for name, version in versions.items():
            require(archive.read(name).strip() == version, 're-review library version '+name)

    def xml(kind, name):
        # R8 may rewrite resource paths; resolve the path from the resource table.
        block = resource(app, kind+'/'+name)[1]
        path = re.search(r'\(file\) (\S+)', block)
        require(path is not None, 'compiled XML path '+name)
        return dump('xmltree', apk, '--file', path.group(1))

    for name in ['eink_control', 'eink_surface', 'eink_border_8dp', 'eink_border_12dp']:
        text = xml('drawable', name)
        require('E: stroke' in text and '1.000000px' in text and black in text, 'static outline '+name)
        require('E: ripple' not in text and 'E: animated-' not in text, 'no animated outline '+name)
    require('dashGap' in xml('drawable', 'eink_control'), 'disabled dashed border')
    for name in ['eink_shutter_photo', 'eink_shutter_video', 'eink_shutter_stop', 'eink_pause', 'eink_play', 'ic_flip_camera']:
        text = xml('drawable', name)
        require('E: vector' in text and 'animated-vector' not in text, 'static camera icon '+name)
    for name in ['settingslib_switch', 'settingslib_switch_compat']:
        require('E: org.lineageos.aperture.ui.views.EinkSwitch' in xml('layout', name), 'static switch '+name)
    settings = xml('layout', 'activity_settings')
    for name in ['EinkAppBarLayout', 'EinkCollapsingToolbarLayout']:
        require('E: com.google.android.material.appbar.'+name in settings, 'static settings binding '+name)
    require(re.search(r'animation_enabled.*=false', xml('layout', 'capture_preview_layout')), 'static Media3 controller')

    for owner, fields in {
        'Lcom/google/android/material/bottomsheet/BottomSheetBehavior;': {
            'viewDragHelper': 'Landroidx/customview/widget/ViewDragHelper;'},
        'Landroidx/customview/widget/ViewDragHelper;': {'mScroller': 'Landroid/widget/OverScroller;'},
        'Lcom/google/android/material/appbar/AppBarLayout$BaseBehavior;': {
            'offsetAnimator': 'Landroid/animation/ValueAnimator;'},
    }.items():
        for name, field_type in fields.items():
            require(classes.get(owner, {}).get(name) == field_type, 'R8 field definition/type '+owner+name)
    for name in ['org/lineageos/aperture/ui/views/EinkBottomSheetBehavior',
                 'org/lineageos/aperture/ui/views/EinkSwitch',
                 'com/google/android/material/appbar/EinkAppBarLayout',
                 'com/google/android/material/appbar/EinkCollapsingToolbarLayout']:
        require('L'+name+';' in classes, 'R8 presentation class '+name)
    print('PASS: packaged Aperture light paper/ink, outlines, static icons/controls and R8 library field contracts')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('apk', type=Path)
    parser.add_argument('--aapt2', type=Path, required=True)
    parser.add_argument('--framework', type=Path, required=True)
    args = parser.parse_args()
    verify(args.apk, args.aapt2, args.framework)
