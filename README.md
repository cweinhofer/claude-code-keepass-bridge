# Claude Code KeePass Bridge

*An independent, unofficial community tool. Not affiliated with, endorsed by, or sponsored by
Anthropic or KeePass. "Claude" is a trademark of Anthropic, PBC, used here only to describe
compatibility.*

Lets Claude Code read service API keys/tokens from your running, unlocked KeePass 2
instance (via the KeePassNatMsg plugin) — without ever writing secret values to disk.
Lock state (for example KeePassWinHello semi-lock vs full lock) is honored automatically.

This is a personal tool shared as-is. It works for my setup, but it's Windows/PowerShell/
KeePass 2-specific and hasn't been tested beyond that. No guarantees, but I wanted it available
in case it's useful to others.

## Prerequisites

- Windows, with PowerShell (`$PROFILE` loaded in your shell)
- [KeePass 2](https://keepass.info/) with the [KeePassNatMsg](https://github.com/smorks/keepassnatmsg) plugin
- Python 3 (`py -3` on PATH) with `keepassxc-proxy-client` and `pywin32` installed:
  ```powershell
  py -3 -m pip install keepassxc-proxy-client pywin32
  ```
- [Claude Code](https://claude.com/claude-code)

## Automatic injection at every `claude` launch

`Credentials.psm1` defines a `claude` function that **shadows** the real `claude.exe`:
it pulls every entry listed in `manifest.json` from KeePass, sets the corresponding
`$env:` variables, then runs the real executable. Since it's loaded from `$PROFILE`,
this happens automatically — just run `claude` as usual.

This is the primary mechanism for accessing credentials. — there's no mid-session fetch path. If KeePass is locked
at launch (the common case — KeePassWinHello semi-locks the database after X min idle), `claude` still
launches normally and prints nothing; entries that couldn't be retrieved simply have no
`$env:` variable set for that session. See "Using credentials" below for what happens
when Claude needs one of those.

Shared via `$PROFILE`, so it works identically for the main `.claude` and the
`.claude-cascade` Claude Code instances.

## Adding a new credential

### Add a new credential to KeePass

1. In KeePass (primary database), create an entry. Any group is fine — no special
   location is required.
2. Set **Title** to whatever's descriptive (e.g. "OpenAI API Key").
3. Set the **URL** field to exactly `http://CCKPB-<name>` — this is the only thing
   the bridge matches on. `<name>` should use only letters, digits, and hyphens
   (e.g. `openai-api-key`, `github-my-project`) — these are confirmed to work. Some
   other URL-allowed punctuation may work, but many are known to cause the parser to
   misbehave, and others simply haven't been extensively tested against
   KeePassNatMsg's host-parsing quirks, so there's no guarantee they're safe.
   `get-credential.py` auto-prepends the `CCKPB-` tag when it looks up entries, so the
   manifest and `Get-KeePassCredential -Name` calls use the plain `<name>` — only the
   KeePass URL field itself needs the prefix.

   > **Why `http://` and not a custom scheme?** KeePassNatMsg matches `get-logins`
   > requests by the *host* parsed from the entry's URL. The .NET URI parser in this
   > KeePass build only extracts a host from a recognized scheme (`http`/`https`/…) —
   > a custom scheme like `claude://` parses to an empty host, so the entry never
   > matches and lookups silently return "no entry found." `http://<name>` parses
   > cleanly to host `<name>`. The URL is never opened; it's only a match key.
   >
   > **Why the `CCKPB-` prefix?** It's a visual marker (all-caps, distinct from any
   > real hostname) so these bridge-only entries are obviously not real URLs at a
   > glance in the KeePass UI. It lives only in the URL field — Titles can stay
   > fully descriptive, and manifest/env names never include it.
4. Put the credential value in the **Password** field.
5. (Optional) Use **Username** for a second related value, e.g. a client ID alongside a client secret.
6. Save.

### Add a corresponding entry to the manifest file

Add an entry to `manifest.json`:

```json
{
  "credentials": [
    { "name": "openai", "env": "OPENAI_API_KEY", "field": "password" },
    { "name": "github-pat", "env": "GITHUB_TOKEN", "field": "password" }
  ]
}
```

- `name` — matches the `<name>` in the entry's `http://CCKPB-<name>` URL (without the `CCKPB-` prefix).
- `env` — the environment variable name Claude/tools will see.
- `field` — `"password"` (default) or `"login"` for the Username field.

This mapping takes effect on the **next** `claude` launch (see "Using credentials" below
— a running session won't pick up a new entry without a restart).

`manifest.json` isn't committed to the repo (see `.gitignore`) — copy `manifest.example.json`
to `manifest.json` and edit it for your own credentials.

Migrating a batch of existing plaintext credentials (`.env` files, scripts, etc.) all at once?
See `BULK-MIGRATION.md` for a workflow that limits how much plaintext exposure that involves.

### Per-entry first-time approval (every new entry, every machine)

The first time *this* entry is looked up, KeePass shows an "Allow access" popup for the
"Claude Code" connection. **Check "Remember this decision" / "always allow"** — this
whitelists the entry permanently so future lookups are silent. Trigger this once, e.g.:

```powershell
Get-KeePassCredential -Name <name>
```

If you forget to check the box, just run it again and check it then.

## Using credentials

Every credential is available as `$env:<VAR>` for the lifetime of the session — set once
at launch from whatever KeePass had unlocked at that moment. There's a single rule:

- **If `$env:<VAR>` is set**, tell Claude something like:
  
  > "The API key for XYZService is `$env:XYZSERVICE_API_KEY`."
  
  Claude references the variable directly in whatever command needs it — no KeePass
  round-trip, value never printed.

- **If `$env:<VAR>` isn't set** — KeePass was locked at launch, or no KeePass
  entry/manifest mapping exists yet for this credential — Claude will stop and tell you
  what's needed. Add the KeePass entry and/or manifest mapping if missing (see "Adding a
  new credential" above), unlock KeePass, and restart the session (`claude` again). The
  wrapper picks it up on the next launch, and it stays available for the rest of that
  session regardless of KeePass relocking afterward.

## Initial setup on a new system

When setting this up on a new machine, **ask Claude Code to do steps 1-2 and 4-5** — it
ran every command for the original setup, including writing the scripts for step 4.
Your role is approving the UAC prompt (step 1) and the KeePass popup (step 4).

1. *(Claude Code)* Install the KeePassNatMsg plugin: download the latest `KeePassNatMsg.plgx`
   release from https://github.com/smorks/keepassnatmsg and copy it to
   `C:\Program Files\KeePass Password Safe 2\Plugins\` (requires admin — Claude Code will
   launch an elevated PowerShell and you approve the UAC prompt). Restart KeePass.

2. *(Claude Code)* Install the Python client: `py -3 -m pip install keepassxc-proxy-client`.

3. *(You)* Get the `.keepass-bridge` folder onto the new machine, however `.claude` itself
   gets there (backup restore, sync, git, manual copy). `association.dat` doesn't need to
   be excluded — step 4 overwrites it — but a stale copy will produce a confusing DPAPI
   decryption error if `get-credential.py` runs before step 4 is done, so excluding it is
   tidier.

4. *(Claude Code, with your approval)* Perform a fresh one-time association: connect to
   the NatMsg pipe (`keepassxc\<username>\kpxc_server`), call `associate()` — **you'll
   get a KeePass popup to approve, name it "Claude Code"** — then DPAPI-protect
   `{"name": ..., "public_key": ...}` with `win32crypt.CryptProtectData` and save as
   `association.dat` in this folder.

5. *(Claude Code)* Add to `$PROFILE`:
   
   ```powershell
   Import-Module "$env:USERPROFILE\.claude\.keepass-bridge\Credentials.psm1" -DisableNameChecking
   ```
   
   ***NB:*** Every existing `http://CCKPB-<name>` entry will need its per-entry first-time approval (see below)
   re-done on the new machine  — the association is new, so KeePass doesn't yet trust it for any entry.

## Troubleshooting

These come from `get-credential.py`/`Get-KeePassCredential`. The `claude` wrapper swallows
them silently at launch (a locked KeePass is the expected normal case) — you'll see them
if you run `Get-KeePassCredential -Name <name>` manually, e.g. for first-time approval.

| Message                                                                        | Meaning                                                                                                  |
| ------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------- |
| `Could not reach KeePass / association invalid. Unlock KeePass and try again.` | KeePass isn't running, or the NatMsg pipe isn't available.                                               |
| `KeePass is locked. Unlock it and try again.`                                  | Database is semi-locked (WinHello) or fully locked — unlock and retry.                                   |
| `No KeePass entry found with URL "http://CCKPB-<name>"`                        | Check the entry's URL field spelling/scheme exactly matches `http://CCKPB-<name>`.                        |
| `Field "<field>" not found on entry "http://CCKPB-<name>"`                     | The requested field doesn't exist on that entry (check spelling, or whether it's a custom string field). |

KeePassNatMsg also pops a Windows toast notification ("receiving credentials for X") on every
successful lookup — separate from the one-time "Allow access" dialog, and not a bug. To turn it
off: **Tools > KeePassNatMsg Options > uncheck "Show a notification when credentials are requested"**.

## Suggested CLAUDE.md language

Add something like this to your global CLAUDE.md so Claude knows the rules of engagement:

```markdown
# Credentials

- All credentials are exposed as `$env:<VAR>` variables, injected at session launch by the
  `claude` wrapper function from your KeePass database via `manifest.json`.
- This is the only acceptable mechanism. Do not work around this (e.g. asking the user to
  paste the value, or skipping the step that needs it). Prompt the user and wait for the
  restart.
- **Never** state credential values (API keys, tokens, passwords, private keys, or other
  secrets) in the discussion, and never write them to project files, memory files, CLAUDE.md
  files, settings files, or any file Claude creates — even temporarily. Reference the env var
  by name in commands and memory entries; never echo/print any values.
- If a task needs a credential that isn't currently available as `$env:<VAR>` — because
  KeePass was locked at session launch (so the var was never set) or because no KeePass
  entry/manifest mapping exists yet — **stop** and tell the user:
  - that they need to unlock KeePass and restart the session (relaunch `claude`)
  - which credential is needed and what it's for
  - if an existing mapping is recorded, state the `$env:<VAR>`
  - if no existing mapping is recorded, ask the user to add a new KeePass entry and manifest
    mapping for it, or provide the `$env:<VAR>` name to use
```

## Claude Code Keepass Bridge files

- `get-credential.py` — Python script that talks to the running KeePass instance.
- `Credentials.psm1` — PowerShell `Get-KeePassCredential` and the `claude` wrapper, imported via `$PROFILE`.
- `manifest.example.json` — template entries to copy as `manifest.json` and edit for your own credentials.
- `manifest.json` *(not committed — see `.gitignore`)* — your entry → env-var mappings for automatic injection (**names only, never credential values**).
- `BULK-MIGRATION.md` — workflow for migrating a batch of existing plaintext credentials at once.
- `diag-handshake.py` / `diag-list-entries.py` — standalone diagnostics for pipe connectivity and URL/host matching.
- `association.dat` *(not committed — see `.gitignore`)* — DPAPI-protected NatMsg association
  key (decrypts only for the Windows user/machine that created it; not portable — redo the
  one-time association on a new machine instead).

## Contributing

See `CONTRIBUTING.md`.

## License

[MPL-2.0](LICENSE)
