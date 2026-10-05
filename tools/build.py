#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 4 * 1024 * 1024

parser = argparse.ArgumentParser()
parser.add_argument('--version')
parser.add_argument('--android-platform', default='35')
args = parser.parse_args()

manifest_path = ROOT / 'kiosk-satellite-plugin.json'
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
if args.version:
    manifest['version'] = args.version
manifest_bytes = (json.dumps(manifest, indent=2, ensure_ascii=False) + '\n').encode('utf-8')

sdk_root = Path(os.environ.get('ANDROID_HOME', os.environ.get('ANDROID_SDK_ROOT', str(Path.home() / 'android-sdk'))))
android_jar = sdk_root / 'platforms' / f"android-{args.android_platform}" / 'android.jar'
if not android_jar.is_file():
    raise SystemExit(f'Missing Android platform: {android_jar}')

build_tools = sorted((sdk_root / 'build-tools').glob('*/d8'))
if not build_tools:
    raise SystemExit('Android d8 was not found. Install Android build-tools.')
d8 = build_tools[-1]

java_home = os.environ.get('JAVA_HOME')
def jtool(name):
    return str(Path(java_home) / 'bin' / name) if java_home else name

out = ROOT / 'dist'
out.mkdir(exist_ok=True)

with tempfile.TemporaryDirectory(prefix='kiosk-sip-plugin-') as temp_name:
    temp = Path(temp_name)
    sdk_classes = temp / 'sdk-classes'
    plugin_classes = temp / 'plugin-classes'
    dex_dir = temp / 'dex'
    sdk_classes.mkdir()
    plugin_classes.mkdir()
    dex_dir.mkdir()

    sdk_sources = [str(p) for p in sorted((ROOT / 'sdk' / 'src').rglob('*.java'))]
    plugin_sources = [str(p) for p in sorted((ROOT / 'src').rglob('*.java'))]
    if not sdk_sources or not plugin_sources:
        raise SystemExit('Missing SDK or plugin Java sources')

    subprocess.run([jtool('javac'), '--release', '8', '-d', str(sdk_classes), *sdk_sources], check=True)
    sdk_jar = out / 'kiosk-plugin-sdk-1.jar'
    subprocess.run([jtool('jar'), 'cf', str(sdk_jar), '-C', str(sdk_classes), '.'], check=True)

    cp = os.pathsep.join([str(sdk_jar), str(android_jar)])
    subprocess.run([jtool('javac'), '--release', '8', '-cp', cp, '-d', str(plugin_classes), *plugin_sources], check=True)
    subprocess.run([
        str(d8), '--min-api', str(manifest['minAndroidSdk']),
        '--lib', str(android_jar), '--classpath', str(sdk_jar),
        '--output', str(dex_dir),
        *[str(p) for p in sorted(plugin_classes.rglob('*.class'))]
    ], check=True)

    plugin_jar = temp / 'plugin.jar'
    with zipfile.ZipFile(plugin_jar, 'w', zipfile.ZIP_DEFLATED) as archive:
        for dex in sorted(dex_dir.glob('*.dex')):
            archive.write(dex, dex.name)

    package = out / f"{manifest['id']}-{manifest['version']}.zip"
    with zipfile.ZipFile(package, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('kiosk-satellite-plugin.json', manifest_bytes)
        archive.write(plugin_jar, 'plugin.jar')
        archive.write(ROOT / 'LICENSE', 'LICENSE')

    if package.stat().st_size > MAX_BYTES:
        package.unlink()
        raise SystemExit('Plugin package exceeds Kiosk Satellite 4 MB limit')

    shutil.copyfile(manifest_path, out / 'kiosk-satellite-plugin.json')
    print(package)
