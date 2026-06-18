# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""One-time setup: register this machine with the running KeePass instance.

Usage: py -3 associate.py [name]

Connects to the KeePassNatMsg pipe and requests a new association. KeePass will show
a "Save and allow access" popup where you confirm/edit the name - whatever you type
there is what gets stored (this script's [name] argument is only the suggested
default). On success, DPAPI-protects the association and saves it as association.dat
in this folder, overwriting any existing one.

If the suggested/chosen name already exists in this KeePass database (common when one
database is shared/synced across several machines), KeePass will ask to overwrite it -
decline, since that would invalidate whichever other machine's association currently
uses that name. Re-run with a different name instead, e.g. one that includes the
hostname (the default already does this).
"""
import sys
import json
import base64
import getpass
import socket
from pathlib import Path

import win32crypt
import keepassxc_proxy_client.protocol as proto

BRIDGE_DIR = Path(__file__).resolve().parent
ASSOCIATION_FILE = BRIDGE_DIR / "association.dat"
PIPE_PATH = r"keepassxc\%s\kpxc_server" % getpass.getuser()


def main():
    suggested = sys.argv[1] if len(sys.argv) > 1 else "Claude Code - %s" % socket.gethostname()

    conn = proto.Connection()
    try:
        conn.connect(path=PIPE_PATH)
    except Exception as e:
        print("Could not reach KeePass - is it running and unlocked? (%s)" % e, file=sys.stderr)
        sys.exit(1)

    print('Handshake OK. Requesting association - check KeePass for a "Save and allow '
          'access" popup.')
    print('Suggested name: "%s" (you can change it in the popup; if it says the name '
          "already exists, decline overwrite and re-run this script with a different "
          "name argument instead)." % suggested)
    conn.associate()
    name, public_key = conn.dump_associate()

    association = {"name": name, "public_key": base64.b64encode(public_key).decode("utf-8")}
    data = json.dumps(association).encode("utf-8")
    blob = win32crypt.CryptProtectData(data, "Claude Code KeePass Bridge", None, None, None, 0)
    ASSOCIATION_FILE.write_bytes(blob)
    print('Association saved as "%s" -> %s' % (name, ASSOCIATION_FILE))


if __name__ == "__main__":
    main()
