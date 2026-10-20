#!/usr/bin/env python3
"""Verify the exact Kiosk Satellite package and checksum format before publishing."""
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile
from plugin_contract import validate_manifest

root = Path(__file__).resolve().parents[1]
dist = root / 'dist'
manifest_bytes = (dist / 'kiosk-satellite-plugin.json').read_bytes()
manifest = json.loads(manifest_bytes)
validate_manifest(manifest)
assert re.fullmatch(r'\d+\.\d+\.\d+(?:-lab\.\d+)?', manifest['version'])
if '-lab.' in manifest['version']:
    assert manifest['id'] == 'kiosk-satellite-sip-native-lab'
else:
    assert manifest['id'] == 'kiosk-satellite-sip'
package = dist / f"{manifest['id']}-{manifest['version']}.zip"
assert package.stat().st_size <= 4 * 1024 * 1024
with zipfile.ZipFile(package) as archive:
    expected = {'kiosk-satellite-plugin.json', 'plugin.jar', 'LICENSE'}
    if manifest.get('icon'):
        expected.add(manifest['icon'])
        icon_bytes = archive.read(manifest['icon'])
        assert icon_bytes == (root / manifest['icon']).read_bytes()
        assert len(icon_bytes) <= 256 * 1024
        assert icon_bytes[:16] == b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'
        assert int.from_bytes(icon_bytes[16:20], 'big') == 256
        assert int.from_bytes(icon_bytes[20:24], 'big') == 256
    assert len(archive.namelist()) == len(expected)
    assert set(archive.namelist()) == expected
    assert archive.read('kiosk-satellite-plugin.json') == manifest_bytes
    assert archive.read('LICENSE') == (root / 'LICENSE').read_bytes()
    with zipfile.ZipFile(io.BytesIO(archive.read('plugin.jar'))) as jar:
        assert 'classes.dex' in jar.namelist()
        assert jar.read('classes.dex').startswith(b'dex\n')
digest = hashlib.sha256(package.read_bytes()).hexdigest()
assert (dist / (package.name+'.sha256')).read_text() == f'{digest}  {package.name}\n'
print(f'PASS: version {manifest["version"]}, ZIP root, identical manifests, DEX, LICENSE, icon and SHA-256.')
