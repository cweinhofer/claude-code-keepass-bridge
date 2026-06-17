# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json, base64, getpass, sys
from pathlib import Path
import win32crypt
import keepassxc_proxy_client.protocol as proto

PIPE_PATH = r"keepassxc\%s\kpxc_server" % getpass.getuser()

conn = proto.Connection()
print("connecting (handshake)...", flush=True)
conn.connect(path=PIPE_PATH)
print("HANDSHAKE OK - pipe server is responsive", flush=True)

# try test_associate + databasehash (works even when locked on most builds)
BRIDGE_DIR = Path(__file__).resolve().parent
blob = (BRIDGE_DIR / "association.dat").read_bytes()
_, data = win32crypt.CryptUnprotectData(blob, None, None, None, 0)
association = json.loads(data.decode("utf-8"))
conn.load_associate(association["name"], base64.b64decode(association["public_key"]))
try:
    print("test_associate:", conn.test_associate(), flush=True)
except Exception as e:
    print("test_associate error:", e, flush=True)
try:
    print("databasehash:", conn.get_databasehash(), flush=True)
except Exception as e:
    print("databasehash error:", e, flush=True)
