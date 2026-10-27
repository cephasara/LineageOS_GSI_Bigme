#!/usr/bin/env python3
"""Apply HiBreak Pro Color patches and incrementally build LineageOS 23.2 system.img."""
import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import urllib.request
import zipfile

REPO = Path(__file__).resolve().parent  # hbpc/: our patches, scripts and docs
ROOT = REPO.parent  # repository root: upstream MisterZtr patch groups under patches/
OVERRIDES = REPO / 'patches/upstream-overrides'  # rebased copies, same relative paths as upstream
PRODUCTS = {
    'vanilla': 'lineage_arm64_bvN4-bp4a-userdebug',
    'gapps': 'lineage_arm64_bgN4-bp4a-userdebug',
}
KEY_SHA = '69804441c70e866d81e0a80dfb762a993076c1325e41aee1d604925c20f977a1'
KEY_NAMES = ('releasekey', 'platform', 'shared', 'media', 'networkstack', 'bluetooth', 'nfc', 'sdk_sandbox')
SERIES = json.loads((REPO / 'patches/hibreak/series.json').read_text())
DEBUG_ADB_SERIES = json.loads((REPO / 'patches/debug-adb/series.json').read_text())
MTK_IMS = json.loads((REPO / 'mtk-ims/source.json').read_text())


def run(*cmd, cwd=None, capture=False, **kw):
    result = subprocess.run([str(c) for c in cmd], cwd=cwd, check=True,
                            stdout=subprocess.PIPE if capture else None, **kw)
    return result.stdout if capture else None


def git(tree, *args):
    return run('git', '-C', tree, '-c', 'commit.gpgsign=false',
               '-c', 'user.name=HiBreak Pro Color', '-c', 'user.email=hibreak@localhost',
               *args, capture=True).decode().strip()


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def build_treble_app(tree, args):
    """Build the patched upstream app; Android applies our platform signature later."""
    project = tree / 'treble_app'
    revision = git(project, 'rev-parse', 'HEAD')
    if git(project, 'status', '--porcelain', '--untracked-files=no'):
        raise RuntimeError('dirty TrebleApp source')
    target = project / 'TrebleApp.apk'
    marker = tree / '.repo/hibreak-treble-app.json'
    if marker.exists() and target.exists():
        state = json.loads(marker.read_text())
        if state == {'source_commit': revision, 'apk_sha256': sha(target)}:
            return
    env = dict(os.environ)
    if args.treble_java_home:
        env['JAVA_HOME'] = str(args.treble_java_home.resolve())
        env['PATH'] = env['JAVA_HOME'] + '/bin:' + env['PATH']
    sdk = (args.android_sdk_root or tree / '.repo/android-sdk').resolve()
    sdk.mkdir(parents=True, exist_ok=True)
    shutil.copytree(project / 'sdk/licenses', sdk / 'licenses', dirs_exist_ok=True)
    env['ANDROID_HOME'] = str(sdk)
    env['GRADLE_USER_HOME'] = str((args.gradle_user_home or tree / '.repo/gradle-cache').resolve())
    run('bash', 'gradlew', '--no-daemon', 'assembleRelease', cwd=project, env=env)
    source = project / 'app/build/outputs/apk/release/app-release-unsigned.apk'
    shutil.copyfile(source, target)
    marker.write_text(json.dumps({'source_commit': revision, 'apk_sha256': sha(target)},
                                 indent=2) + '\n')


def fetch(url, digest, cache):
    """Download once into the cache; any file used must match its pinned SHA-256."""
    target = cache / f'{digest}-{url.rsplit("/", 1)[-1]}'
    if target.is_file():
        if sha(target) == digest:
            return target
        target.unlink()
    cache.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + '.part')
    print('download:', url, flush=True)
    try:
        with urllib.request.urlopen(url, timeout=120) as response, partial.open('wb') as stream:
            shutil.copyfileobj(response, stream)
    except (OSError, http.client.HTTPException) as error:
        # URLError/HTTPError/timeouts are OSError; IncompleteRead and other protocol
        # errors are HTTPException.
        partial.unlink(missing_ok=True)
        raise RuntimeError(f'cannot download {url} and no cached copy in {cache}: {error!r}')
    if sha(partial) != digest:
        actual = sha(partial)
        partial.unlink()
        raise RuntimeError(f'SHA-256 mismatch for {url}: expected {digest}, got {actual}')
    partial.replace(target)
    return target


def build_mtk_ims(tree, cache):
    """Patch TrebleDroid's MediaTek IMS APK; Android applies our platform signature later."""
    patch = REPO / MTK_IMS['patch']
    target = tree / MTK_IMS['module_apk']
    marker = tree / '.repo/hibreak-mtk-ims.json'
    state = {'apk_sha256': MTK_IMS['apk']['sha256'], 'apktool_sha256': MTK_IMS['apktool']['sha256'],
             'patch_sha256': sha(patch), 'classes_dex_sha256': MTK_IMS['patched_classes_dex_sha256']}
    if marker.exists() and target.exists():
        if json.loads(marker.read_text()) == {**state, 'output_sha256': sha(target)}:
            return
    source = fetch(MTK_IMS['apk']['url'], MTK_IMS['apk']['sha256'], cache)
    apktool = fetch(MTK_IMS['apktool']['url'], MTK_IMS['apktool']['sha256'], cache)
    java = tree / 'prebuilts/jdk/jdk21/linux-x86/bin/java'
    with tempfile.TemporaryDirectory(prefix='hibreak-mtk-ims-', dir=tree / '.repo') as temp:
        work = Path(temp)
        decoded = work / 'decoded'
        tool = (java, f'-Djava.io.tmpdir={work}', '-jar', apktool)
        # Code only (-r): the manifest and resources stay the original binary files.
        run(*tool, 'd', '-f', '-r', '-p', work / 'framework', '-o', decoded, source)
        # A repository of its own, so git apply cannot resolve paths against an outer checkout.
        run('git', 'init', '-q', decoded)
        run('git', '-C', decoded, 'apply', patch)
        shutil.rmtree(decoded / '.git')
        run(*tool, 'b', '-f', '-p', work / 'framework', '-o', work / 'apktool.apk', decoded)
        dex = (decoded / 'build/apk/classes.dex').read_bytes()
        if hashlib.sha256(dex).hexdigest() != MTK_IMS['patched_classes_dex_sha256']:
            raise RuntimeError('patched MediaTek IMS classes.dex does not match its pinned SHA-256')
        # Same entries, order and compression as the original; only classes.dex changes.
        # The old v1 signature files go: the build signs the APK with the platform key.
        unsigned = work / 'unsigned.apk'
        with zipfile.ZipFile(source) as original, zipfile.ZipFile(unsigned, 'w') as result:
            for info in original.infolist():
                name = info.filename
                if name.startswith('META-INF/') and (name == 'META-INF/MANIFEST.MF' or
                        name.endswith(('.SF', '.RSA', '.DSA', '.EC'))):
                    continue
                entry = zipfile.ZipInfo(name, date_time=info.date_time)
                entry.compress_type = info.compress_type
                entry.external_attr = info.external_attr
                entry.create_system = info.create_system
                result.writestr(entry, dex if name == 'classes.dex' else original.read(name))
        unsigned.replace(target)  # same file system (.repo is in the tree): atomic
    marker.write_text(json.dumps({**state, 'output_sha256': sha(target)}, indent=2) + '\n')


def upstream_patches():
    result = []
    for group in ('trebledroid', 'trebledroid-staging', 'personal'):
        for directory in sorted((ROOT / 'patches' / group).iterdir()):
            if not directory.is_dir():
                continue
            project = directory.name.removeprefix('platform_').replace('_', '/')
            project = {'build': 'build/make', 'vendor/hardware/overlay': 'vendor/hardware_overlay',
                       'treble/app': 'treble_app', 'testing': 'platform_testing', 'vendor/partner/gms': 'vendor/partner_gms'}.get(project, project)
            result += [(project, upstream_effective(p)) for p in sorted(directory.glob('*.patch'))]
    return result


def upstream_effective(patch):
    """Use our rebased copy for an upstream patch without editing the upstream file."""
    override = OVERRIDES / patch.relative_to(ROOT)
    return override if override.is_file() else patch


def upstream_key(patch):
    # Overrides keep the upstream path as identity so markers stay comparable.
    base = OVERRIDES if patch.is_relative_to(OVERRIDES) else ROOT
    return patch.relative_to(base).as_posix()


def upstream_digest():
    digest = hashlib.sha256()
    for project, patch in upstream_patches():
        digest.update(upstream_key(patch).encode() + b'\0' + patch.read_bytes())
    return digest.hexdigest()


def ensure_upstream(tree):
    marker = tree / '.repo/lineage-gsi-upstream-applied.json'
    if marker.exists():
        state = json.loads(marker.read_text())
        if state['patches_sha256'] != upstream_digest():
            raise RuntimeError('upstream patch set changed; review/rebase the source checkout first')
        for project, revision in state['projects'].items():
            git(tree / project, 'merge-base', '--is-ancestor', revision, 'HEAD')
        return
    projects = sorted({p for p, _ in upstream_patches()})
    for p in projects:
        if git(tree / p, 'status', '--porcelain'):
            raise RuntimeError(f'dirty upstream project: {p}')
    progress_file = tree / '.repo/lineage-gsi-upstream-progress.json'
    progress = json.loads(progress_file.read_text()) if progress_file.exists() else {}
    for p, patch in upstream_patches():
        key = upstream_key(patch)
        digest = sha(patch)
        if key in progress:
            previous = progress[key]
            if previous['sha256'] != digest:
                raise RuntimeError(f'already applied upstream patch changed: {key}')
            git(tree / p, 'merge-base', '--is-ancestor', previous['commit'], 'HEAD')
            continue
        print('upstream:', p, patch.name, flush=True)
        present = subprocess.run(['git', '-C', str(tree / p), 'apply', '--reverse',
                                  '--check', str(patch)], stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
        if present.returncode == 0:
            print('  already present in the pinned source', flush=True)
        else:
            # Never silently skip a failed upstream patch or leave a failed am session.
            try:
                git(tree / p, 'am', str(patch))
            except subprocess.CalledProcessError:
                git(tree / p, 'am', '--abort')
                raise
        progress[key] = {'sha256': digest, 'commit': git(tree / p, 'rev-parse', 'HEAD')}
        progress_file.write_text(json.dumps(progress, indent=2) + '\n')
    state = {'patches_sha256': upstream_digest(),
             'projects': {p: git(tree / p, 'rev-parse', 'HEAD') for p in projects}}
    marker.write_text(json.dumps(state, indent=2) + '\n')
    progress_file.unlink(missing_ok=True)


def apply_device(tree, check=False):
    projects = {}
    for entry in SERIES:
        projects.setdefault(entry['project'], []).append(REPO / entry['patch'])
    pending = []
    # Later feature patches may overlap an earlier project bundle. Check complete
    # ordered prefixes in a temporary index, never in the working tree. This also
    # accepts an existing build checkout containing only an earlier prefix.
    for name, patches in projects.items():
        project = tree / name
        if git(project, 'status', '--porcelain'):
            raise RuntimeError(f'dirty source project: {project}')
        with tempfile.TemporaryDirectory(prefix='hibreak-index-', dir=tree / '.repo') as temp:
            env = dict(os.environ, GIT_INDEX_FILE=str(Path(temp) / 'index'))
            def apply_index(patch, reverse=False):
                return subprocess.run(
                    ['git', '-C', str(project), 'apply', '--cached',
                     *(['--reverse'] if reverse else []), str(patch)], env=env,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
            for count in range(len(patches), -1, -1):
                run('git', '-C', project, 'read-tree', 'HEAD', env=env)
                if not all(apply_index(p, True) for p in reversed(patches[:count])):
                    continue
                if not all(apply_index(p) for p in patches):
                    continue
                if check and count != len(patches):
                    raise RuntimeError(f'HiBreak patch series is incomplete: {name}')
                pending.extend((project, p) for p in patches[count:])
                break
            else:
                raise RuntimeError(f'cannot identify ordered HiBreak patch state: {name}')
    # All projects are checked before the first mutation; preserve out and caches.
    for project, patch in pending:
        git(project, 'apply', str(patch))
        git(project, 'add', '-A')
        git(project, 'commit', '-m', f'HiBreak: {patch.stem}')
    print(f'HiBreak patches: {len(projects)} projects / {len(SERIES)} patches verified; '
          f'{len(pending)} applied', flush=True)


def configure_debug_adb(tree, enabled, check=False):
    pending = []
    for entry in DEBUG_ADB_SERIES:
        project, patch = tree / entry['project'], REPO / entry['patch']
        if git(project, 'status', '--porcelain'):
            raise RuntimeError(f'dirty debug source project: {project}')
        def applies(reverse):
            return subprocess.run(['git', '-C', str(project), 'apply', '--check',
                *(['--reverse'] if reverse else []), str(patch)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
        present = applies(True)
        if not present and not applies(False):
            raise RuntimeError(f'cannot identify debug patch state: {project}')
        if present != enabled:
            if check:
                raise RuntimeError(f'wrong debug ADB patch state: {project}')
            pending.append((project, patch))
    for project, patch in pending:
        git(project, 'apply', *([] if enabled else ['--reverse']), str(patch))
        git(project, 'add', '-A')
        git(project, 'commit', '-m', ('Enable' if enabled else 'Remove') + ' opt-in debug ADB patch')
    print('Debug ADB:', 'ENABLED (all USB hosts)' if enabled else 'disabled', flush=True)


def stage_inputs(tree, key_path, keys):
    target = tree / 'device/phh/treble/bigme-display/eink_key'
    source = key_path or target
    if not source.is_file() or sha(source) != KEY_SHA:
        raise RuntimeError('provide the stock HiBreak Pro Color /system/eink_key with --eink-key')
    if not target.exists() or target.read_bytes() != source.read_bytes():
        shutil.copyfile(source, target)
    target.chmod(0o644)
    dest = tree / 'vendor/lineage-priv/keys'
    source_keys = keys or dest
    certs = {}
    for name in KEY_NAMES:
        pk8 = source_keys / (name + '.pk8')
        cert = source_keys / (name + '.x509.pem')
        if pk8.stat().st_mode & 0o077:
            raise RuntimeError(f'private key must have mode 0600: {pk8}')
        public = run('openssl', 'pkey', '-inform', 'DER', '-in', pk8, '-passin', 'pass:',
                     '-pubout', capture=True)
        if public != run('openssl', 'x509', '-in', cert, '-pubkey', '-noout', capture=True):
            raise RuntimeError(f'certificate/private-key mismatch: {name}')
        der = run('openssl', 'x509', '-in', cert, '-outform', 'DER', capture=True)
        certs[name] = hashlib.sha256(der).hexdigest()
    dest.mkdir(mode=0o700, parents=True, exist_ok=True)
    for name in (*KEY_NAMES, 'testkey'):
        for suffix in ('.pk8', '.x509.pem'):
            # Android's historical testkey filename aliases our release identity.
            source = source_keys / (('releasekey' if name == 'testkey' else name) + suffix)
            target = dest / (name + suffix)
            if target.exists() and target.read_bytes() != source.read_bytes():
                raise RuntimeError(f'refusing to replace an existing signing identity: {target}')
            if not target.exists():
                target.write_bytes(source.read_bytes())
            target.chmod(0o600)
    config = dest / 'keys.mk'
    content = ('PRODUCT_DEFAULT_DEV_CERTIFICATE := vendor/lineage-priv/keys/releasekey\n'
               'PRODUCT_MAINLINE_BLUETOOTH_SEPOLICY_DEV_CERTIFICATES := vendor/lineage-priv/keys\n')
    if not config.exists() or config.read_text() != content:
        config.write_text(content)
        config.chmod(0o600)
    return certs


def build(args):
    tree = args.tree.resolve()
    product = PRODUCTS[args.variant]
    if git(REPO, 'status', '--porcelain'):
        raise RuntimeError('commit changes in the patch repository before building')
    revision = git(REPO, 'rev-parse', 'HEAD')
    ensure_upstream(tree)
    configure_debug_adb(tree, False)
    apply_device(tree)
    configure_debug_adb(tree, args.debug_adb)
    certs = stage_inputs(tree, args.eink_key, args.keys)
    build_treble_app(tree, args)
    build_mtk_ims(tree, (args.download_cache or tree / '.repo/hibreak-downloads').resolve())
    out_dir = args.out_dir
    out = Path(out_dir) if Path(out_dir).is_absolute() else tree / out_dir
    out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    for key in ('BINDGEN_EXTRA_CLANG_ARGS', 'CPATH', 'C_INCLUDE_PATH', 'CPLUS_INCLUDE_PATH',
                'OBJC_INCLUDE_PATH', 'LIBRARY_PATH', 'NIX_CFLAGS_COMPILE', 'NIX_LDFLAGS',
                'CC', 'CXX', 'CPP', 'CFLAGS', 'CXXFLAGS', 'CPPFLAGS', 'LDFLAGS', 'RUSTFLAGS',
                'DISABLE_AUTO_INSTALLCLEAN'):
        env.pop(key, None)
    number = f'HBPC.23.2.P1.{time.strftime("%Y%m%d.%H%M%S", time.gmtime())}.g{revision[:8]}'
    if args.debug_adb:
        number += '.debug-adb'
    env.update(OUT_DIR=out_dir, BUILD_NUMBER=number, DISPLAY_BUILD_NUMBER='true', BUILD_USERNAME='hibreak',
               BUILD_HOSTNAME='local', ALLOW_NINJA_ENV='true', USE_CCACHE='1')
    if args.ccache_dir:
        env['CCACHE_DIR'] = str(args.ccache_dir.resolve())
    started = time.monotonic()
    run('bash', '-c', '''set -eo pipefail
source build/envsetup.sh >/dev/null
breakfast "$1"
[[ "$(get_build_var PRODUCT_DEFAULT_DEV_CERTIFICATE)" == vendor/lineage-priv/keys/releasekey ]]
[[ "$(get_build_var TARGET_BUILD_VARIANT)" == userdebug ]]
[[ "$(get_build_var BOARD_SYSTEMIMAGE_FILE_SYSTEM_TYPE)" == ext4 ]]
make -j"$2" "$3"
''', 'hibreak-build', product, args.jobs, 'nothing' if args.command == 'check' else 'systemimage',
        cwd=tree, env=env)
    if args.command == 'check':
        return
    image = out / 'target/product/generic_arm64/system.img'
    run('python3', REPO / 'verify-hibreak.py', image, '--tree', tree, '--out', out,
        '--keys', tree / 'vendor/lineage-priv/keys', '--variant', args.variant,
        *(['--debug-adb'] if args.debug_adb else []))
    if git(REPO, 'rev-parse', 'HEAD') != revision or git(REPO, 'status', '--porcelain'):
        raise RuntimeError('patch repository changed during build')
    apply_device(tree, check=True)
    configure_debug_adb(tree, args.debug_adb, check=True)
    if stage_inputs(tree, args.eink_key, args.keys) != certs:
        raise RuntimeError('signing identity changed during build')
    dist = (args.dist or out / 'dist/hibreak').resolve()
    dist.mkdir(parents=True, exist_ok=True)
    flavor = args.variant + ('-debug-adb' if args.debug_adb else '')
    name = f'LineageOS-23.2-{time.strftime("%Y%m%d", time.gmtime())}-{args.variant.upper()}-EXT4-GSI' + ('-DEBUG-ADB' if args.debug_adb else '') + '.img'
    # Keep upstream filenames while making each build immutable in its own directory.
    archive = dist / number
    archive.mkdir(exist_ok=False)
    name = str(Path(number) / name)
    target = dist / name
    shutil.copyfile(image, target)
    digest = sha(target)
    manifest = Path(str(target) + '.manifest.xml')
    run('repo', 'manifest', '-r', '-o', manifest, cwd=tree)
    info = {'patch_repository_commit': revision, 'product': product, 'variant': args.variant,
            'filesystem': 'ext4', 'debug_adb': args.debug_adb, 'build_number': number,
            'image_sha256': digest, 'image_size': target.stat().st_size,
            'manifest_sha256': sha(manifest), 'apk_certificates_sha256': certs,
            'build_elapsed_seconds': round(time.monotonic() - started, 1),
            'out_dir': str(out.resolve()), 'ccache_dir': env.get('CCACHE_DIR')}
    Path(str(target) + '.build-info').write_text(json.dumps(info, indent=2) + '\n')
    Path(str(target) + '.sha256').write_text(f'{digest}  {Path(name).name}\n')
    latest = 'latest-debug-adb' if args.debug_adb else 'latest'
    for link, value in [(latest + '.img', name), (latest + '.build-info', name + '.build-info'),
                        (f'latest-{flavor}-ext4.img', name),
                        (f'latest-{flavor}-ext4.build-info', name + '.build-info')]:
        temp = dist / ('.' + link + '.tmp')
        temp.unlink(missing_ok=True)
        temp.symlink_to(value)
        temp.replace(dist / link)
    (dist / (latest + '.img.sha256')).write_text(f'{digest}  {latest}.img\n')
    variant_link = f'latest-{flavor}-ext4.img'
    (dist / (variant_link + '.sha256')).write_text(f'{digest}  {variant_link}\n')
    print('Verified system image:', target)
    print('Build number:', number)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['apply', 'build', 'check'])
    parser.add_argument('--tree', type=Path, required=True)
    parser.add_argument('--variant', choices=PRODUCTS, default='vanilla',
                        help='EXT4 image flavor; both use the same source/output/cache')
    parser.add_argument('--debug-adb', action='store_true',
                        help='Opt-in debug image: USB ADB accepts all hosts; enables adb root on request')
    parser.add_argument('--upstream-only', action='store_true')
    parser.add_argument('--eink-key', type=Path)
    parser.add_argument('--keys', type=Path)
    parser.add_argument('--out-dir', default=os.environ.get('OUT_DIR', 'out'))
    parser.add_argument('--ccache-dir', type=Path)
    parser.add_argument('--treble-java-home', type=Path,
                        default=os.environ.get('HIBREAK_TREBLE_JAVA_HOME'),
                        help='JDK 17 for the upstream TrebleApp Gradle build')
    parser.add_argument('--gradle-user-home', type=Path,
                        help='Reusable Gradle download/build cache')
    parser.add_argument('--android-sdk-root', type=Path,
                        help='Android SDK cache for the TrebleApp build')
    parser.add_argument('--download-cache', type=Path,
                        help='Pinned downloads (MediaTek IMS APK, apktool); reused offline')
    parser.add_argument('--dist', type=Path)
    parser.add_argument('-j', '--jobs', type=int, default=int(os.environ.get('BUILD_JOBS', '16')))
    args = parser.parse_args()
    if args.jobs < 1 or not (args.tree / '.repo').is_dir():
        parser.error('a repo-managed source tree and a positive job count are required')
    if args.command == 'apply':
        ensure_upstream(args.tree.resolve())
        configure_debug_adb(args.tree.resolve(), False)
        if not args.upstream_only:
            apply_device(args.tree.resolve())
            configure_debug_adb(args.tree.resolve(), args.debug_adb)
    else:
        build(args)


if __name__ == '__main__':
    main()
