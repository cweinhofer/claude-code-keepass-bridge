# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Fetch a credential value from the running KeePass instance via KeePassNatMsg.

Usage: py -3 get-secret.py <name> [field]

Looks up a KeePass entry with URL "http://CCKPB-<name>" and prints the requested
field (default: password) to stdout. Exits non-zero with a message on stderr
if KeePass is locked, not running, or the entry isn't found.
"""
import sys
import json
import base64
import getpass
from pathlib import Path

import win32crypt
import keepassxc_proxy_client.protocol as proto

BRIDGE_DIR = Path(__file__).resolve().parent
ASSOCIATION_FILE = BRIDGE_DIR / "association.dat"
PIPE_PATH = r"keepassxc\%s\kpxc_server" % getpass.getuser()


def fail(message):
    print(message, file=sys.stderr)
    sys.exit(1)


def main():
    if len(sys.argv) < 2:
        fail("Usage: get-secret.py <name> [field]")

    name = sys.argv[1]
    field = sys.argv[2] if len(sys.argv) > 2 else "password"

    if not ASSOCIATION_FILE.exists():
        fail("No KeePassNatMsg association found at %s" % ASSOCIATION_FILE)

    blob = ASSOCIATION_FILE.read_bytes()
    try:
        _, data = win32crypt.CryptUnprotectData(blob, None, None, None, 0)
    except Exception as e:
        fail("Failed to decrypt association.dat (DPAPI): %s" % e)

    association = json.loads(data.decode("utf-8"))

    try:
        conn = proto.Connection()
        conn.connect(path=PIPE_PATH)
        conn.load_associate(association["name"], base64.b64decode(association["public_key"]))
        conn.test_associate()
    except Exception:
        fail("Could not reach KeePass / association invalid. Unlock KeePass and try again.")

    try:
        entries = conn.get_logins("http://CCKPB-%s" % name)
    except Exception:
        fail("KeePass is locked. Unlock it and try again.")

    if not entries:
        fail('No KeePass entry found with URL "http://CCKPB-%s"' % name)

    entry = entries[0]
    if field in entry:
        value = entry[field]
    else:
        value = None
        for sf in entry.get("stringFields", []):
            if field in sf:
                value = sf[field]
                break
        if value is None:
            fail('Field "%s" not found on entry "http://CCKPB-%s"' % (field, name))

    print(value)


if __name__ == "__main__":
    main()
