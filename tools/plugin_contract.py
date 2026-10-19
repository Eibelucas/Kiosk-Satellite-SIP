"""Validate the native manifest fields required by KS PluginManifest.validateFields.

The host requires a default for EVERY top-level setting, including empty secrets.
Reference: jxlarrea/kiosk-satellite PluginManifest.kt, checked 2026-10-19.
"""
import re


def validate_manifest(manifest):
    if manifest.get('schemaVersion') != 1 or manifest.get('apiVersion') != 1:
        raise ValueError('SDK 1 manifest required')
    for key, limit in [('id', 64), ('name', 80), ('version', 40), ('entryClass', 200),
                       ('description', 1000), ('author', 120), ('license', 120)]:
        value = manifest.get(key)
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            raise ValueError(f'Invalid {key}')
    settings = manifest.get('settings', [])
    if not isinstance(settings, list) or len(settings) > 50:
        raise ValueError('Invalid settings')
    seen = set()
    for field in settings:
        key = field.get('key')
        if not isinstance(key, str) or not re.fullmatch(r'[a-zA-Z][a-zA-Z0-9_]{0,63}', key) or key in seen:
            raise ValueError('Invalid setting key')
        seen.add(key)
        if not isinstance(field.get('title'), str) or not field['title'].strip() or len(field['title']) > 80:
            raise ValueError(f'Invalid title: {key}')
        if 'default' not in field:
            raise ValueError(f'Missing default for setting: {key}')
        kind, value = field.get('type'), field['default']
        if kind in {'string', 'secret'}:
            if not isinstance(value, str) or len(value) > 512:
                raise ValueError(f'Invalid text default: {key}')
            if kind == 'secret' and value != '':
                raise ValueError(f'Secret default must be empty: {key}')
        elif kind == 'select':
            choices = field.get('options', [])
            if not isinstance(choices, list) or not 1 <= len(choices) <= 32 or any(not isinstance(c, str) or not c.strip() or len(c) > 80 for c in choices) or len(set(choices)) != len(choices) or value not in choices:
                raise ValueError(f'Invalid select default: {key}')
        elif kind == 'boolean':
            if type(value) is not bool:
                raise ValueError(f'Invalid boolean default: {key}')
        else:
            raise ValueError(f'Native lab contract checker does not support {kind}')
