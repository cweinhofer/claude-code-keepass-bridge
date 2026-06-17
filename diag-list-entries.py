# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import base64
import getpass
import sys
from pathlib import Path

import win32crypt
import keepassxc_proxy_client.protocol as proto

BRIDGE_DIR = Path(__file__).resolve().parent
ASSOCIATION_FILE = BRIDGE_DIR / "association.dat"
PIPE_PATH = r"keepassxc\%s\kpxc_server" % getpass.getuser()

blob = ASSOCIATION_FILE.read_bytes()
_, data = win32crypt.CryptUnprotectData(blob, None, None, None, 0)
association = json.loads(data.decode("utf-8"))

conn = proto.Connection()
conn.connect(path=PIPE_PATH)
conn.load_associate(association["name"], base64.b64decode(association["public_key"]))
conn.test_associate()

url = sys.argv[1]
entries = conn.get_logins(url)
print(repr(url), "->", entries)
