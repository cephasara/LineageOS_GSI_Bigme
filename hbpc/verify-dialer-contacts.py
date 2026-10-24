#!/usr/bin/env python3
"""Verify actual Dialer-main/Contacts APK presentation and bundled bridge definitions."""
import argparse
import importlib.util
from pathlib import Path
import re
import subprocess
import zipfile

spec = importlib.util.spec_from_file_location('documents_dex', Path(__file__).with_name('verify-documentsui.py'))
dex = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dex)

def verify(dialer, contacts, aapt2, framework):
    def dump(*args):
        return subprocess.check_output([str(aapt2), 'dump', *map(str, args)], text=True)
    def require(ok, message):
        if not ok: raise RuntimeError('Dialer/Contacts: '+message)
    def resource(text, name):
        m = re.search(r'    resource (0x[0-9a-f]+) '+re.escape(name)+r'(?=\s)([^\n]*\n.*?)(?=    resource |\Z)', text, re.S)
        require(m is not None, 'missing '+name)
        return m.group(1), m.group(2)
    fw = dump('resources', framework)
    for apk, package, prefix, themes in [
        (dialer, 'com.android.dialer', 'main', ['MainEink.Root', 'MainEink.Launch', 'MainEink.Dialog']),
        (contacts, 'com.android.contacts', 'contacts', ['ContactsEink.Compat', 'ContactsEink.Platform', 'ContactsEink.Dialog', 'ContactsEink.PlatformDialog'])]:
        app = dump('resources', apk)
        require("package: name='"+package+"'" in dump('badging', apk), 'package '+package)
        def block(name): return resource(app, name)[1]
        def xml(kind, name):
            paths = re.findall(r'\(file\) (\S+)', block(kind+'/'+name))
            require(bool(paths), 'compiled XML '+name)
            return '\n'.join(dump('xmltree', apk, '--file', path) for path in paths)
        for name in themes:
            theme = block('style/'+name)
            for key, value in [('textColorPrimary','#ff000000'), ('textColorSecondary','#ff000000'),
                               ('colorBackground','#ffffffff'), ('statusBarColor','#ffffffff'),
                               ('navigationBarColor','#ffffffff'), ('windowLightStatusBar','true'),
                               ('windowLightNavigationBar','true'), ('forceDarkAllowed','false'),
                               ('windowAnimationStyle','@null')]:
                require(resource(fw, 'attr/'+key)[0]+'='+value in theme, name+' '+key)
            parent = re.search(r'parent=([^\n]+)', theme).group(1)
            native = {'ContactsEink.Platform': 'Theme.Material.Light',
                      'ContactsEink.PlatformDialog': 'Theme.Material.Light.Dialog'}
            require(parent == resource(fw, 'style/'+native[name])[0] if name in native else 'Light' in parent,
                    'light parent '+name)
        for suffix in ['line','disabled']:
            text = xml('drawable', prefix+'_eink_'+suffix)
            require('E: stroke' in text and '#ff000000' in text and '1.000000px' in text, '1px black '+suffix)
            require('E: ripple' not in text and 'E: animated-' not in text, 'static '+suffix)
            if suffix == 'disabled': require('dashGap' in text, 'disabled dash')
        active = xml('drawable', prefix+'_eink_active')
        line_id = resource(app, 'drawable/'+prefix+'_eink_line')[0]
        require(active.count('@'+line_id) == 2 and 'paddingMode' in active, 'double outline without inset padding')
        for shape in ['check','radio']:
            require('E: selector' in xml('drawable', prefix+'_eink_'+shape), 'static choice states')
            for state in ['true','false']:
                text = xml('drawable', prefix+'_eink_'+shape+'_'+state)
                require(text.count('32.000000dp') == 2 and 'E: vector' in text, 'native choice intrinsic size')
        popup = xml('drawable', prefix+'_eink_popup')
        require('E: nine-patch' in popup and '@'+resource(app, 'drawable/abc_popup_background_mtrl_mult')[0] in popup,
                'native popup nine-patch metrics')
        require('#ffffffff' in popup and '1.000000px' in popup, 'popup white and outlined')
        progress = xml('drawable', prefix+'_eink_progress')
        owner = 'com.android.dialer.main.impl' if prefix == 'main' else 'com.android.contacts.widget'
        require(owner+'.EinkProgressDrawable' in progress, 'static progress binding')
        with zipfile.ZipFile(apk) as archive:
            definitions = {}
            for name in archive.namelist():
                if name.endswith('.dex'): definitions.update(dex.dex_declared_fields(archive.read(name)))
            require('L'+owner.replace('.', '/')+'/EinkProgressDrawable;' in definitions, 'defined reflective drawable')
            require(archive.read('META-INF/androidx.appcompat_appcompat.version').strip() == b'1.8.0-alpha01', 're-review AppCompat native metrics')
            if prefix == 'contacts':
                for name, version in [('androidx.swiperefreshlayout_swiperefreshlayout','1.2.0-alpha01'),
                                      ('androidx.drawerlayout_drawerlayout','1.3.0-alpha01')]:
                    require(archive.read('META-INF/'+name+'.version').strip().decode() == version, 're-review bridge '+name)
                fields = definitions.get('Landroidx/swiperefreshlayout/widget/SwipeRefreshLayout;', {})
                require(fields.get('mCircleView') == 'Landroidx/swiperefreshlayout/widget/CircleImageView;', 'declared circle field ABI')
                require(fields.get('mProgress') == 'Landroidx/swiperefreshlayout/widget/CircularProgressDrawable;', 'declared progress field ABI')
                for cls, layout in [('androidx.swiperefreshlayout.widget.EinkSwipeRefreshLayout','contact_list_content'),
                                    ('com.android.contacts.widget.EinkDrawerLayout','contacts_drawer_activity')]:
                    require('L'+cls.replace('.', '/')+';' in definitions, 'defined '+cls)
                    require('E: '+cls in xml('layout', layout), 'bound '+cls)
        if prefix == 'main':
            require(re.search(r'mainEinkUi\(0x[0-9a-f]+\)=true', block('style/MainEink.Root')), 'main-local opt-in')
            for name, parent in [('MainActivityThemeBase','MainEink.Root'), ('MainActivityTheme','MainActivityThemeBase'),
                                 ('MainActivityThemeBase.Dark','MainActivityThemeBase'), ('LaunchTheme','MainEink.Launch')]:
                parents = re.findall(r'parent=([^ ]+)', block('style/'+name))
                require(parents and set(parents) == {'style/'+parent}, 'all configurations '+name)
            require('@'+resource(app, 'drawable/abc_dialog_material_background')[0] in xml('drawable','main_eink_dialog'), 'native dialog insets')
            require(re.search(r'background\(0x[0-9a-f]+\)=@'+resource(fw, 'color/white')[0], block('style/MainActionModeStyle')), 'readable selection bar')
        else:
            for name, parent in [('PeopleTheme','ContactsEink.Platform'), ('PeopleThemeAppCompat','ContactsEink.Compat')]:
                parents = re.findall(r'parent=([^ ]+)', block('style/'+name))
                require(parents and set(parents) == {'style/'+parent}, 'all API configurations '+name)
            for name in ['primary_text_color','secondary_text_color','letter_tile_font_color']:
                require(set(re.findall(r'#[0-9a-f]{8}', block('color/'+name))) == {'#ff000000'}, 'all night text '+name)
            for name in ['actionbar_background_color','letter_tile_default_color','background_primary']:
                require(set(re.findall(r'#[0-9a-f]{8}', block('color/'+name))) == {'#ffffffff'}, 'all night paper '+name)
        print('PASS: packaged '+package+' light/static themes, outlines, native background/choice metrics and drawable/bridge definitions')

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('dialer', type=Path)
    p.add_argument('contacts', type=Path)
    p.add_argument('--aapt2', type=Path, required=True)
    p.add_argument('--framework', type=Path, required=True)
    a = p.parse_args()
    verify(a.dialer, a.contacts, a.aapt2, a.framework)
