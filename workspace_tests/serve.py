import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"kiosk_sip"/"app"))
from configuration import Settings
from workspace_server import create_app
from werkzeug.serving import run_simple

class Pbx:
    process=None
    def restart(self): pass
    def stop(self): pass
    def status(self):return {"asterisk_running":False,"lines":[],"devices":[],"media_bridge":False}

directory=tempfile.TemporaryDirectory(prefix="sip-ui-browser-")
app=create_app(Settings(directory.name),Pbx())
def ingress(environ,start):
    environ["kiosk.ingress"]=True
    return app(environ,start)
run_simple("127.0.0.1",5932,ingress,use_reloader=False)
