"""Container test: real PJSIP registration with fake data, no provider or calls."""
import hashlib
import os
import pwd
import re
import socket
import subprocess
import sys
import tempfile
import time
import uuid
import threading
import queue
from pathlib import Path

sys.path.insert(0, "/app")
from configuration import DEFAULTS, asterisk_files


def main():
    user = pwd.getpwnam("asterisk")
    base = Path(tempfile.mkdtemp(prefix="sip-smoke-"))
    base.chmod(0o755)
    for sub in ("config", "run", "db", "spool", "log"):
        path = base / sub
        path.mkdir()
        os.chown(path, user.pw_uid, user.pw_gid)
    password = "fake-phone;secret\\with-punctuation"
    cfg = {**DEFAULTS, "phone_password": password, "listen_address": "127.0.0.1",
           "local_network": "127.0.0.1/32", "sip_port": 15070}
    cfg['phone_number'] = '+4921611234567'
    cfg['lines'] = [{**cfg, 'id':'main', 'label':'Main', 'provider':'custom', 'enabled':True,
                     'incoming_mode':'normal', 'auth_mode':'password', 'auth_username':'fake',
                     'auth_password':'fake-provider-secret', 'registrar':'127.0.0.1:15071',
                     'domain':'127.0.0.1', 'client_user':'+4921611234567', 'contact_user':'+4921611234567',
                     'from_user':'+4921611234567', 'stun_server':''},
                    {**cfg, 'id':'second', 'label':'Second', 'provider':'custom', 'enabled':True,
                     'incoming_mode':'reject', 'phone_number':'+4921611234568', 'auth_mode':'password', 'auth_username':'fake2',
                     'auth_password':'fake-provider-secret2', 'registrar':'127.0.0.1:15071',
                     'domain':'127.0.0.1', 'client_user':'+4921611234568', 'contact_user':'+4921611234568',
                     'from_user':'+4921611234568', 'stun_server':''}]
    responses = queue.Queue()
    registrar = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    registrar.bind(('127.0.0.1',15071)); registrar.settimeout(.5)
    stopped = threading.Event()
    def sip_headers(msg):
        return [row for row in msg.split('\r\n') if row.startswith(('Via:','From:','To:','Call-ID:','CSeq:'))]
    def serve_registrar():
        while not stopped.is_set():
            try: packet,peer=registrar.recvfrom(16384)
            except socket.timeout: continue
            except OSError: return
            msg=packet.decode()
            if msg.startswith('REGISTER '):
                contact=next(row for row in msg.split('\r\n') if row.startswith('Contact:'))
                reply='SIP/2.0 200 OK\r\n'+'\r\n'.join(sip_headers(msg))+f'\r\n{contact};expires=120\r\nExpires: 120\r\nContent-Length: 0\r\n\r\n'
                registrar.sendto(reply.encode(),peer)
            else: responses.put(msg)
    threading.Thread(target=serve_registrar,daemon=True).start()
    files = asterisk_files(cfg, "fake-ami-secret")
    # The tiny fake phone has no background OPTIONS handler while waiting for
    # provider registrations; disable qualification for this test phone only.
    files['pjsip.conf'] = files['pjsip.conf'].replace('qualify_frequency=30','qualify_frequency=0')
    # Independent config/control socket/database; do not stop the running add-on.
    files["manager.conf"] = "[general]\nenabled=no\n"
    for old, new in (("/etc/asterisk", str(base / "config")), ("/run/asterisk", str(base / "run")),
                     ("/data/asterisk", str(base / "db")), ("/var/log/asterisk", str(base / "log")),
                     ("/var/spool/asterisk", str(base / "spool"))):
        files["asterisk.conf"] = files["asterisk.conf"].replace(old, new)
    for name, content in files.items():
        path = base / "config" / name
        path.write_text(content)
        os.chown(path, 0, user.pw_gid)
        path.chmod(0o640)
    astconf = str(base / "config" / "asterisk.conf")
    process = subprocess.Popen(["asterisk", "-f", "-C", astconf, "-U", "asterisk", "-G", "asterisk"])
    try:
        for _ in range(50):
            result = subprocess.run(["asterisk", "-C", astconf, "-rx", "core show uptime"], capture_output=True, text=True)
            if "System uptime" in result.stdout:
                break
            time.sleep(.2)
        assert process.poll() is None, "Test Asterisk stopped"
        # SIP modules can finish loading just after the control socket opens.
        time.sleep(1)
        for function in ('CALLERID','PJSIP_HEADER','FILTER'):
            loaded=subprocess.check_output(['asterisk','-C',astconf,'-rx','core show function '+function],text=True)
            assert 'No function by that name' not in loaded and 'Syntax' in loaded,loaded
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
            client.bind(("127.0.0.1", 0))
            client.settimeout(5)
            local_port = client.getsockname()[1]
            call_id = str(uuid.uuid4())
            uri = "sip:127.0.0.1:15070"

            def register(cseq, auth=""):
                msg = (f"REGISTER {uri} SIP/2.0\r\nVia: SIP/2.0/UDP 127.0.0.1:{local_port};branch=z9hG4bK{uuid.uuid4().hex};rport\r\n"
                       f"Max-Forwards: 70\r\nFrom: <sip:100@127.0.0.1>;tag=fake\r\nTo: <sip:100@127.0.0.1>\r\n"
                       f"Call-ID: {call_id}\r\nCSeq: {cseq} REGISTER\r\nContact: <sip:100@127.0.0.1:{local_port}>\r\n"
                       f"Expires: 120\r\n{auth}Content-Length: 0\r\n\r\n")
                client.sendto(msg.encode(), ("127.0.0.1", 15070))
                return client.recv(16384).decode()

            challenge = register(1)
            assert challenge.startswith("SIP/2.0 401"), challenge.splitlines()[0]
            values = dict(re.findall(r'([a-z_]+)="([^"]+)"', challenge, re.I))
            realm, nonce = values["realm"], values["nonce"]
            md5 = lambda text: hashlib.md5(text.encode()).hexdigest()
            ha1, ha2 = md5(f"100:{realm}:{password}"), md5(f"REGISTER:{uri}")
            cnonce, nc = uuid.uuid4().hex, "00000001"
            response = md5(f"{ha1}:{nonce}:{nc}:{cnonce}:auth:{ha2}") if "qop" in values else md5(f"{ha1}:{nonce}:{ha2}")
            auth = f'Authorization: Digest username="100", realm="{realm}", nonce="{nonce}", uri="{uri}", response="{response}", algorithm=MD5'
            if "qop" in values:
                auth += f', qop=auth, nc={nc}, cnonce="{cnonce}"'
            answer = register(2, auth + "\r\n")
            assert answer.startswith("SIP/2.0 200"), answer.splitlines()[0]
            contacts=subprocess.check_output(['asterisk','-C',astconf,'-rx','pjsip show contacts'],text=True)
            assert '100/sip:100@' in contacts,contacts
            # Two fake accounts share the same registrar. Real INVITEs must route
            # by their called number; the secondary account is rejected, never dialed out.
            for _ in range(40):
                result=subprocess.check_output(['asterisk','-C',astconf,'-rx','pjsip show registrations'],text=True)
                if result.count(' Registered')>=2: break
                time.sleep(.2)
            assert result.count(' Registered')>=2,result
            def invite(destination, expect_phone, expected_code=None):
                ident=uuid.uuid4().hex
                sdp='v=0\r\no=fake 1 1 IN IP4 127.0.0.1\r\ns=Test\r\nc=IN IP4 127.0.0.1\r\nt=0 0\r\nm=audio 41000 RTP/AVP 8\r\na=rtpmap:8 PCMA/8000\r\na=sendrecv\r\n'
                request=(f'INVITE sip:{destination}@127.0.0.1:15070 SIP/2.0\r\nVia: SIP/2.0/UDP 127.0.0.1:15071;branch=z9hG4bK{ident};rport\r\nMax-Forwards: 70\r\nFrom: <sip:+491701234567@127.0.0.1>;tag={ident}\r\nTo: <sip:{destination}@127.0.0.1>\r\nCall-ID: {ident}\r\nCSeq: 1 INVITE\r\nContact: <sip:fake@127.0.0.1:15071>\r\nContent-Type: application/sdp\r\nContent-Length: {len(sdp)}\r\n\r\n{sdp}')
                registrar.sendto(request.encode(),('127.0.0.1',15070))
                if expect_phone:
                    while True:
                        phone_msg=client.recv(16384).decode()
                        if phone_msg.startswith('INVITE '):break
                        # Answer qualify OPTIONS if it races the test.
                        if phone_msg.startswith('OPTIONS '):
                            client.sendto(('SIP/2.0 200 OK\r\n'+'\r\n'.join(sip_headers(phone_msg))+'\r\nContent-Length: 0\r\n\r\n').encode(),('127.0.0.1',15070))
                    assert 'sip:100@' in phone_msg.splitlines()[0],phone_msg
                    assert 'answer-after=0' not in phone_msg,phone_msg
                    client.sendto(('SIP/2.0 486 Busy Here\r\n'+'\r\n'.join(sip_headers(phone_msg))+'\r\nContent-Length: 0\r\n\r\n').encode(),('127.0.0.1',15070))
                deadline=time.monotonic()+6
                while time.monotonic()<deadline:
                    reply=responses.get(timeout=6)
                    if f'Call-ID: {ident}' in reply and reply.startswith('SIP/2.0 ') and int(reply.split()[1])>=300:
                        break
                else: raise AssertionError('No final response for test INVITE')
                code=int(reply.split()[1])
                assert code==(expected_code or (486 if expect_phone else 403)),(destination,reply)
            invite('+4921611234567',True)
            invite('+4921611234568',False)
            invite('+4921619999999',False,404)
        dialplan = subprocess.check_output(["asterisk", "-C", astconf, "-rx", "dialplan show 600@from-phone"], text=True)
        assert "Echo()" in dialplan, dialplan
        print("PASS: real Asterisk startup, authenticated local SIP REGISTER, password punctuation, two fake provider registrations, normal/secondary incoming routing and echo dialplan. No external call made.")
    finally:
        stopped.set(); registrar.close()
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


if __name__ == "__main__":
    main()
