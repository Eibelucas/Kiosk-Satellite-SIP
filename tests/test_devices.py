"""Multiple SIP identities, external routing and secret redaction."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'kiosk_sip/app'))
from configuration import Settings, asterisk_files, validate


def device(extension, name='Kiosk', **changes):
    return dict(extension=extension, name=name, password='fake-device-secret-' + extension, enabled=True, **changes)


def config(**changes):
    return validate({**dict(enabled=True, phone_number='+4900001234567', listen_address='10.99.0.20',
                           local_network='10.99.0.0/24', phone_password='fake-legacy-secret',
                           devices=[device('101', 'Küche'), device('102', 'Büro')]), **changes})


def test_separate_endpoint_auth_and_aor_for_every_device():
    cfg = config()
    files = asterisk_files(cfg, 'fake-ami-secret')
    for ext in ('101', '102'):
        assert f'auth=device-{ext}-auth' in files['pjsip.conf']
        assert f'username={ext}\npassword=fake-device-secret-{ext}' in files['pjsip.conf']
        assert f'exten => {ext},1,Dial(PJSIP/{ext},30)' not in files['extensions.conf']
    assert files['pjsip.conf'].count('max_contacts=1') == 3
    assert 'Dial(PJSIP/101&PJSIP/102,45)' in files['extensions.conf']
    assert 'exten => _1XX,1,Hangup(1)' in files['extensions.conf']


def test_line_can_ring_one_selected_device():
    prior = config()
    line = {**prior['lines'][0], 'incoming_devices': ['102']}
    cfg = validate({'lines': [line]}, prior)
    dial = asterisk_files(cfg, 'fake-ami-secret')['extensions.conf']
    assert '[incoming-main]\nexten => s,1,Dial(PJSIP/102,45)' in dial
    assert 'Dial(PJSIP/101&PJSIP/102,45)' not in dial


def test_device_password_preserved_only_for_same_extension():
    prior = config()
    cfg = validate({'devices': [{'extension': '101', 'name': 'Neuer Name', 'enabled': True, 'password': ''}]}, prior)
    assert cfg['devices'][0]['password'] == 'fake-device-secret-101'
    with pytest.raises(ValueError, match='Geräte-SIP-Passwort'):
        validate({'devices': [{'extension': '103', 'name': 'Neues Gerät', 'enabled': True, 'password': ''}]}, prior)


@pytest.mark.parametrize('devices', [
    [device('101'), device('101')], [device('100')], [device('600')], [device('101\n')],
    [{**device('101'), 'password': 'short'}], [{**device('101'), 'name': 'bad\nname'}],
    [{**device('101'), 'enabled': 'true'}], [{**device('101'), 'unknown': 'x'}],
])
def test_invalid_devices_rejected(devices):
    with pytest.raises(ValueError):
        config(devices=devices)


def test_multi_devices_do_not_need_legacy_password():
    cfg = config(phone_password='')
    assert cfg['phone_password'] == ''
    assert 'username=100\n' not in asterisk_files(cfg, 'fake-ami-secret')['pjsip.conf']


def test_disabled_and_missing_ring_targets_rejected():
    prior = config()
    for target in ('103', '600'):
        with pytest.raises(ValueError):
            validate({'lines': [{**prior['lines'][0], 'incoming_devices': [target]}]}, prior)
    prior['devices'][1]['enabled'] = False
    with pytest.raises(ValueError, match='aktive Geräte'):
        validate({'lines': [{**prior['lines'][0], 'incoming_devices': ['102']}]}, prior)


def test_disabled_endpoint_is_not_generated_or_rung():
    prior = config()
    cfg = validate({'devices': [{**d, 'enabled': d['extension'] != '102'} for d in prior['devices']]}, prior)
    files = asterisk_files(cfg, 'fake-ami-secret')
    assert 'username=102' not in files['pjsip.conf']
    assert '[incoming-main]\nexten => s,1,Dial(PJSIP/101,45)' in files['extensions.conf']


@pytest.fixture
def instance():
    # No POSIX storage calls are needed for these read-only API checks.
    settings = Settings.__new__(Settings)
    settings.value = config(lan_enabled=True, web_password='fake-web-secret-123')
    settings.session_secret = 'fake-test-session'

    return settings


def test_public_settings_redact_all_device_secrets(instance):
    settings = instance
    public = settings.public()
    assert public['devices'][0]['password_set'] is True
    assert 'password' not in public['devices'][0]
    assert all(d['password'] not in json.dumps(public) for d in settings.value['devices'])
