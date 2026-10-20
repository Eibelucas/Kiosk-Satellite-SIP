"""The test runtime is off until explicitly activated in the lab UI."""
from pbx import Pbx

class WorkspacePbx(Pbx):
    def restart(self):
        if not getattr(self.settings,"workspace_enabled",False):
            self.stop()
            return
        return super().restart()
