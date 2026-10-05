#!/usr/bin/env python3
import json
import os
import re
import socket
import uuid
from pathlib import Path
from flask import Flask, jsonify, render_template, request

BASE_DIR = Path(__file__).resolve().parent
CONTACTS_FILE = Path(os.environ.get("CONTACTS_FILE", BASE_DIR / "contacts.json"))

app = Flask(__name__)

NUMBER_RE = re.compile(r"^\+?[0-9]{3,20}$")


def env(name, default=""):
    return os.environ.get(name, default).strip()


def read_ami_frame(sock_file):
    lines = []
    while True:
        line = sock_file.readline()
        if not line:
            break
        text = line.decode("utf-8", errors="replace").rstrip("\r\n")
        if not text:
            if lines:
                break
            continue
        lines.append(text)
    frame = {}
    for line in lines:
        if ":" in line:
            key, value = line.split(":", 1)
            frame[key.strip()] = value.strip()
    return frame


def send_ami_action(sock, sock_file, fields):
    payload = "".join(f"{key}: {value}\r\n" for key, value in fields.items()) + "\r\n"
    sock.sendall(payload.encode("utf-8"))
    return read_ami_frame(sock_file)


def originate(number):
    host = env("AMI_HOST")
    username = env("AMI_USERNAME")
    secret = env("AMI_SECRET")
    channel = env("ASTERISK_CHANNEL")
    context = env("ASTERISK_CONTEXT", "from-kiosk-phone")
    caller_id = env("ASTERISK_CALLER_ID", "Kiosk Satellite")
    port = int(env("AMI_PORT", "5038"))

    missing = [name for name, value in {
        "AMI_HOST": host,
        "AMI_USERNAME": username,
        "AMI_SECRET": secret,
        "ASTERISK_CHANNEL": channel,
    }.items() if not value]
    if missing:
        raise RuntimeError("Missing configuration: " + ", ".join(missing))

    action_id = str(uuid.uuid4())
    with socket.create_connection((host, port), timeout=5) as sock:
        sock.settimeout(5)
        sock_file = sock.makefile("rb")
        # AMI greeting
        sock_file.readline()

        login = send_ami_action(sock, sock_file, {
            "Action": "Login",
            "Username": username,
            "Secret": secret,
            "Events": "off",
            "ActionID": action_id + "-login",
        })
        if login.get("Response") != "Success":
            raise RuntimeError(login.get("Message", "AMI login failed"))

        response = send_ami_action(sock, sock_file, {
            "Action": "Originate",
            "Channel": channel,
            "Context": context,
            "Exten": number,
            "Priority": "1",
            "CallerID": caller_id,
            "Async": "true",
            "Variable": f"KIOSK_SIP_DESTINATION={number}",
            "ActionID": action_id,
        })

        try:
            send_ami_action(sock, sock_file, {"Action": "Logoff"})
        except Exception:
            pass

        if response.get("Response") != "Success":
            raise RuntimeError(response.get("Message", "Asterisk rejected originate"))
        return {"action_id": action_id, "message": response.get("Message", "Originate queued")}


def load_contacts():
    try:
        data = json.loads(CONTACTS_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    if not isinstance(data, list):
        return []
    result = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name", "")).strip()[:80]
        number = str(entry.get("number", "")).replace(" ", "").strip()
        if name and NUMBER_RE.fullmatch(number):
            result.append({"name": name, "number": number, "favorite": bool(entry.get("favorite", False))})
    return result


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/status")
def status():
    return jsonify({
        "ok": True,
        "ami_configured": all([env("AMI_HOST"), env("AMI_USERNAME"), env("AMI_SECRET"), env("ASTERISK_CHANNEL")]),
        "media_bridge": False,
        "note": "RTP to Kiosk Satellite Intercom bridge is not implemented yet",
    })


@app.get("/api/contacts")
def contacts():
    return jsonify(load_contacts())


@app.post("/api/call")
def call():
    body = request.get_json(silent=True) or {}
    number = str(body.get("number", "")).replace(" ", "").strip()
    if not NUMBER_RE.fullmatch(number):
        return jsonify({"ok": False, "error": "Ungültige Telefonnummer"}), 400
    try:
        result = originate(number)
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 502
    return jsonify({"ok": True, **result})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(env("PORT", "8088")), debug=False)
