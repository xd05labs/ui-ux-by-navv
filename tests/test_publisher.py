"""Windows integration tests; no real account, repository creation or network push."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
BAT = ROOT / "Publish-Clean.bat"


def ps_string(value):
    return "'" + str(value).replace("'", "''") + "'"


@unittest.skipUnless(os.name == "nt" and shutil.which("powershell.exe") and shutil.which("git"),
                     "Windows PowerShell and Git are required")
class PublisherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="clean-publisher-test-")
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)

    def run_ps(self, body):
        prelude = f"""
$ErrorActionPreference = 'Stop'
$env:CLEAN_PUBLISH_LIBRARY_ONLY = '1'
$raw = [IO.File]::ReadAllText({ps_string(BAT)})
$marker = '# === POWERSHELL PAYLOAD ==='
. ([ScriptBlock]::Create($raw.Substring($raw.LastIndexOf($marker) + $marker.Length)))
$testRoot = {ps_string(self.path)}
$script:Git = (Get-Command git.exe).Source
$script:EmptyHooks = Join-Path $testRoot 'hooks'
$null = [IO.Directory]::CreateDirectory($script:EmptyHooks)
"""
        script = self.path / "scenario.ps1"
        script.write_text(prelude + body, encoding="utf-8-sig")
        result = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)],
                                cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def run_batch(self, project, mode="--dry-run", user_input=None):
        shutil.copy2(BAT, project / BAT.name)
        command = ["cmd.exe", "/d", "/c", BAT.name] + ([mode] if mode else [])
        return subprocess.run(command, cwd=project, input=user_input,
                              capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)

    def test_batch_filters_tracked_ignored_and_runtime_files_without_changing_git(self):
        project = self.path / "project [spaces] & !percent%"
        project.mkdir()
        (project / ".gitignore").write_text(".env\nignored.txt\n", encoding="utf-8")
        (project / ".publishignore").write_text("local-note.txt\n", encoding="utf-8")
        for name in ("README.md", "main.py", ".env.example", "ignored.txt", "local-note.txt", ".env", "app.sqlite3", "debug.log"):
            (project / name).write_text("APP_MODE=example\n", encoding="utf-8")
        for directory in ("node_modules", ".venv", "dist", "obj", "artifacts"):
            (project / directory).mkdir()
            (project / directory / "not-source.txt").write_text("excluded", encoding="utf-8")
        with (project / "huge.dat").open("wb") as stream:
            stream.truncate(25 * 1024 * 1024 + 1)
        subprocess.run(["git", "init", "-q", str(project)], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(project), "add", "-f", ".env"], check=True, capture_output=True)
        before = (project / ".git" / "index").read_bytes()
        result = self.run_batch(project)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads((project / ".clean-publish-report.json").read_text())
        included = {file["path"] for file in report["included"]}
        self.assertTrue({"README.md", "main.py", ".env.example", "Publish-Clean.bat"}.issubset(included))
        self.assertTrue({".env", "ignored.txt", "local-note.txt", "huge.dat", "app.sqlite3", "debug.log"}.isdisjoint(included))
        self.assertFalse(any(name.startswith(("node_modules/", ".venv/", "dist/", "obj/", "artifacts/")) for name in included))
        self.assertEqual(before, (project / ".git" / "index").read_bytes())
        self.assertFalse(report["published"])

    def test_potential_secret_blocks_upload_without_printing_value(self):
        project = self.path / "secret-project"
        project.mkdir()
        token = "ghp_" + "A" * 36
        (project / "main.js").write_text('const accessToken = "' + token + '";', encoding="utf-8")
        result = self.run_batch(project)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(token, result.stdout + result.stderr)
        report = json.loads((project / ".clean-publish-report.json").read_text())
        self.assertFalse(report["published"])
        self.assertIn("GitHub token", [item["kind"] for item in report["secretFindings"]])

    def test_native_argument_escaping_preserves_quotes_backslashes_and_metacharacters(self):
        values = ['space & bang! percent%', 'quote"inside', "C:\\ends with\\"]
        body = "$result = Invoke-Native " + ps_string(sys.executable) + " @('-c', 'import json,sys; print(json.dumps(sys.argv[1:]))', "
        body += ", ".join(ps_string(value) for value in values) + ")\nWrite-Output $result.Output"
        self.assertEqual(json.loads(self.run_ps(body)), values)

    def test_repository_links_are_canonical_and_credentials_or_wrong_hosts_are_rejected(self):
        output = self.run_ps(r"""
$a = ConvertTo-GitHubTarget 'git@github.com:owner/project.git'
$b = ConvertTo-GitHubTarget 'https://github.com/owner/project/'
if ($a.Url -ne $b.Url) { throw 'Canonical URLs differ' }
foreach ($value in @('https://evil.example/owner/project', ('https://user' + ':secret@github.com/owner/project'), 'owner/../escape', 'https://github.com/owner/project?token=x')) {
    $rejected = $false
    try { $null = ConvertTo-GitHubTarget $value } catch { $rejected = $true }
    if (-not $rejected) { throw 'Unsafe repository link accepted' }
}
Write-Output 'links passed'
""")
        self.assertIn("links passed", output)

    def test_double_click_entry_displays_numbered_menu_and_exits_without_setup(self):
        project = self.path / "menu project"
        project.mkdir()
        result = self.run_batch(project, mode=None, user_input="7\n0\n")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[1] Check / download / install required tools", result.stdout)
        self.assertIn("[4] Publish to an existing repository link", result.stdout)
        self.assertIn("Windows may show a UAC prompt", result.stdout)
        self.assertFalse((project / ".clean-publish-report.json").exists())

    def test_menu_dispatches_actions_and_recovers_from_invalid_input_and_action_failure(self):
        output = self.run_ps(r"""
$env:CLEAN_PUBLISH_ROOT = $testRoot
$script:Answers = New-Object 'System.Collections.Generic.Queue[string]'
foreach ($answer in @('9','2','3','4','5','6','7','0')) { $script:Answers.Enqueue($answer) }
$script:Actions = New-Object 'System.Collections.Generic.List[string]'
function Read-Host { param([string]$Prompt); return $script:Answers.Dequeue() }
function Ensure-PublisherTools { param([string[]]$Names); return $true }
function Start-CleanPublish {
    param([string]$Action)
    $script:Actions.Add($Action)
    if ($Action -eq 'create') { throw 'Synthetic action failure; menu must continue' }
    return 0
}
function Connect-PublisherGitHub { $script:Actions.Add('account') }
function Show-PublisherReport { $script:Actions.Add('report') }
function Show-PublisherHelp { $script:Actions.Add('help') }
if ((Start-PublisherMenu) -ne 0) { throw 'Menu did not exit cleanly' }
if (($script:Actions -join ',') -ne 'dry-run,create,existing,account,report,help') { throw 'Menu action dispatch failed' }
Write-Output 'menu passed'
""")
        self.assertIn("Invalid option", output)
        self.assertIn("menu passed", output)

    def test_missing_tools_use_terminal_installer_and_refresh_without_restarting(self):
        output = self.run_ps(r"""
$script:GhInstalled = $false
$script:InstallCalls = 0
$script:RefreshCalls = 0
function Find-PublisherTool {
    param([string]$Name)
    if ($Name -eq 'git.exe') { return 'TEST-GIT' }
    if ($Name -eq 'winget.exe') { return 'TEST-WINGET' }
    if ($Name -eq 'gh.exe' -and $script:GhInstalled) { return 'TEST-GH' }
    return $null
}
function Read-Host { param([string]$Prompt); return '1' }
function Invoke-ConsoleTool {
    param([string]$Program,[string[]]$Arguments)
    if ($Program -ne 'TEST-WINGET' -or $Arguments -notcontains 'GitHub.cli' -or
        $Arguments -contains 'Git.Git' -or $Arguments -notcontains '--exact' -or
        $Arguments -notcontains '--silent' -or $Arguments -notcontains '--accept-package-agreements' -or
        $Arguments -notcontains '--source' -or $Arguments -notcontains 'winget') { throw 'Wrong package or install channel' }
    $script:InstallCalls++
    $script:GhInstalled = $true
    return 0
}
function Update-PublisherPath { $script:RefreshCalls++ }
if (-not (Ensure-PublisherTools)) { throw 'Installation did not finish successfully' }
if ($script:InstallCalls -ne 1 -or $script:RefreshCalls -ne 1) { throw 'Existing tools were installed again, or PATH not refreshed' }
Write-Output 'install flow passed'
""")
        self.assertIn("install flow passed", output)

    def test_cancelled_and_offline_dependency_checks_never_download(self):
        output = self.run_ps(r"""
$script:Prompts = 0
function Find-PublisherTool { param([string]$Name); return $null }
function Read-Host { param([string]$Prompt); $script:Prompts++; return '0' }
function Invoke-ConsoleTool { throw 'Unexpected installer execution' }
function Ensure-PublisherWinGet { throw 'Unexpected WinGet setup' }
if (Ensure-PublisherTools) { throw 'Cancelled installation reported success' }
$failed = $false
try { $null = Ensure-PublisherTools -Offline } catch { $failed = $_.Exception.Message -match 'never downloads' }
if (-not $failed -or $script:Prompts -ne 1) { throw 'Offline mode prompted or failed to reject missing tools' }
Write-Output 'cancel and offline passed'
""")
        self.assertIn("cancel and offline passed", output)

    def test_failed_or_unusable_install_does_not_report_success(self):
        output = self.run_ps(r"""
function Find-PublisherTool {
    param([string]$Name)
    if ($Name -eq 'winget.exe') { return 'TEST-WINGET' }
    return $null
}
function Read-Host { param([string]$Prompt); return '1' }
function Update-PublisherPath {}
foreach ($code in @(1603,0)) {
    $script:InstallExit = $code
    function Invoke-ConsoleTool { param([string]$Program,[string[]]$Arguments); return $script:InstallExit }
    $failed = $false
    try { $null = Ensure-PublisherTools @('gh.exe') }
    catch { $failed = $_.Exception.Message -match 'installation failed|not yet available' }
    if (-not $failed) { throw 'Failed or undiscoverable installation accepted as successful' }
}
Write-Output 'failure handling passed'
""")
        self.assertIn("failure handling passed", output)

    def test_missing_winget_bootstrap_requires_menu_selection_and_then_is_detected(self):
        output = self.run_ps(r"""
$script:Bootstraps = 0
$script:Accept = '0'
function Find-PublisherTool {
    param([string]$Name)
    if ($Name -eq 'winget.exe' -and $script:Bootstraps) { return 'TEST-WINGET' }
    return $null
}
function Read-Host { param([string]$Prompt); return $script:Accept }
function Install-WinGetBootstrap { $script:Bootstraps++ }
function Update-PublisherPath {}
if (Ensure-PublisherWinGet) { throw 'Cancelled bootstrap returned an executable' }
if ($script:Bootstraps) { throw 'Bootstrap ran without menu selection' }
$script:Accept = '1'
if ((Ensure-PublisherWinGet) -ne 'TEST-WINGET' -or $script:Bootstraps -ne 1) { throw 'Approved terminal bootstrap failed' }
Write-Output 'bootstrap flow passed'
""")
        self.assertIn("bootstrap flow passed", output)

    def test_terminal_execution_exposes_output_and_returns_real_exit_status(self):
        body = "$code = Invoke-ConsoleTool " + ps_string(sys.executable)
        body += " @('-c', 'import sys; print(\"terminal progress\"); sys.exit(9)')\n"
        body += "if ($code -ne 9) { throw 'Installer exit status lost' }; Write-Output 'console passed'"
        output = self.run_ps(body)
        self.assertIn("terminal progress", output)
        self.assertIn("console passed", output)

    def test_raw_git_tree_preserves_remote_files_removes_artifacts_and_avoids_filters(self):
        output = self.run_ps(r"""
$bare = Join-Path $testRoot 'remote.git'
$source = Join-Path $testRoot 'source'
$snapshotRoot = Join-Path $testRoot 'snapshot'
$null = [IO.Directory]::CreateDirectory($source)
$null = [IO.Directory]::CreateDirectory($snapshotRoot)
$null = Invoke-Git @('init', '--bare', ('--template=' + $script:EmptyHooks), $bare)
$null = Invoke-Git @(('--git-dir=' + $bare), 'read-tree', '--empty')
foreach ($path in @('remote-only.md', '.env', 'node_modules/ignored.js')) {
    $file = Join-Path $source ($path.Replace('/', '_'))
    [IO.File]::WriteAllText($file, 'Existing content')
    $blob = (Invoke-Git @(('--git-dir=' + $bare), 'hash-object', '-w', '--no-filters', $file)).Output.Trim()
    $null = Invoke-Git @(('--git-dir=' + $bare), 'update-index', '--add', '--cacheinfo', ('100644,' + $blob + ',' + $path))
}
$seedTree = (Invoke-Git @(('--git-dir=' + $bare), 'write-tree')).Output.Trim()
$parent = (Invoke-Git @('-c','user.name=Fixture','-c','user.email=fixture@example.test',('--git-dir=' + $bare),'commit-tree',$seedTree,'-m','Seed')).Output.Trim()
$file = Join-Path $snapshotRoot 'start.sh'
[IO.File]::WriteAllText($file, ('#!/bin/sh' + [char]10 + 'echo ready' + [char]10))
$snapshot = [pscustomobject]@{Root=$snapshotRoot;Included=@([pscustomobject]@{path='start.sh';sha256=(Get-SHA256 $file)})}
$prepared = Prepare-PublishTree $bare $snapshot $parent
$entries = (Invoke-Git @(('--git-dir=' + $bare), 'ls-tree', '-r', $prepared.Tree)).Output
if ($entries -notmatch 'remote-only.md' -or $entries -notmatch '100755 blob .+start.sh') { throw 'Remote-only file or executable mode lost' }
if ($entries -match '\.env|node_modules') { throw 'Excluded remote files retained in new tree' }
if ($prepared.Removed.Count -ne 2) { throw 'Removal report incorrect' }
[IO.File]::WriteAllText($file, 'changed after scan')
$rejected = $false
try { $null = Prepare-PublishTree $bare $snapshot $parent } catch { $rejected = $true }
if (-not $rejected) { throw 'Changed snapshot was accepted' }
Write-Output 'tree passed'
""")
        self.assertIn("tree passed", output)

    def test_full_new_and_existing_publish_flow_uses_local_remote_and_never_source_history(self):
        output = self.run_ps(r"""
$project = Join-Path $testRoot 'project'
$localRemote = Join-Path $testRoot 'local-remote.git'
$null = [IO.Directory]::CreateDirectory($project)
[IO.File]::WriteAllText((Join-Path $project '.private-history.txt'), 'Must not enter exported history')
[IO.File]::WriteAllText((Join-Path $project 'main.py'), 'print("first")')
$null = Invoke-Git @('init', $project)
$null = Invoke-Git @('-C',$project,'add','.')
$null = Invoke-Git @('-C',$project,'-c','user.name=Fixture','-c','user.email=fixture@example.test','commit','-m','Private source history')
$sourceHead = (Invoke-Git @('-C',$project,'rev-parse','HEAD')).Output.Trim()
$sourceIndexHash = Get-SHA256 (Join-Path $project '.git/index')
Remove-Item -LiteralPath (Join-Path $project '.private-history.txt')
$env:CLEAN_PUBLISH_ROOT = $project
$env:CLEAN_PUBLISH_MODE = ''
$script:OriginalNative = (Get-Command Invoke-Native).ScriptBlock
$script:RemoteExists = $false
$script:CreateCalls = 0
$script:PromptAnswers = New-Object 'System.Collections.Generic.Queue[string]'
foreach ($answer in @('example-project','1','1')) { $script:PromptAnswers.Enqueue($answer) }
function Read-Host { param([string]$Prompt); return $script:PromptAnswers.Dequeue() }
function Get-Command {
    param([string]$Name, [object]$ErrorAction)
    if ($Name -eq 'gh.exe') { return [pscustomobject]@{ Source = 'TEST-GH' } }
    return Microsoft.PowerShell.Core\Get-Command $Name -ErrorAction Stop
}
function Invoke-Native([string]$Program,[string[]]$Arguments,[switch]$AllowFailure) {
    if ($Program -eq 'TEST-GH') {
        $joined = $Arguments -join ' '
        $output = ''; $code = 0
        if ($joined -like 'api *') { $output = '{"login":"owner","id":42}' }
        elseif ($joined -like 'repo view*') {
            if (-not $script:RemoteExists) { $code = 1 }
            else { $output = '{"isPrivate":true,"viewerPermission":"ADMIN","defaultBranchRef":{"name":"main"}}' }
        } elseif ($joined -like 'repo create*') {
            if ($Arguments -notcontains '--private') { throw 'New repository was not private by default' }
            $script:CreateCalls++
            $null = & $script:OriginalNative $script:Git @('init','--bare',('--template=' + $script:EmptyHooks),$localRemote)
            $script:RemoteExists = $true
        }
        return [pscustomobject]@{ExitCode=$code;Output=$output;Error=''}
    }
    $rewritten = @($Arguments | ForEach-Object { if ($_ -eq 'https://github.com/owner/example-project.git') { $localRemote } else { $_ } })
    return & $script:OriginalNative $Program $rewritten -AllowFailure:$AllowFailure
}
if ((Start-CleanPublish -Action 'create') -ne 0) { throw 'New publish failed' }
$first = (Invoke-Git @(('--git-dir=' + $localRemote),'rev-parse','refs/heads/main')).Output.Trim()
if ($script:CreateCalls -ne 1) { throw 'Repository creation not called once' }
if ((Invoke-Git @('-C',$project,'rev-parse','HEAD')).Output.Trim() -ne $sourceHead) { throw 'Source history changed' }
if ((Get-SHA256 (Join-Path $project '.git/index')) -ne $sourceIndexHash) { throw 'Source index changed' }
if ((Invoke-Git @(('--git-dir=' + $localRemote),'rev-list','--count','refs/heads/main')).Output.Trim() -ne '1') { throw 'Source history leaked into export' }
[IO.File]::WriteAllText((Join-Path $project 'main.py'), 'print("second")')
foreach ($answer in @('https://github.com/owner/example-project','1')) { $script:PromptAnswers.Enqueue($answer) }
if ((Start-CleanPublish -Action 'existing') -ne 0) { throw 'Existing publish failed' }
$head = (Invoke-Git @(('--git-dir=' + $localRemote),'rev-parse','refs/heads/main')).Output.Trim()
$parent = (Invoke-Git @(('--git-dir=' + $localRemote),'rev-parse',($head+'^'))).Output.Trim()
if ($parent -ne $first -or $script:CreateCalls -ne 1) { throw 'Remote history was overwritten or repository recreated' }
$content = (Invoke-Git @(('--git-dir=' + $localRemote),'show',($head+':main.py'))).Output
if ($content -notmatch 'second') { throw 'Updated source not published' }
$report = [IO.File]::ReadAllText((Join-Path $project '.clean-publish-report.json')) | ConvertFrom-Json
if (-not $report.published) { throw 'Success not recorded' }
[IO.File]::WriteAllText((Join-Path $project 'main.py'), 'print("cancelled")')
foreach ($answer in @('https://github.com/owner/example-project','0')) { $script:PromptAnswers.Enqueue($answer) }
if ((Start-CleanPublish -Action 'existing') -ne 0) { throw 'Cancellation failed' }
if ((Invoke-Git @(('--git-dir=' + $localRemote),'rev-parse','refs/heads/main')).Output.Trim() -ne $head) { throw 'Cancellation still pushed' }
Write-Output 'full flow passed'
""")
        self.assertIn("full flow passed", output)


if __name__ == "__main__":
    unittest.main()
