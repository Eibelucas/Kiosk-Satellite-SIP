"""Ingress-only administration for the separate UI Lab."""
from flask import abort, jsonify, render_template, request
from server import create_app as base_app
from lab import LabStore, sample, blank
from providers import PROVIDERS

def create_app(settings,pbx,gateway_port=8092,ingress_port=8099):
    app=base_app(settings,pbx,gateway_port,ingress_port)
    app.config["SESSION_COOKIE_NAME"]="kiosk_sip_ui_lab_session"
    store=LabStore(settings.directory)
    settings.lab_enabled=store.applied["runtime_enabled"]
    app.config["LAB_STORE"]=store
    phone=app.view_functions["index"]
    app.add_url_rule("/phone","lab_phone",phone)
    app.view_functions["index"]=lambda: render_template("lab.html")
    app.view_functions["setup"]=lambda: render_template("lab.html")
    app.view_functions["save_setup"]=lambda: abort(405)

    def error(exc,status=400):
        return jsonify(ok=False,error=str(exc)),status

    @app.get("/api/setup/lab")
    def lab_get():
        with store.lock:
            return jsonify(ok=True,**store.public(),providers=PROVIDERS,gateway_port=gateway_port,
                           ports={"ami":5039,"rtp_start":30200,"rtp_end":30299},
                           status=pbx.status())

    @app.post("/api/setup/lab")
    def lab_save():
        body=request.get_json(silent=True)
        if not isinstance(body,dict) or set(body)!={"draft","revision"}: return error(ValueError("Ungültige Speicheranfrage."))
        try:
            with store.lock:
                store.save(body["draft"],body["revision"])
                return jsonify(ok=True,**store.public())
        except RuntimeError as exc: return error(exc,409)
        except (ValueError,TypeError) as exc: return error(exc)

    @app.post("/api/setup/lab/reset")
    def lab_reset():
        body=request.get_json(silent=True)
        if not isinstance(body,dict) or set(body)!={"revision","sample"} or type(body["sample"]) is not bool: return error(ValueError("Ungültige Zurücksetzen-Anfrage."))
        try:
            with store.lock:
                if body["sample"] and store.applied["runtime_enabled"]: raise RuntimeError("Den Test-Telefonserver vor dem Laden von Beispieldaten ausschalten und anwenden.")
                store.save(sample() if body["sample"] else blank(),body["revision"])
                return jsonify(ok=True,**store.public())
        except RuntimeError as exc: return error(exc,409)
        except (ValueError,TypeError) as exc: return error(exc)

    @app.post("/api/setup/lab/apply")
    def lab_apply():
        body=request.get_json(silent=True)
        if not isinstance(body,dict) or set(body)!={"revision"}: return error(ValueError("Ungültige Aktivierungsanfrage."))
        try:
            with store.lock:
                if body["revision"]!=store.revision: raise RuntimeError("Entwurf wurde geändert. Neu laden und erneut anwenden.")
                if store.value["runtime_enabled"]:
                    compiled=store.compile()
                    if compiled["sip_port"] in {gateway_port,ingress_port} or (compiled["audio_target"]=="kiosk" and compiled["intercom_port"] in {gateway_port,ingress_port}):
                        raise ValueError("SIP-, Rückruf- und Web-Ports müssen getrennt sein.")
                    settings.save(compiled)
                    settings.lab_enabled=True
                    pbx.restart()
                else:
                    settings.lab_enabled=False
                    pbx.stop()
                store.mark_applied()
                return jsonify(ok=True,message="Test-Konfiguration angewendet." if settings.lab_enabled else "Entwurf übernommen. Der Test-Telefonserver bleibt ausgeschaltet.",
                               **store.public(),status=pbx.status())
        except ValueError as exc: return error(exc)
        except RuntimeError as exc: return error(exc,409)
        except OSError: return error(ValueError("Test-Konfiguration konnte nicht angewendet werden. Add-on-Protokoll prüfen."),503)

    return app
