#!/usr/bin/env python3
"""Verify the exact Kiosk Satellite package and checksum format before publishing."""
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

root = Path(__file__).resolve().parents[1]
dist = root / 'dist'
manifest_bytes = (dist / 'kiosk-satellite-plugin.json').read_bytes()
manifest = json.loads(manifest_bytes)
assert re.fullmatch(r'\d+\.\d+\.\d+', manifest['version'])
package = dist / f"{manifest['id']}-{manifest['version']}.zip"
assert package.stat().st_size <= 4 * 1024 * 1024
with zipfile.ZipFile(package) as archive:
    assert set(archive.namelist()) == {'kiosk-satellite-plugin.json','plugin.jar','LICENSE'}
    assert archive.read('kiosk-satellite-plugin.json') == manifest_bytes
    assert archive.read('LICENSE') == (root / 'LICENSE').read_bytes()
    with zipfile.ZipFile(io.BytesIO(archive.read('plugin.jar'))) as jar:
        assert 'classes.dex' in jar.namelist()
        assert jar.read('classes.dex').startswith(b'dex\n')
digest = hashlib.sha256(package.read_bytes()).hexdigest()
assert (dist / (package.name+'.sha256')).read_text() == f'{digest}  {package.name}\n'
print(f'PASS: version {manifest["version"]}, ZIP root, identical manifests, DEX, LICENSE and SHA-256.')
