# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

$script:BridgeDir = $PSScriptRoot

function Get-KeePassCredential {
    <#
    .SYNOPSIS
    Fetch a credential from the running KeePass instance via KeePassNatMsg.
    Looks up the entry with URL "http://CCKPB-<Name>" and returns the requested field
    (default: password). Returns $null and prints KeePass's own error (e.g. "unlock
    KeePass") if the database is locked or the entry isn't found.

    Used internally by the `claude` wrapper at session launch. For manual/diagnostic
    use only — Claude Code sessions rely solely on launch-time injection, not this
    function directly (see .keepass-bridge\README.md).
    #>
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [string]$Field = "password"
    )

    $value = & py -3 "$script:BridgeDir\get-credential.py" $Name $Field
    if ($LASTEXITCODE -ne 0) {
        return $null
    }
    return $value
}

function claude {
    <#
    .SYNOPSIS
    Wraps the real claude.exe: injects credentials from manifest.json as environment
    variables (pulled from KeePass at launch, never written to disk), then launches
    Claude Code normally. Shadows the claude.exe on PATH.

    If KeePass is locked at launch (the common case), entries that can't be retrieved
    are silently skipped — their $env: variables are simply left unset. Claude will
    prompt mid-session if it needs one of them.
    #>
    $manifestPath = Join-Path $script:BridgeDir "manifest.json"
    if (Test-Path $manifestPath) {
        $manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json
        foreach ($entry in $manifest.credentials) {
            $field = if ($entry.field) { $entry.field } else { "password" }
            $value = Get-KeePassCredential -Name $entry.name -Field $field 2>$null
            if ($null -eq $value) {
                Write-Verbose "Skipping `$env:$($entry.env) - could not retrieve credential '$($entry.name)'"
                continue
            }
            Set-Item -Path "Env:$($entry.env)" -Value $value
        }
    }

    $claudeExe = (Get-Command claude.exe -CommandType Application -All -ErrorAction SilentlyContinue | Select-Object -First 1).Source
    & $claudeExe @args
}

Export-ModuleMember -Function Get-KeePassCredential, claude
