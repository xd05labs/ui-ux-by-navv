@echo off
setlocal DisableDelayedExpansion
set "CLEAN_PUBLISH_SELF=%~f0"
set "CLEAN_PUBLISH_ROOT=%~dp0"
set "CLEAN_PUBLISH_MODE=%~1"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "$c=[IO.File]::ReadAllText($env:CLEAN_PUBLISH_SELF); $m='# === POWERSHELL PAYLOAD ==='; $i=$c.LastIndexOf($m,[StringComparison]::Ordinal); if($i -lt 0){exit 2}; & ([ScriptBlock]::Create($c.Substring($i+$m.Length)))"
set "CLEAN_PUBLISH_EXIT=%ERRORLEVEL%"
if /I "%CLEAN_PUBLISH_MODE%"=="--dry-run" exit /b %CLEAN_PUBLISH_EXIT%
if /I "%CLEAN_PUBLISH_MODE%"=="--help" exit /b %CLEAN_PUBLISH_EXIT%
if "%CLEAN_PUBLISH_MODE%"=="" exit /b %CLEAN_PUBLISH_EXIT%
if "%CLEAN_PUBLISH_NO_PAUSE%"=="1" exit /b %CLEAN_PUBLISH_EXIT%
echo.
pause
exit /b %CLEAN_PUBLISH_EXIT%
# === POWERSHELL PAYLOAD ===
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Quote-NativeArgument([string]$Value) {
    # Windows CommandLineToArgvW escaping; never evaluate a user-supplied command.
    $escaped = [regex]::Replace($Value, '(\\*)"', '$1$1\"')
    $escaped = [regex]::Replace($escaped, '(\\+)$', '$1$1')
    return '"' + $escaped + '"'
}

function Invoke-Native([string]$Program, [string[]]$Arguments, [switch]$AllowFailure) {
    $info = New-Object System.Diagnostics.ProcessStartInfo
    $info.FileName = $Program
    $info.Arguments = (($Arguments | ForEach-Object { Quote-NativeArgument $_ }) -join ' ')
    $info.UseShellExecute = $false
    $info.CreateNoWindow = $true
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true
    $info.StandardOutputEncoding = New-Object System.Text.UTF8Encoding($false)
    $info.StandardErrorEncoding = New-Object System.Text.UTF8Encoding($false)
    # An enclosing Git shell must not redirect our isolated index/object writes.
    foreach ($key in @($info.EnvironmentVariables.Keys)) {
        if ($key -match '^GIT_(DIR|COMMON_DIR|WORK_TREE|INDEX_FILE|OBJECT_DIRECTORY|ALTERNATE_OBJECT_DIRECTORIES|CONFIG_COUNT|CONFIG_PARAMETERS|CONFIG_KEY_.*|CONFIG_VALUE_.*|NAMESPACE|SHALLOW_FILE|REPLACE_REF_BASE)$') {
            $info.EnvironmentVariables.Remove($key)
        }
    }
    $info.EnvironmentVariables['GIT_TERMINAL_PROMPT'] = '0'
    $info.EnvironmentVariables['GH_HOST'] = 'github.com'
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $info
    try {
        $null = $process.Start()
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $stderr = $process.StandardError.ReadToEndAsync()
        $process.WaitForExit()
        $result = [pscustomobject]@{ ExitCode = $process.ExitCode; Output = $stdout.Result; Error = $stderr.Result }
        if ($result.ExitCode -ne 0 -and -not $AllowFailure) {
            throw (([IO.Path]::GetFileName($Program)) + ' failed (exit ' + $result.ExitCode + '). ' + $result.Error.Trim())
        }
        return $result
    } finally { $process.Dispose() }
}

function Get-SHA256([string]$Path) {
    $algorithm = [Security.Cryptography.SHA256]::Create()
    $stream = [IO.File]::OpenRead($Path)
    try { return ([BitConverter]::ToString($algorithm.ComputeHash($stream))).Replace('-', '').ToLowerInvariant() }
    finally { $stream.Dispose(); $algorithm.Dispose() }
}

function Invoke-Git([string[]]$Arguments, [switch]$AllowFailure) {
    $common = @('-c', ('core.hooksPath=' + $script:EmptyHooks), '-c', 'commit.gpgSign=false', '-c', 'core.autocrlf=false')
    return Invoke-Native $script:Git ($common + $Arguments) -AllowFailure:$AllowFailure
}

function Get-SafePath([string]$Root, [string]$Relative) {
    if ([IO.Path]::IsPathRooted($Relative) -or $Relative -match '(^|[\\/])\.\.([\\/]|$)' -or $Relative.Contains(':') -or -not $Relative) {
        throw 'Unsafe relative path in project or repository.'
    }
    $prefix = [IO.Path]::GetFullPath($Root).TrimEnd('\') + '\'
    $full = [IO.Path]::GetFullPath((Join-Path $Root $Relative))
    if (-not $full.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) { throw 'Path escaped the project.' }
    return $full
}

function Test-ReparsePath([string]$Root, [string]$Relative) {
    $current = [IO.Path]::GetFullPath($Root)
    foreach ($part in ($Relative -split '[\\/]')) {
        $current = Join-Path $current $part
        if (((Get-Item -LiteralPath $current -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { return $true }
    }
    return $false
}

function Get-ExclusionReason([string]$Relative) {
    $parts = $Relative.Replace('\', '/').Split('/')
    $directories = @('.git', '.hg', '.svn', 'node_modules', 'bower_components', '.venv', 'venv', 'virtualenv',
        '__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache', '.tox', '.nox', '.next', '.nuxt', '.svelte-kit',
        '.angular', '.cache', '.parcel-cache', '.turbo', '.idea', '.vs', '.vscode', 'build', 'dist', 'out', 'target',
        'bin', 'obj', 'coverage', 'htmlcov', 'logs', 'tmp', 'temp', 'backups', '.gradle', '.terraform', '.serverless', 'artifacts')
    foreach ($part in $parts[0..([Math]::Max(0, $parts.Length - 2))]) {
        if ($parts.Length -gt 1 -and $directories -contains $part) { return 'dependency/cache/build/local-data directory' }
    }
    $name = $parts[-1]
    if ($name -match '^\.env($|\.)' -and $name -notmatch '\.(example|sample|template)$') { return 'environment secrets file' }
    if ($name -match '^(\.git|\.npmrc|\.pypirc|\.netrc|_netrc|\.git-credentials|id_rsa|id_dsa|id_ecdsa|id_ed25519|credentials\.json|service[-_]account.*\.json)$') { return 'credential or repository-private file' }
    if ($name -match '(\.pem|\.key|\.p12|\.pfx|\.keystore|\.jks)$') { return 'private-key/keystore material' }
    if ($name -match '(\.sqlite3?(?:-.*)?|\.db(?:-.*)?|\.log|\.bak|\.tmp|\.py[co]|\.o|\.obj|\.pdb|\.exe|\.dll|\.so|\.dylib|\.class|\.jar|\.war|\.zip|\.7z|\.rar|\.tar|\.gz|\.tsbuildinfo)$') { return 'runtime data or generated binary/archive' }
    if ($name -match '^(\.DS_Store|Thumbs\.db|desktop\.ini|\.coverage.*|\.clean-publish.*|\.appforge\.lock)$') { return 'local operating-system/tool state' }
    return $null
}

function Get-TextForScan([byte[]]$Bytes) {
    if ($Bytes.Length -ge 4 -and $Bytes[0] -eq 255 -and $Bytes[1] -eq 254 -and $Bytes[2] -eq 0 -and $Bytes[3] -eq 0) { return [Text.Encoding]::UTF32.GetString($Bytes) }
    if ($Bytes.Length -ge 2 -and $Bytes[0] -eq 255 -and $Bytes[1] -eq 254) { return [Text.Encoding]::Unicode.GetString($Bytes) }
    if ($Bytes.Length -ge 2 -and $Bytes[0] -eq 254 -and $Bytes[1] -eq 255) { return [Text.Encoding]::BigEndianUnicode.GetString($Bytes) }
    if ($Bytes.Length -gt 0 -and $Bytes[0..([Math]::Min($Bytes.Length - 1, 8191))] -contains 0) { return $null }
    return [Text.Encoding]::UTF8.GetString($Bytes)
}

function Find-SecretKinds([string]$Text) {
    if (-not $Text) { return }
    $patterns = [ordered]@{
        'private key' = '-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----'
        'GitHub token' = '(?:gh[pousr]_[A-Za-z0-9]{30,255}|github_pat_[A-Za-z0-9_]{30,255})'
        'AWS access key' = '(?:AKIA|ASIA)[A-Z0-9]{16}'
        'Google API key' = 'AIza[0-9A-Za-z_-]{35}'
        'live payment key' = '(?:sk|rk)_live_[A-Za-z0-9]{16,}'
        'API secret token' = 'sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{32,}'
        'Slack token' = 'xox[baprs]-[0-9A-Za-z-]{20,}'
        'credential-bearing URL' = '(?i)(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|https?)://[^/\s:@]+:[^/\s@]+@'
    }
    foreach ($entry in $patterns.GetEnumerator()) { if ([regex]::IsMatch($Text, $entry.Value)) { $entry.Key } }
    # Conservative heuristic; known fixture/placeholders and env lookups are not credentials.
    $assignment = '(?im)["'']?(?:password|passwd|secret|client_secret|api[_-]?key|access[_-]?token|auth[_-]?token)["'']?\s*[:=]\s*["'']([^"''\r\n]{20,})["'']'
    foreach ($match in [regex]::Matches($Text, $assignment)) {
        $value = $match.Groups[1].Value
        if ($value -match '(?i)example|dummy|test|placeholder|changeme|change.me|your[_ -]|\$\{|process\.env|os\.environ') { continue }
        $entropy = 0.0
        foreach ($group in ($value.ToCharArray() | Group-Object)) {
            $probability = $group.Count / [double]$value.Length
            $entropy -= $probability * [Math]::Log($probability, 2)
        }
        if ($entropy -ge 3.5) { 'possible embedded credential'; break }
    }
}

function New-CleanSnapshot([string]$SourceRoot, [string]$Scratch) {
    $filterGit = Join-Path $Scratch 'filter.git'
    $snapshot = Join-Path $Scratch 'snapshot'
    $null = New-Item -ItemType Directory -Path $snapshot
    $null = Invoke-Git @('init', '--bare', ('--template=' + $script:EmptyHooks), $filterGit)
    $selection = @(('--git-dir=' + $filterGit), ('--work-tree=' + $SourceRoot), '-c', 'core.bare=false', 'ls-files', '--others', '--exclude-standard', '-z')
    $localExclude = Invoke-Git @('-C', $SourceRoot, 'rev-parse', '--path-format=absolute', '--git-path', 'info/exclude') -AllowFailure
    if ($localExclude.ExitCode -eq 0 -and (Test-Path -LiteralPath $localExclude.Output.Trim() -PathType Leaf)) { $selection += '--exclude-from=' + $localExclude.Output.Trim() }
    $extraIgnore = Join-Path $SourceRoot '.publishignore'
    if (Test-Path -LiteralPath $extraIgnore -PathType Leaf) { $selection += '--exclude-from=' + $extraIgnore }
    $result = Invoke-Git $selection
    $included = New-Object 'System.Collections.Generic.List[object]'
    $excluded = New-Object 'System.Collections.Generic.List[object]'
    $findings = New-Object 'System.Collections.Generic.List[object]'
    foreach ($relative in ($result.Output.Split([char]0) | Where-Object { $_ } | Sort-Object)) {
        $reason = Get-ExclusionReason $relative
        $source = Get-SafePath $SourceRoot $relative
        if (-not $reason -and (Test-ReparsePath $SourceRoot $relative)) { $reason = 'symlink/junction/reparse point' }
        if (-not $reason -and -not (Test-Path -LiteralPath $source -PathType Leaf)) { $reason = 'nested repository or non-file' }
        if (-not $reason -and (Get-Item -LiteralPath $source -Force).Length -gt 25MB) { $reason = 'larger than 25 MiB; review Git LFS separately' }
        if ($reason) { $excluded.Add([pscustomobject]@{ path = $relative; reason = $reason }); continue }
        $bytes = [IO.File]::ReadAllBytes($source)
        if ($bytes.Length -gt 25MB) { throw 'A source file grew above the size limit during snapshotting.' }
        $text = Get-TextForScan $bytes
        foreach ($kind in @(Find-SecretKinds $text)) { $findings.Add([pscustomobject]@{ path = $relative; kind = $kind }) }
        $destination = Get-SafePath $snapshot $relative
        $null = [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($destination))
        [IO.File]::WriteAllBytes($destination, $bytes)
        $hash = Get-SHA256 $destination
        $included.Add([pscustomobject]@{ path = $relative; bytes = $bytes.Length; sha256 = $hash })
    }
    return [pscustomobject]@{ Root = $snapshot; Included = @($included.ToArray()); Excluded = @($excluded.ToArray()); Findings = @($findings.ToArray()) }
}

function ConvertTo-GitHubTarget([string]$Value) {
    $value = $Value.Trim().TrimEnd('/')
    if ($value -match '^(?:https://github\.com/|git@github\.com:)?([A-Za-z0-9][A-Za-z0-9-]{0,38})/([A-Za-z0-9_.-]{1,100})$') {
        $owner = $Matches[1]; $name = $Matches[2] -replace '\.git$', ''
        if ($name -in @('.', '..') -or -not $name) { throw 'Invalid GitHub repository name.' }
        return [pscustomobject]@{ Owner = $owner; Name = $name; Slug = "$owner/$name"; Url = "https://github.com/$owner/$name.git" }
    }
    throw 'Use a github.com HTTPS/SSH repository link or OWNER/REPOSITORY. Embedded credentials and other hosts are rejected.'
}

function Prepare-PublishTree([string]$GitDirectory, [object]$Snapshot, [string]$Parent = '') {
    if ($Parent) { $null = Invoke-Git @(('--git-dir=' + $GitDirectory), 'read-tree', ($Parent + '^{tree}')) }
    else { $null = Invoke-Git @(('--git-dir=' + $GitDirectory), 'read-tree', '--empty') }
    $removed = New-Object 'System.Collections.Generic.List[string]'
    $modes = @{}
    $tracked = (Invoke-Git @(('--git-dir=' + $GitDirectory), 'ls-files', '--stage', '-z')).Output
    foreach ($entry in ($tracked.Split([char]0) | Where-Object { $_ })) {
        if ($entry -notmatch '^([0-9]+) [a-f0-9]+ [0-9]\t(.+)$') { throw 'Unexpected remote index entry.' }
        $mode = $Matches[1]; $path = $Matches[2]
        $null = Get-SafePath $Snapshot.Root $path
        if (Get-ExclusionReason $path) {
            $null = Invoke-Git @(('--git-dir=' + $GitDirectory), ('--work-tree=' + $Snapshot.Root), '-c', 'core.bare=false', 'update-index', '--force-remove', '--', $path)
            $removed.Add($path)
        } else { $modes[$path] = $mode }
    }
    foreach ($file in $Snapshot.Included) {
        $path = Get-SafePath $Snapshot.Root $file.path
        if ((Get-SHA256 $path) -ne $file.sha256) { throw 'Snapshot changed after scanning; refusing to publish.' }
        $blob = (Invoke-Git @(('--git-dir=' + $GitDirectory), 'hash-object', '-w', '--no-filters', '--', $path)).Output.Trim()
        $mode = '100644'
        if (($modes.ContainsKey($file.path) -and $modes[$file.path] -eq '100755') -or $file.path.EndsWith('.sh')) { $mode = '100755' }
        $null = Invoke-Git @(('--git-dir=' + $GitDirectory), 'update-index', '--add', '--cacheinfo', ($mode + ',' + $blob + ',' + $file.path))
    }
    $tree = (Invoke-Git @(('--git-dir=' + $GitDirectory), 'write-tree')).Output.Trim()
    return [pscustomobject]@{ Tree = $tree; Removed = @($removed.ToArray()) }
}

function Write-PublishReport([string]$Path, [object]$Report) {
    [IO.File]::WriteAllText($Path, ($Report | ConvertTo-Json -Depth 8), (New-Object Text.UTF8Encoding($false)))
}

function Remove-OwnedScratch([string]$Path) {
    $tempPrefix = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\') + '\'
    $absolute = [IO.Path]::GetFullPath($Path)
    if (-not $absolute.StartsWith($tempPrefix, [StringComparison]::OrdinalIgnoreCase) -or
        [IO.Path]::GetFileName($absolute) -notmatch '^CleanGitHubPublish-[a-f0-9]{32}$') { throw 'Refusing cleanup outside the owned temporary directory.' }
    if (Test-Path -LiteralPath $absolute) {
        $pending = New-Object 'System.Collections.Generic.Stack[string]'
        $pending.Push($absolute)
        while ($pending.Count) {
            $directory = $pending.Pop()
            if (((Get-Item -LiteralPath $directory -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Refusing recursive cleanup of a reparse point.' }
            foreach ($entry in Get-ChildItem -LiteralPath $directory -Force) {
                if (($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Refusing recursive cleanup of a reparse point.' }
                if ($entry.PSIsContainer) { $pending.Push($entry.FullName) }
            }
        }
        Remove-Item -LiteralPath $absolute -Recurse -Force
    }
}

function Read-MenuChoice([string]$Title, [System.Collections.IDictionary]$Options, [string]$Default = '0') {
    while ($true) {
        Write-Host ''
        Write-Host $Title -ForegroundColor Cyan
        foreach ($key in $Options.Keys) { Write-Host ('  [' + $key + '] ' + $Options[$key]) }
        $choice = ([string](Read-Host ('Choose an option (default ' + $Default + ')'))).Trim()
        if (-not $choice) { $choice = $Default }
        if ($Options.Contains($choice)) { return $choice }
        Write-Host 'Invalid option. Select one of the numbers shown.' -ForegroundColor Yellow
    }
}

function Find-PublisherTool([string]$Name) {
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    return $null
}

function Update-PublisherPath {
    $paths = @($env:Path, [Environment]::GetEnvironmentVariable('Path', 'Machine'), [Environment]::GetEnvironmentVariable('Path', 'User'))
    foreach ($base in @($env:ProgramFiles, [Environment]::GetEnvironmentVariable('ProgramFiles(x86)'), (Join-Path $env:LOCALAPPDATA 'Programs'))) {
        if ($base) {
            $paths += Join-Path $base 'Git\cmd'
            $paths += Join-Path $base 'GitHub CLI'
            $paths += Join-Path $base 'GitHub CLI\bin'
        }
    }
    $paths += Join-Path $env:LOCALAPPDATA 'Microsoft\WindowsApps'
    $env:Path = (($paths -join ';').Split(';') | Where-Object { $_ } | Select-Object -Unique) -join ';'
}

function Invoke-ConsoleTool([string]$Program, [string[]]$Arguments) {
    # Inherit terminal streams so download/installer progress remains visible.
    $info = New-Object System.Diagnostics.ProcessStartInfo
    $info.FileName = $Program
    $info.Arguments = (($Arguments | ForEach-Object { Quote-NativeArgument $_ }) -join ' ')
    $info.UseShellExecute = $false
    $info.CreateNoWindow = $false
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $info
    try { $null = $process.Start(); $process.WaitForExit(); return $process.ExitCode }
    finally { $process.Dispose() }
}

function Install-WinGetBootstrap {
    Write-Host 'Downloading Microsoft.WinGet.Client from PowerShell Gallery in this terminal...'
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    $null = Install-PackageProvider -Name NuGet -MinimumVersion 2.8.5.201 -Scope CurrentUser -Force
    $null = Install-Module -Name Microsoft.WinGet.Client -Repository PSGallery -Scope CurrentUser -Force -AllowClobber
    Import-Module Microsoft.WinGet.Client -ErrorAction Stop
    $null = Repair-WinGetPackageManager -Latest
}

function Ensure-PublisherWinGet {
    $winget = Find-PublisherTool 'winget.exe'
    if ($winget) { return $winget }
    $choice = Read-MenuChoice 'WinGet is missing. Download it through the terminal?' ([ordered]@{
        '1' = 'Install/repair WinGet using Microsoft PowerShell Gallery (current user)'
        '0' = 'Cancel and return'
    })
    if ($choice -eq '0') { return $null }
    Install-WinGetBootstrap
    Update-PublisherPath
    $winget = Find-PublisherTool 'winget.exe'
    if (-not $winget) { throw 'WinGet is still unavailable. Read the terminal installer error; this Windows installation may require a restart or administrator assistance.' }
    return $winget
}

function Ensure-PublisherTools([string[]]$Names = @('git.exe', 'gh.exe'), [switch]$Offline) {
    $packages = @{
        'git.exe' = @{ Id = 'Git.Git'; Label = 'Git' }
        'gh.exe' = @{ Id = 'GitHub.cli'; Label = 'GitHub CLI' }
    }
    $missing = @()
    foreach ($name in $Names) {
        if (-not $packages.ContainsKey($name)) { throw 'Unsupported dependency.' }
        $path = Find-PublisherTool $name
        if ($path) { Write-Host ($packages[$name].Label + ': installed') }
        else { $missing += $name; Write-Host ($packages[$name].Label + ': missing') -ForegroundColor Yellow }
    }
    if (-not $missing.Count) { return $true }
    if ($Offline) { throw 'A required tool is missing. Open the BAT menu and select option 1 to download/install it; --dry-run never downloads anything.' }
    $labels = ($missing | ForEach-Object { $packages[$_].Label + ' (' + $packages[$_].Id + ')' }) -join ', '
    Write-Host ('Missing packages: ' + $labels)
    $choice = Read-MenuChoice 'Install missing requirements from the WinGet repository?' ([ordered]@{
        '1' = 'Download and install in this terminal (accept package/source agreements)'
        '0' = 'Cancel and return'
    })
    if ($choice -eq '0') { return $false }
    $winget = Ensure-PublisherWinGet
    if (-not $winget) { return $false }
    foreach ($name in $missing) {
        Write-Host ('Downloading/installing ' + $packages[$name].Label + '...') -ForegroundColor Cyan
        $code = Invoke-ConsoleTool $winget @('install', '--id', $packages[$name].Id, '--exact', '--source', 'winget',
            '--silent', '--accept-package-agreements', '--accept-source-agreements', '--disable-interactivity', '--no-upgrade')
        if ($code -notin @(0, 3010, 1641)) { throw ($packages[$name].Label + ' installation failed (exit ' + $code + '). Nothing will be published.') }
        Update-PublisherPath
        if (-not (Find-PublisherTool $name)) { throw ($packages[$name].Label + ' is not yet available. A restart may be required; installation output is shown above.') }
    }
    return $true
}

function Connect-PublisherGitHub {
    $gh = Find-PublisherTool 'gh.exe'
    if (-not $gh) { throw 'GitHub CLI is missing. Select menu option 1 to install it.' }
    $auth = Invoke-Native $gh @('auth', 'status', '--hostname', 'github.com') -AllowFailure
    if ($auth.ExitCode -ne 0) {
        Write-Host 'GitHub device sign-in starts in the terminal; GitHub may require browser verification.'
        if ((Invoke-ConsoleTool $gh @('auth', 'login', '--hostname', 'github.com', '--git-protocol', 'https', '--web')) -ne 0) { throw 'GitHub sign-in failed.' }
    }
    $account = (Invoke-Native $gh @('api', '--hostname', 'github.com', 'user')).Output | ConvertFrom-Json
    Write-Host ('Authenticated account: ' + $account.login) -ForegroundColor Green
    return [pscustomobject]@{ Program = $gh; Account = $account }
}

function Show-PublisherHelp {
    Write-Host 'Copy this single BAT into a project root and double-click it for the numbered menu.'
    Write-Host 'The menu installs missing Git/GitHub CLI tools through terminal downloads, then returns here.'
    Write-Host 'Choose preview, create a repository, or publish to an existing link. New repositories default to private.'
    Write-Host 'Preview and confirm the final file list. Git ignores and secret checks still apply.'
    Write-Host 'Publish-Clean.bat --dry-run : offline preview only; never installs, authenticates or uploads.'
    Write-Host 'Windows may show a UAC prompt if an installer needs elevated permissions.'
}

function Show-PublisherReport {
    $path = Join-Path $env:CLEAN_PUBLISH_ROOT '.clean-publish-report.json'
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { Write-Host 'No report yet. Select menu option 2 to preview files.'; return }
    $report = [IO.File]::ReadAllText($path) | ConvertFrom-Json
    Write-Host ('Report: ' + $path)
    Write-Host ('Published: ' + $report.published + ' | Selected: ' + @($report.included).Count + ' | Excluded: ' + @($report.excluded).Count)
    foreach ($file in $report.included) { Write-Host ('  + ' + $file.path) }
    foreach ($file in $report.excluded) { Write-Host ('  - ' + $file.path + ' (' + $file.reason + ')') }
    foreach ($finding in $report.secretFindings) { Write-Host ('BLOCKED: ' + $finding.path + ' (' + $finding.kind + ')') -ForegroundColor Red }
}

function Start-CleanPublish([ValidateSet('dry-run', 'create', 'existing')][string]$Action = 'create', [switch]$Offline) {
    $source = [IO.Path]::GetFullPath($env:CLEAN_PUBLISH_ROOT).TrimEnd('\')
    if ($source -match '^[A-Za-z]:$') { throw 'Use a project folder rather than a drive root.' }
    if (-not $source -or -not (Test-Path -LiteralPath $source -PathType Container)) { throw 'Place this BAT inside the project folder first.' }
    if (((Get-Item -LiteralPath $source -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Use the actual project directory, not a junction/symlink.' }
    if (-not (Ensure-PublisherTools @('git.exe') -Offline:$Offline)) { return 0 }
    $script:Git = Find-PublisherTool 'git.exe'
    $scratch = Join-Path ([IO.Path]::GetTempPath()) ('CleanGitHubPublish-' + [Guid]::NewGuid().ToString('N'))
    $null = New-Item -ItemType Directory -Path $scratch
    $script:EmptyHooks = Join-Path $scratch 'empty-hooks'
    $null = New-Item -ItemType Directory -Path $script:EmptyHooks
    $reportPath = Join-Path $source '.clean-publish-report.json'
    try {
        Write-Host ('Preparing a clean snapshot of: ' + $source)
        $snapshot = New-CleanSnapshot $source $scratch
        $report = [ordered]@{ generatedAt = [DateTime]::UtcNow.ToString('o'); source = $source; published = $false;
            included = @($snapshot.Included); excluded = @($snapshot.Excluded); secretFindings = @($snapshot.Findings);
            removedFromRemoteTip = @(); target = $null; visibility = $null;
            notes = @('Git ignores applied before enumeration, including already-tracked local files.', 'Only selected local snapshot content is scanned; existing remote-only files and history are not audited.', 'No scanner guarantees the absence of all secrets. Review every included file.', 'This is a filtered export, not a build or application test.') }
        Write-PublishReport $reportPath $report
        Write-Host ('Selected ' + $snapshot.Included.Count + ' files; excluded ' + $snapshot.Excluded.Count + ' additional paths after Git ignores.')
        Write-Host ('Full file list and hashes: ' + $reportPath)
        foreach ($file in ($snapshot.Included | Select-Object -First 100)) { Write-Host ('  + ' + $file.path) }
        if ($snapshot.Findings.Count) {
            foreach ($finding in $snapshot.Findings) { Write-Host ('BLOCKED: ' + $finding.path + ' (' + $finding.kind + ')') -ForegroundColor Red }
            throw 'Potential credentials detected. Nothing uploaded. Replace secrets with environment lookups and rerun.'
        }
        if (-not $snapshot.Included.Count) { throw 'No usable files selected. Review .gitignore and .publishignore.' }
        if ($Action -eq 'dry-run') { Write-Host 'Dry run complete. No account login, repository creation, commit or push performed.'; return 0 }
        if (-not (Ensure-PublisherTools @('gh.exe'))) { return 0 }
        $connection = Connect-PublisherGitHub
        $gh = $connection.Program; $account = $connection.Account
        if ($Action -eq 'existing') { $target = ConvertTo-GitHubTarget (Read-Host 'Existing GitHub repository link') }
        else {
            $name = Read-Host 'Repository name'
            if ($name -notmatch '^[A-Za-z0-9_.-]{1,100}$' -or $name -in @('.', '..')) { throw 'Use a repository name containing letters, numbers, dot, underscore or hyphen.' }
            $target = ConvertTo-GitHubTarget ($account.login + '/' + $name)
        }
        if ($target.Owner -ine $account.login) { throw 'This publisher targets repositories on the signed-in personal account only. Sign in to the owner account.' }
        $view = Invoke-Native $gh @('repo', 'view', $target.Slug, '--json', 'nameWithOwner,isPrivate,defaultBranchRef,viewerPermission') -AllowFailure
        $create = $view.ExitCode -ne 0
        if ($create -and $Action -eq 'existing') { throw 'Existing repository could not be read. Check the link and your access; no repository created.' }
        $isPrivate = $true; $branch = 'main'; $parent = ''
        if (-not $create) {
            $remote = $view.Output | ConvertFrom-Json
            if ($remote.viewerPermission -notin @('ADMIN', 'MAINTAIN', 'WRITE')) { throw 'The signed-in account lacks write permission.' }
            $isPrivate = $remote.isPrivate
            if ($null -ne $remote.defaultBranchRef) { $branch = $remote.defaultBranchRef.name }
        } else {
            $visibility = Read-MenuChoice 'New repository visibility' ([ordered]@{ '1' = 'Private (recommended)'; '2' = 'Public (source is downloadable/forkable)'; '0' = 'Cancel' }) '1'
            if ($visibility -eq '0') { Write-Host 'Cancelled. Nothing created or pushed.'; return 0 }
            $isPrivate = $visibility -eq '1'
        }
        if (-not $isPrivate) { Write-Host 'PUBLIC: everyone can download the source; GitHub terms permit on-platform forks. A license does not prevent copying.' -ForegroundColor Yellow }
        $gitDirectory = Join-Path $scratch 'publish.git'
        $null = Invoke-Git @('init', '--bare', ('--template=' + $script:EmptyHooks), $gitDirectory)
        $null = Invoke-Git @('check-ref-format', ('refs/heads/' + $branch))
        $authConfig = @('-c', 'credential.helper=', '-c', 'credential.https://github.com.helper=!gh auth git-credential')
        if (-not $create -and $null -ne $remote.defaultBranchRef) {
            $null = Invoke-Git ($authConfig + @(('--git-dir=' + $gitDirectory), 'fetch', '--no-tags', '--depth=1', $target.Url, ('refs/heads/' + $branch)))
            $parent = (Invoke-Git @(('--git-dir=' + $gitDirectory), 'rev-parse', 'FETCH_HEAD')).Output.Trim()
        }
        $prepared = Prepare-PublishTree $gitDirectory $snapshot $parent
        $report.target = $target.Url; $report.visibility = $(if ($isPrivate) { 'private' } else { 'public' })
        $report.removedFromRemoteTip = @($prepared.Removed)
        Write-PublishReport $reportPath $report
        if ($parent -and $prepared.Tree -eq (Invoke-Git @(('--git-dir=' + $gitDirectory), 'rev-parse', ($parent + '^{tree}'))).Output.Trim()) {
            Write-Host 'No changes to publish. Remote-only clean files were preserved.'; return 0
        }
        Write-Host ('Target: ' + $target.Slug + ' | visibility: ' + $report.visibility + ' | branch: ' + $branch)
        foreach ($removed in $prepared.Removed) { Write-Host ('  - remote tip: ' + $removed) }
        $diffArgs = @(('--git-dir=' + $gitDirectory), 'diff', '--cached', '--stat')
        if ($parent) { $diffArgs += $parent }
        Write-Host (Invoke-Git $diffArgs).Output
        Write-Host 'Existing remote-only clean files are preserved. Existing history is retained; historical secrets are not erased.'
        $confirmation = Read-MenuChoice ('Review the report. Target: ' + $target.Slug + ' | ' + $report.visibility) ([ordered]@{
            '1' = ('Confirm: create/commit/push to this ' + $report.visibility + ' repository')
            '0' = 'Cancel; upload nothing'
        })
        if ($confirmation -ne '1') { Write-Host 'Cancelled. Nothing created or pushed.'; return 0 }
        $email = ([string]$account.id) + '+' + $account.login + '@users.noreply.github.com'
        $commitArgs = @('-c', ('user.name=' + $account.login), '-c', ('user.email=' + $email), ('--git-dir=' + $gitDirectory), 'commit-tree', $prepared.Tree, '-m', 'Publish clean project snapshot')
        if ($parent) { $commitArgs += @('-p', $parent) }
        $commit = (Invoke-Git $commitArgs).Output.Trim()
        if ($create) {
            $visibilityFlag = $(if ($isPrivate) { '--private' } else { '--public' })
            $null = Invoke-Native $gh @('repo', 'create', $target.Slug, $visibilityFlag)
        }
        # Normal fast-forward push only: no force, tags, source history or source index.
        $null = Invoke-Git ($authConfig + @(('--git-dir=' + $gitDirectory), 'push', $target.Url, ($commit + ':refs/heads/' + $branch)))
        $report.published = $true; $report['commit'] = $commit
        Write-PublishReport $reportPath $report
        Write-Host ('Published successfully: https://github.com/' + $target.Slug) -ForegroundColor Green
        return 0
    } finally { Remove-OwnedScratch $scratch }
}

function Start-PublisherMenu {
    while ($true) {
        $choice = Read-MenuChoice ('CLEAN GITHUB PUBLISHER | ' + $env:CLEAN_PUBLISH_ROOT) ([ordered]@{
            '1' = 'Check / download / install required tools'
            '2' = 'Preview clean project files (no upload)'
            '3' = 'Create or find a repository and publish'
            '4' = 'Publish to an existing repository link'
            '5' = 'GitHub sign-in / account status'
            '6' = 'View last file-selection report'
            '7' = 'Help'
            '0' = 'Exit'
        })
        try {
            switch ($choice) {
                '0' { return 0 }
                '1' { $null = Ensure-PublisherTools }
                '2' { $null = Start-CleanPublish -Action 'dry-run' }
                '3' { if (Ensure-PublisherTools) { $null = Start-CleanPublish -Action 'create' } }
                '4' { if (Ensure-PublisherTools) { $null = Start-CleanPublish -Action 'existing' } }
                '5' { if (Ensure-PublisherTools @('gh.exe')) { $null = Connect-PublisherGitHub } }
                '6' { Show-PublisherReport }
                '7' { Show-PublisherHelp }
            }
        } catch { Write-Host ('Clean publisher: ' + $_.Exception.Message) -ForegroundColor Red }
    }
}

if ($env:CLEAN_PUBLISH_LIBRARY_ONLY -ne '1') {
    try {
        if ($env:CLEAN_PUBLISH_MODE -eq '--help') { Show-PublisherHelp; exit 0 }
        if ($env:CLEAN_PUBLISH_MODE -eq '--dry-run') { exit (Start-CleanPublish -Action 'dry-run' -Offline) }
        if ($env:CLEAN_PUBLISH_MODE) { throw 'Supported options: --dry-run or --help. Run without arguments for the menu.' }
        exit (Start-PublisherMenu)
    }
    catch { Write-Host ('Clean publisher: ' + $_.Exception.Message) -ForegroundColor Red; exit 1 }
}
