import hmac
import json
import secrets
import threading
import time
from datetime import timedelta

from flask import Flask, abort, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from configuration import DESTINATION


class IngressOnly:
    """Trust the source socket, never a client-provided ingress/X-Forwarded header."""
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        if environ.get("REMOTE_ADDR") != "172.30.32.2":
            start_response("403 Forbidden", [("Content-Type", "text/plain")])
            return [b"Only Home Assistant Ingress can access this port."]
        environ["kiosk.ingress"] = True
        return self.app(environ, start_response)


class LanOnly:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        environ["kiosk.ingress"] = False
        return self.app(environ, start_response)


def create_app(settings, pbx, gateway_port=8088):
    app = Flask(__name__)
    app.secret_key = settings.session_secret
    app.config.update(MAX_CONTENT_LENGTH=65536, SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_NAME="kiosk_sip_session",
                      SESSION_COOKIE_SAMESITE="Strict", PERMANENT_SESSION_LIFETIME=timedelta(hours=12))
    # The LAN listener is HTTP inside the private network. Set up TLS in a
    # reverse proxy if used beyond that network; never expose it to the WAN.
    attempts = {}
    attempts_lock = threading.Lock()
    save_lock = threading.Lock()
    call_lock = threading.Lock()
    last_call = [0.0]

    def ingress():
        return request.environ.get("kiosk.ingress") is True

    def csrf_token():
        if "csrf" not in session:
            session["csrf"] = secrets.token_urlsafe(32)
        return session["csrf"]

    def auth_revision():
        import hashlib
        value = settings.value["web_username"] + ":" + settings.value["web_password_hash"]
        return hashlib.sha256(value.encode()).hexdigest()

    @app.before_request
    def authorize():
        admin = request.path == "/setup" or request.path.startswith("/api/setup")
        if admin and not ingress():
            abort(403)
        if not ingress():
            if not settings.value["lan_enabled"]:
                abort(403)
            if request.endpoint not in {"login", "static"} and session.get("auth_revision") != auth_revision():
                if request.path.startswith("/api/"):
                    return jsonify(ok=False, error="Bitte an der Telefonseite anmelden."), 401
                return redirect(url_for("login"))
        if request.method in {"POST", "PUT", "DELETE"}:
            # Session token required for HA ingress and LAN, including login.
            token = request.headers.get("X-CSRF-Token") or request.form.get("csrf", "")
            expected = session.get("csrf", "")
            if not expected or not hmac.compare_digest(expected.encode(), token.encode()):
                return jsonify(ok=False, error="Sitzung abgelaufen. Seite neu laden."), 403

    @app.after_request
    def headers(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; form-action 'self'; base-uri 'none'"
        return response

    @app.context_processor
    def template_context():
        return {"csrf": csrf_token(), "is_ingress": ingress()}

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if ingress():
            return redirect("./")
        error = ""
        if request.method == "POST":
            remote = request.remote_addr
            now = time.monotonic()
            with attempts_lock:
                attempts.update({key: [t for t in times if now - t < 300] for key, times in list(attempts.items())})
                for key in [key for key, times in attempts.items() if not times]:
                    del attempts[key]
                if len(attempts.get(remote, [])) >= 8:
                    return render_template("login.html", error="Zu viele Versuche. Bitte fünf Minuten warten."), 429
                # Bound memory as well as per-IP attempts.
                if len(attempts) >= 1024 and remote not in attempts:
                    return render_template("login.html", error="Bitte später erneut anmelden."), 429
                attempts.setdefault(remote, []).append(now)
            user, password = request.form.get("username", ""), request.form.get("password", "")
            if hmac.compare_digest(user.encode(), settings.value["web_username"].encode()) and check_password_hash(settings.value["web_password_hash"], password):
                session.clear()
                session["auth_revision"] = auth_revision()
                session.permanent = True
                with attempts_lock:
                    attempts.pop(remote, None)
                return redirect("./")
            error = "Benutzername oder Passwort stimmt nicht."
        return render_template("login.html", error=error)

    @app.get("/")
    def index():
        if ingress() and not settings.value["phone_password"]:
            return redirect("setup")
        return render_template("phone.html")

    @app.get("/setup")
    def setup():
        return render_template("setup.html")

    @app.get("/api/setup")
    def get_setup():
        return jsonify(config=settings.public(), gateway_port=gateway_port,
                       gateway_url=f"http://{settings.value['listen_address']}:{gateway_port}/",
                       csrf=csrf_token())

    @app.post("/api/setup")
    def save_setup():
        body = request.get_json(silent=True)
        try:
            with save_lock:
                if isinstance(body, dict) and body.get("sip_port") in {gateway_port, 8099}:
                    raise ValueError("SIP-Port und Web-Port müssen unterschiedlich sein.")
                settings.save(body)
                pbx.restart()
            return jsonify(ok=True, message="Gespeichert. Asterisk wurde neu gestartet. LAN-Zugriff bei Bedarf nach einem Add-on-Neustart aktivieren.")
        except ValueError as exc:
            return jsonify(ok=False, error=str(exc)), 400
        except (OSError, RuntimeError):
            return jsonify(ok=False, error="Konfiguration gespeichert, Asterisk konnte nicht neu starten. Add-on-Protokoll prüfen."), 503

    @app.get("/api/status")
    def status():
        return jsonify(ok=True, **pbx.status(), configured=bool(settings.value["phone_password"]),
                       enabled=settings.value["enabled"], lan_enabled=settings.value["lan_enabled"])

    @app.get("/api/contacts")
    def contacts():
        return jsonify(settings.value["contacts"])

    @app.post("/api/call")
    def call():
        body = request.get_json(silent=True)
        number = body.get("number", "") if isinstance(body, dict) else ""
        if not isinstance(number, str) or not DESTINATION.fullmatch(number):
            return jsonify(ok=False, error="Ungültige Telefonnummer."), 400
        state = pbx.status()
        if not settings.value["enabled"] or not state["telekom_registered"]:
            return jsonify(ok=False, error="Telekom ist noch nicht registriert. Einrichtung und Status prüfen."), 409
        if not state["phone_registered"]:
            return jsonify(ok=False, error="SIP-Telefon 100 anmelden. Der Kiosk selbst hat noch keine Audio-Bridge."), 409
        with call_lock:
            now = time.monotonic()
            if now - last_call[0] < 5:
                return jsonify(ok=False, error="Ein Rückruf wurde gerade angefordert. Bitte kurz warten."), 429
            last_call[0] = now
        try:
            return jsonify(ok=True, **pbx.originate(number))
        except (OSError, RuntimeError):
            return jsonify(ok=False, error="Asterisk hat den Rückruf nicht angenommen. Add-on-Protokoll prüfen."), 502

    return app
