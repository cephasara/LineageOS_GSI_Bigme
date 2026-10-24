#!/usr/bin/env python3
"""Verify the packaged DocumentsUI paper/ink resources (not device rendering)."""
import argparse
from pathlib import Path
import re
import subprocess
import struct
import zipfile


def dex_declared_fields(data):
    """Read class_data definitions, not strings/references that R8 could leave behind."""
    if not data.startswith(b'dex\n'):
        raise RuntimeError('DocumentsUI invalid DEX header')

    def u32(offset):
        return struct.unpack_from('<I', data, offset)[0]

    def uleb(offset):
        value = shift = 0
        while True:
            byte = data[offset]
            offset += 1
            value |= (byte & 127) << shift
            if byte < 128:
                return value, offset
            shift += 7
            if shift > 28:
                raise RuntimeError('DocumentsUI invalid DEX ULEB')

    strings = []
    for i in range(u32(56)):
        _, offset = uleb(u32(u32(60) + 4 * i))
        strings.append(data[offset:data.index(b'\0', offset)].decode('utf-8', errors='replace'))
    types = [strings[u32(u32(68) + 4 * i)] for i in range(u32(64))]
    fields = [struct.unpack_from('<HHI', data, u32(84) + 8 * i) for i in range(u32(80))]
    classes = {}
    for i in range(u32(96)):
        entry = u32(100) + 32 * i
        owner = types[u32(entry)]
        classes[owner] = {}
        offset = u32(entry + 24)
        if not offset:
            continue
        counts = []
        for _ in range(4):
            size, offset = uleb(offset)
            counts.append(size)
        for size in counts[:2]:
            index = 0
            for _ in range(size):
                delta, offset = uleb(offset)
                _, offset = uleb(offset)  # access flags
                index += delta
                class_id, type_id, name_id = fields[index]
                if types[class_id] != owner:
                    raise RuntimeError('DocumentsUI DEX field owner mismatch')
                classes[owner][strings[name_id]] = types[type_id]
    return classes


def verify(apk, aapt2, framework):
    def dump(*args):
        return subprocess.check_output([str(aapt2), 'dump', *map(str, args)], text=True)
    app = dump('resources', apk)
    fw = dump('resources', framework)

    def resource(text, name):
        match = re.search(r'    resource (0x[0-9a-f]+) ' + re.escape(name)
                          + r'\b([^\n]*\n.*?)(?=    resource |\Z)', text, re.S)
        if not match:
            raise RuntimeError('DocumentsUI missing resource: ' + name)
        return match.group(1), match.group(2)

    white = '@' + resource(fw, 'color/white')[0]
    black = '@' + resource(fw, 'color/black')[0]
    theme = resource(app, 'style/DocumentsEinkTheme')[1]
    for attr, expected in [('colorBackground', white), ('textColorPrimary', black),
                           ('textColorSecondary', black), ('windowAnimationStyle', '@null'),
                           ('forceDarkAllowed', 'false')]:
        key = resource(fw, 'attr/' + attr)[0]
        if key + '=' + expected not in theme:
            raise RuntimeError('DocumentsUI platform theme mismatch: ' + attr)
    for attr, expected in [('colorSurface', white), ('colorSurfaceContainer', white),
                           ('colorSurfaceContainerHigh', white), ('colorOnSurface', black),
                           ('colorOnSurfaceVariant', black), ('colorOnPrimary', white)]:
        if not re.search(re.escape(attr) + r'\(0x[0-9a-f]+\)=' + re.escape(expected), theme):
            raise RuntimeError('DocumentsUI Material theme mismatch: ' + attr)
    durations = re.findall(r'motionDuration\w+\(0x[0-9a-f]+\)=(\d+)', theme)
    if len(durations) != 16 or set(durations) != {'0'}:
        raise RuntimeError('DocumentsUI Material motion durations are not all zero')
    for name in ['app_background_color_m3', 'color_surface_header_m3',
                 'item_drag_shadow_background_m3']:
        block = resource(app, 'color/' + name)[1]
        values = re.findall(r'^\s+\([^)]*\) (\S+)', block, re.M)
        if not values or set(values) != {white}:
            raise RuntimeError('DocumentsUI day/night surface mismatch: ' + name)
    button = resource(app, 'style/MaterialButtonM3')[1]
    if not re.search(r'strokeWidth\(0x[0-9a-f]+\)=1\.0+px', button):
        raise RuntimeError('DocumentsUI button border is not a physical pixel')
    if not re.search(r'backgroundTint\(0x[0-9a-f]+\)=' + re.escape(white), button):
        raise RuntimeError('DocumentsUI button background is not white')
    for name in ['eink_panel', 'eink_menu', 'list_item_background_m3',
                 'grid_thumbnail_background', 'grid_nameplate_background', 'root_item_background_m3']:
        xml = dump('xmltree', apk, '--file', 'res/drawable/' + name + '.xml')
        if 'E: stroke' not in xml or '1.000000px' not in xml or black not in xml:
            raise RuntimeError('DocumentsUI static black 1px outline missing: ' + name)
        if 'E: ripple' in xml or 'E: animated-' in xml:
            raise RuntimeError('DocumentsUI animated state drawable retained: ' + name)
        if name in ('eink_panel', 'eink_menu') and 'com.android.documentsui.ui.EinkShapeDrawable' not in xml:
            raise RuntimeError('DocumentsUI shared-border suppression missing: ' + name)
        if name == 'eink_menu' and xml.count('8.000000dp') != 2:
            raise RuntimeError('DocumentsUI popup native vertical padding changed')
    edge = dump('xmltree', apk, '--file', 'res/drawable/eink_drawer_edge.xml')
    if '1.000000px' not in edge or black not in edge or '0x00800005' not in edge:
        raise RuntimeError('DocumentsUI foreground drawer edge is not black 1px / END')
    with zipfile.ZipFile(apk) as archive:
        for library, expected in [('drawerlayout_drawerlayout', b'1.3.0-alpha01'),
                                  ('customview_customview', b'1.2.0-alpha03')]:
            if archive.read('META-INF/androidx.' + library + '.version').strip() != expected:
                raise RuntimeError('Re-review DocumentsUI native drawer completion for ' + library)
        classes = {}
        for name in archive.namelist():
            if name.endswith('.dex'):
                classes.update(dex_declared_fields(archive.read(name)))
        # Material 3 is on (static DocumentsUIOverlay), so the legacy drawer_layout is
        # always mapped to drawer_layout_m3; only the M3 layouts are patched.
        layouts = ['drawer_layout_m3', 'nav_rail_layout']
    for name in layouts:
        xml = dump('xmltree', apk, '--file', 'res/layout/' + name + '.xml')
        if 'E: com.android.documentsui.ui.DocumentsDrawerLayout' not in xml:
            raise RuntimeError('DocumentsUI static drawer not bound to layout: ' + name)
    for name in ['ui/EinkShapeDrawable', 'ui/DocumentsDrawerLayout', 'dirlist/EinkListDividers']:
        if 'Lcom/android/documentsui/' + name + ';' not in classes:
            raise RuntimeError('DocumentsUI presentation class removed/renamed by R8: ' + name)
    for owner, fields in {
        'Landroidx/drawerlayout/widget/DrawerLayout;': {
            'mLeftDragger': 'Landroidx/customview/widget/ViewDragHelper;',
            'mRightDragger': 'Landroidx/customview/widget/ViewDragHelper;'},
        'Landroidx/customview/widget/ViewDragHelper;': {'mScroller': 'Landroid/widget/OverScroller;'},
    }.items():
        for name, field_type in fields.items():
            if classes.get(owner, {}).get(name) != field_type:
                raise RuntimeError('DocumentsUI bundled drawer field contract missing: ' + owner + name)
    print('PASS: packaged DocumentsUI paper/ink, 1px drawer/list presentation, static drawer bindings and R8 field contracts')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('apk', type=Path)
    parser.add_argument('--aapt2', type=Path, required=True)
    parser.add_argument('--framework', type=Path, required=True)
    args = parser.parse_args()
    verify(args.apk, args.aapt2, args.framework)
