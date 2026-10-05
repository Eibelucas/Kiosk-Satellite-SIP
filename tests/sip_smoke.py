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
import struct
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
    cfg['lines'].append({**cfg['lines'][1], 'id':'page', 'phone_number':'+4921611234569',
        'client_user':'+4921611234569', 'contact_user':'+4921611234569', 'from_user':'+4921611234569',
        'incoming_mode':'announcement', 'announcement_callers':['+491701234567'],
        'announcement_auto_answer':True, 'announcement_max_seconds':30, 'announcement_pin':''})
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
    files['pjsip.conf'] = files['pjsip.conf'].replace('qualify_frequency=30','qualify_frequency=0').replace('expiration=600','expiration=600\nmax_random_initial_delay=0')
    # Independent config/control socket/database; do not stop the running add-on.
    files["logger.conf"] = "[general]\n[logfiles]\nconsole=verbose,notice,warning,error\n"
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
    process = subprocess.Popen(["asterisk", "-f", "-vvv", "-C", astconf, "-U", "asterisk", "-G", "asterisk"])
    try:
        for _ in range(50):
            result = subprocess.run(["asterisk", "-C", astconf, "-rx", "core show uptime"], capture_output=True, text=True)
            if "System uptime" in result.stdout:
                break
            time.sleep(.2)
        assert process.poll() is None, "Test Asterisk stopped"
        # SIP modules can finish loading just after the control socket opens.
        time.sleep(1)
        for function in ('CALLERID','PJSIP_HEADER','FILTER','GROUP_COUNT','TIMEOUT'):
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
                if result.count(' Registered')>=3: break
                time.sleep(.2)
            assert result.count(' Registered')>=3,result
            def invite(destination, expect_phone, expected_code=None, caller='+491701234567', page=False):
                ident=uuid.uuid4().hex
                sdp='v=0\r\no=fake 1 1 IN IP4 127.0.0.1\r\ns=Test\r\nc=IN IP4 127.0.0.1\r\nt=0 0\r\nm=audio 41000 RTP/AVP 8\r\na=rtpmap:8 PCMA/8000\r\na=sendrecv\r\n'
                request=(f'INVITE sip:{destination}@127.0.0.1:15070 SIP/2.0\r\nVia: SIP/2.0/UDP 127.0.0.1:15071;branch=z9hG4bK{ident};rport\r\nMax-Forwards: 70\r\nFrom: <sip:{caller}@127.0.0.1>;tag={ident}\r\nTo: <sip:{destination}@127.0.0.1>\r\nCall-ID: {ident}\r\nCSeq: 1 INVITE\r\nContact: <sip:fake@127.0.0.1:15071>\r\nContent-Type: application/sdp\r\nContent-Length: {len(sdp)}\r\n\r\n{sdp}')
                registrar.sendto(request.encode(),('127.0.0.1',15070))
                if expect_phone:
                    while True:
                        phone_msg=client.recv(16384).decode()
                        if phone_msg.startswith('INVITE '):break
                        # Answer qualify OPTIONS if it races the test.
                        if phone_msg.startswith('OPTIONS '):
                            client.sendto(('SIP/2.0 200 OK\r\n'+'\r\n'.join(sip_headers(phone_msg))+'\r\nContent-Length: 0\r\n\r\n').encode(),('127.0.0.1',15070))
                    assert 'sip:100@' in phone_msg.splitlines()[0],phone_msg
                    assert ('answer-after=0' in phone_msg)==page,phone_msg
                    if page:
                        assert 'info=alert-autoanswer' in phone_msg,phone_msg
                        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as source_rtp, socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as phone_rtp:
                            source_rtp.bind(('127.0.0.1',41000)); source_rtp.settimeout(.1)
                            phone_rtp.bind(('127.0.0.1',42000)); phone_rtp.settimeout(.1)
                            phone_sdp=sdp.replace('41000','42000')
                            rows=[row+';tag=fakephone' if row.startswith('To:') else row for row in sip_headers(phone_msg)]
                            client.sendto(('SIP/2.0 200 OK\r\n'+'\r\n'.join(rows)+f'\r\nContact: <sip:100@127.0.0.1:{local_port}>\r\nContent-Type: application/sdp\r\nContent-Length: {len(phone_sdp)}\r\n\r\n{phone_sdp}').encode(),('127.0.0.1',15070))
                            deadline=time.monotonic()+5
                            while time.monotonic()<deadline:
                                reply=responses.get(timeout=5)
                                if f'Call-ID: {ident}' in reply and reply.startswith('SIP/2.0 200'):break
                            else:raise AssertionError('Page did not answer source')
                            source_port=int(re.search(r'm=audio (\d+)',reply).group(1))
                            phone_port=int(re.search(r'm=audio (\d+)',phone_msg).group(1))
                            dialog_rows=sip_headers(reply)
                            def dialog(method,seq):
                                rows=[row for row in dialog_rows if not row.startswith(('Via:','CSeq:'))]
                                wire=f'{method} sip:{destination}@127.0.0.1:15070 SIP/2.0\r\nVia: SIP/2.0/UDP 127.0.0.1:15071;branch=z9hG4bK{uuid.uuid4().hex};rport\r\n'+'\r\n'.join(rows)+f'\r\nCSeq: {seq} {method}\r\nMax-Forwards: 70\r\nContent-Length: 0\r\n\r\n'
                                registrar.sendto(wire.encode(),('127.0.0.1',15070))
                            dialog('ACK',1)
                            received=[]
                            for seq in range(35):
                                payload=bytes([0x80 if seq%2 else 0x00])*160
                                source_rtp.sendto(struct.pack('!BBHII',0x80,8,seq,seq*160,1234)+payload,('127.0.0.1',source_port))
                                time.sleep(.02)
                                try:received.append(phone_rtp.recv(4096)[12:])
                                except socket.timeout:pass
                            assert any(p and any(v not in (0xD5,0x55) for v in p) for p in received),'No announcement audio reached fake speaker'
                            # With the source now quiet, inject audio from the target.
                            # Muted Page participants must not send it back to the caller.
                            time.sleep(.25)
                            source_rtp.settimeout(.001)
                            while True:
                                try:source_rtp.recv(4096)
                                except socket.timeout:break
                            source_rtp.settimeout(.05)
                            reverse=[]
                            for seq in range(25):
                                phone_rtp.sendto(struct.pack('!BBHII',0x80,8,seq,seq*160,4321)+bytes([0x80])*160,('127.0.0.1',phone_port))
                                time.sleep(.02)
                                try:reverse.append(source_rtp.recv(4096)[12:])
                                except socket.timeout:pass
                            assert all(all(v in (0xD5,0x55) for v in p) for p in reverse),'Target microphone leaked into announcement'
                            dialog('BYE',2)
                        return
                    rows=[row+';tag=fakephone' if row.startswith('To:') else row for row in sip_headers(phone_msg)]
                    client.sendto(('SIP/2.0 486 Busy Here\r\n'+'\r\n'.join(rows)+'\r\nContent-Length: 0\r\n\r\n').encode(),('127.0.0.1',15070))
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
            invite('+4921611234569',False,403,caller='+491709999999')
            invite('+4921611234569',False,403,caller='anonymous')
            invite('+4921611234569',True,page=True)
        dialplan = subprocess.check_output(["asterisk", "-C", astconf, "-rx", "dialplan show 600@from-phone"], text=True)
        assert "Echo()" in dialplan, dialplan
        print("PASS: real Asterisk startup, authenticated local SIP REGISTER, password punctuation, three fake provider registrations, isolated incoming routing, announcement allowlist, Auto-Answer headers and one-way RTP audio and echo dialplan. No external call made.")
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
