"""[MADE-UP DATA WALK, NOT A RESULT] Run one tool, unchanged, with every way out of the laptop closed.

Usage: python -B guard_run.py <path of the tool> [the tool's own arguments ...]

Before the tool starts, this script
  1. puts a made-up text in the place of the service keys of this one process (the real keys are
     never read, printed or sent; a tool run here can not use them);
  2. puts walk_stub.urlopen in the place of urllib.request.urlopen (made-up replies);
  3. makes every socket connection fail, as a second lock.
Then it runs the tool file as it is, as the main program, with the tool's own arguments.
It changes no file of the tool. The tool sees its own path, so it works in the scratch project copy.
"""
import os
import runpy
import socket
import sys
import urllib.request
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import walk_stub  # noqa: E402

for name in ('GEMINI_API_KEY', 'DEEPSEEK_API_KEY', 'ANTHROPIC_API_KEY', 'OPENAI_API_KEY', 'GOOGLE_API_KEY'):
    os.environ[name] = walk_stub.MADE_UP_KEY
if os.environ.get('WALK_NO_KEYS') == '1':
    for name in ('GEMINI_API_KEY', 'DEEPSEEK_API_KEY'):
        os.environ[name] = ''


def blocked(*args, **kwargs):
    raise OSError('NETWORK_BLOCKED_BY_THE_WALK: a tool tried to open a connection. Nothing was sent.')


socket.socket.connect = blocked
socket.socket.connect_ex = blocked
socket.create_connection = blocked
urllib.request.urlopen = walk_stub.urlopen
(HERE / 'logs').mkdir(exist_ok=True)

tool = Path(sys.argv[1]).resolve()
if HERE not in tool.parents:
    raise SystemExit('guard_run.py runs only a tool copy under %s' % HERE)
sys.argv = [str(tool)] + sys.argv[2:]
sys.path.insert(0, str(tool.parent))
runpy.run_path(str(tool), run_name='__main__')
