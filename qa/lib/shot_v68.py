"""V68 helper: serves out/ and runs s140 with QA_SHOTS to save the desktop hover frame."""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server as qa_server  # noqa: E402

srv = qa_server.Server()
srv.start()
try:
    suite = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "suites", "s140_lang_hover_v68.py")
    r = subprocess.run([sys.executable, suite, srv.base], env=dict(os.environ))
finally:
    srv.stop()
sys.exit(r.returncode)
