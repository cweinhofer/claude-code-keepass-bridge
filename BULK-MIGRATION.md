# Bulk-migrating existing plaintext credentials into the bridge

If you already have API keys/tokens scattered across `.env` files, config files, or scripts,
this is a one-time workflow for moving a batch of them into KeePass at once, instead of
creating entries one at a time through the GUI.

**Security note before you start:** the discovery step below necessarily exposes plaintext
credential values to whatever Claude Code session does the search — something has to read
the files to find them. Limit the exposure:

- Do this in a **brand-new, disposable session** you plan to delete afterward.
- Don't mix in unrelated work in that same session.
- Delete the intermediate CSV file (Step 2) the moment you've imported it into KeePass — until
  then it's a plaintext credential dump sitting on disk.

## Step 1 — Identify existing plaintext credentials

In the disposable session, ask Claude to search for credentials already on disk, e.g.:

> Search this machine for credentials stored in plaintext — `.env` files, config files,
> scripts with hardcoded API keys/tokens/passwords, etc. For each one found, report what it's
> for, where it's stored, and the current value.

Review the results and decide which should move into the bridge.

## Step 2 — Generate a KeePass-importable file

If your CLAUDE.md has a rule against printing/writing credential values (recommended — see
the README's "Suggested CLAUDE.md language" section), tell Claude to suspend it for this step
only, since the point here is writing values into an importable file.

Prompt template:

> I need you to take the credentials you just identified and put them into a structured data
> file I can import into KeePass. For this session only, you can ignore [your CLAUDE.md's
> credential-handling rule].
>
> Before starting, read the following page to understand the KeePass CSV import format:
> https://keepass.info/help/kb/imp_csv.html
> and read these files to understand the tool that will read these entries — the "Claude Code
> KeePass Bridge":
> - `<bridge-folder>\README.md`
> - `<bridge-folder>\manifest.json` (or `manifest.example.json` if you haven't created a real one yet)
>
> **Create the CSV file.** Use the KeePass CSV format, but populate each field according to
> what the bridge needs (see the README's "Adding a new credential" section for the URL/field
> conventions). For credentials with two related values that belong together (e.g. a username
> + API key, or an SSH user + password), store them in one entry using the Username and
> Password fields. In the Notes field, record the original file path and any other context
> that will help you remember what the credential was for later.
>
> Every entry needs a **bridge name key** (see README) and a `$env:` variable name. If the
> credential already has an env var name where you found it, reuse that and base the bridge
> name key on it. If it doesn't, make a descriptive best guess, but list the guessed
> name/env-var pair in a separate "Names to Confirm" file so I can review them.
>
> Save both files somewhere you'll clean up afterward (e.g. your Desktop).
>
> **Create a manifest.** Once the entries are finalized, write a `manifest.json` (per the
> README's format) to `<bridge-folder>\manifest-candidate.json` — don't overwrite the real
> `manifest.json` yet.

## Step 3 — Import and verify

1. Open KeePass: **File > Import > CSV File**, and select the generated CSV.
2. Check the imported entries against the "Names to Confirm" file and fix any names you don't like.
3. **Delete the CSV file from disk now.** It's done its job — there's no reason for a plaintext
   credential dump to keep existing as a file.
4. Tell Claude to promote the candidate manifest:
   - Delete the old `manifest.json`.
   - Rename `manifest-candidate.json` to `manifest.json`.
5. With KeePass unlocked, run `Get-KeePassCredential -Name <name>` for each new entry to
   trigger the one-time "Allow access" popup — check **"Remember this decision"** each time.
6. Restart your `claude` session and confirm the expected `$env:` variables are present.

## Step 4 — Clean up

- Delete the disposable session's history/transcript now that the migration is done — it
  contains the plaintext values found in Step 1.
- Confirm the CSV and "Names to Confirm" files are gone from disk.
