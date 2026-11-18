param([switch]$ValidateOnly)

$ErrorActionPreference = 'Stop'
$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$configPath = Join-Path $PSScriptRoot 'schedule.json'
$config = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
$promptPath = Join-Path $PSScriptRoot 'project-worker-prompt.md'
$schemaPath = Join-Path $PSScriptRoot 'worker-result.schema.json'
$statusPath = Join-Path $PSScriptRoot 'status.json'
$logsPath = Join-Path $PSScriptRoot 'logs'
$utf8 = [System.Text.UTF8Encoding]::new($false)

foreach ($requiredPath in @($projectRoot, $promptPath, $schemaPath, $config.codex_path)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) { throw "Required path missing: $requiredPath" }
}
$null = Get-Content -LiteralPath $schemaPath -Raw | ConvertFrom-Json
if ($ValidateOnly) {
    Write-Output "Worker configuration validated; no scientific work or model run started. Start: $($config.start_local)"
    exit 0
}

$startAt = [DateTimeOffset]::Parse($config.start_local)
if ([DateTimeOffset]::Now -lt $startAt) {
    throw "Refusing to start project work before scheduled time $startAt"
}
$null = [System.IO.Directory]::CreateDirectory($logsPath)
$lockHandle = $null
$activeProcess = $null
$startedAt = [DateTimeOffset]::Now
$pass = 0

function Write-WorkerStatus([string]$State, [string]$Message, [int]$PassNumber, [object]$ProcessId = $null) {
    $stateData = [ordered]@{
        state = $State
        message = $Message
        updated_at = [DateTimeOffset]::Now.ToString('o')
        started_at = $startedAt.ToString('o')
        scheduled_start = $config.start_local
        pass = $PassNumber
        worker_pid = $ProcessId
        logs = $logsPath
    }
    $temporaryPath = "$statusPath.tmp"
    [System.IO.File]::WriteAllText($temporaryPath, ($stateData | ConvertTo-Json -Depth 6), $utf8)
    Move-Item -LiteralPath $temporaryPath -Destination $statusPath -Force
}

function Quote-NativeArgument([string]$Value) {
    # These arguments are generated from controlled paths/options; prompts use stdin.
    if ($Value.Contains('"') -or $Value.EndsWith('\')) {
        throw 'Unexpected embedded quote or trailing backslash in generated worker argument.'
    }
    return '"' + $Value + '"'
}

function Get-MissingDeliverables {
    $required = @(
        'README.md', 'results/metadata.json', 'results/correlations.csv',
        'results/summary.json', 'results/validation.json', 'reports/final_report.md',
        'reports/final_report.pdf', 'reports/presentation.pptx'
    )
    foreach ($relativePath in $required) {
        $candidate = Join-Path $projectRoot $relativePath
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            Write-Output $relativePath
        } elseif ((Get-Item -LiteralPath $candidate).Length -eq 0) {
            Write-Output "$relativePath (empty)"
        }
    }
    $figuresPath = Join-Path $projectRoot 'figures'
    if (-not (Test-Path -LiteralPath $figuresPath)) {
        Write-Output 'figures/ (missing)'
    } elseif (@(Get-ChildItem -LiteralPath $figuresPath -File -Filter '*.png').Count -lt 4) {
        Write-Output 'figures/ (fewer than four PNG figures)'
    }
    $validationPath = Join-Path $projectRoot 'results/validation.json'
    if (Test-Path -LiteralPath $validationPath) {
        try {
            $validation = Get-Content -LiteralPath $validationPath -Raw | ConvertFrom-Json
            if ($validation.overall_pass -ne $true) { Write-Output 'results/validation.json overall_pass must be true' }
        } catch { Write-Output 'results/validation.json is invalid JSON' }
    }
}

try {
    $lockHandle = [System.IO.File]::Open((Join-Path $PSScriptRoot 'worker.lock'), 'OpenOrCreate', 'ReadWrite', 'None')
    $failureCount = 0
    $continuationNote = ''
    # Normal execution should complete in one invocation. Bounded continuations
    # recover early returns and transient errors without an endless paid loop.
    for ($pass = 1; $pass -le 12; $pass++) {
        $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
        $prefix = Join-Path $logsPath ("pass-{0:D2}-{1}" -f $pass, $stamp)
        $resultPath = "$prefix.result.json"
        $stdoutPath = "$prefix.events.jsonl"
        $stderrPath = "$prefix.stderr.log"
        $prompt = [System.IO.File]::ReadAllText($promptPath)
        if ($continuationNote) { $prompt += "`n`n## Continuation context`n$continuationNote" }
        $arguments = @(
            '-a', 'never', 'exec', '--skip-git-repo-check', '--color', 'never', '--json',
            '-s', 'workspace-write', '-c', 'sandbox_workspace_write.network_access=true',
            '-C', $projectRoot, '--output-schema', $schemaPath,
            '--output-last-message', $resultPath, '-'
        )
        $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
        $startInfo.FileName = $config.codex_path
        $startInfo.Arguments = ($arguments | ForEach-Object { Quote-NativeArgument $_ }) -join ' '
        $startInfo.WorkingDirectory = $projectRoot
        $startInfo.UseShellExecute = $false
        $startInfo.CreateNoWindow = $true
        $startInfo.RedirectStandardInput = $true
        $startInfo.RedirectStandardOutput = $true
        $startInfo.RedirectStandardError = $true
        $stdoutFile = [System.IO.File]::Create($stdoutPath)
        $stderrFile = [System.IO.File]::Create($stderrPath)
        try {
            $activeProcess = [System.Diagnostics.Process]::Start($startInfo)
            $stdoutCopy = $activeProcess.StandardOutput.BaseStream.CopyToAsync($stdoutFile)
            $stderrCopy = $activeProcess.StandardError.BaseStream.CopyToAsync($stderrFile)
            # Windows PowerShell's .NET runtime lacks StandardInputEncoding.
            # Write UTF-8 explicitly to the underlying redirected stream.
            $inputWriter = [System.IO.StreamWriter]::new($activeProcess.StandardInput.BaseStream, $utf8)
            try { $inputWriter.Write($prompt) } finally { $inputWriter.Dispose() }
            Write-WorkerStatus 'running' "Executing end-to-end project worker; events: $stdoutPath" $pass $activeProcess.Id
            while (-not $activeProcess.WaitForExit(30000)) {
                Write-WorkerStatus 'running' "Worker active; progress is recorded in WORK_LOG.md and $stdoutPath" $pass $activeProcess.Id
            }
            $stdoutCopy.GetAwaiter().GetResult()
            $stderrCopy.GetAwaiter().GetResult()
            $workerExitCode = $activeProcess.ExitCode
        } finally {
            $stdoutFile.Dispose()
            $stderrFile.Dispose()
        }
        $activeProcess.Dispose()
        $activeProcess = $null
        if ($workerExitCode -ne 0 -or -not (Test-Path -LiteralPath $resultPath)) {
            $failureCount++
            Write-WorkerStatus 'retrying' "Worker exit code $workerExitCode; failure $failureCount of 3. See $stderrPath" $pass
            if ($failureCount -ge 3) { throw 'Three consecutive execution failures. Inspect worker logs before restarting.' }
            $continuationNote = "A prior invocation failed or returned no structured result. Read WORK_LOG.md and existing artifacts, recover incomplete work, and continue. Previous log: $stderrPath"
            Start-Sleep -Seconds 60
            continue
        }
        $failureCount = 0
        $result = Get-Content -LiteralPath $resultPath -Raw | ConvertFrom-Json
        Copy-Item -LiteralPath $resultPath -Destination (Join-Path $PSScriptRoot 'latest-result.json') -Force
        $missing = @(Get-MissingDeliverables)
        if ($result.status -eq 'complete' -and $result.remaining_work.Count -eq 0 -and $missing.Count -eq 0) {
            Write-WorkerStatus 'complete' $result.summary $pass
            exit 0
        }
        if ($result.status -eq 'blocked' -and $result.needs_user_input) {
            Write-WorkerStatus 'blocked' ($result.summary + ' Remaining: ' + ($result.remaining_work -join '; ')) $pass
            exit 2
        }
        $continuationNote = "Previous worker summary: $($result.summary)`nRemaining work: $($result.remaining_work -join '; ')`nMissing/unverified deliverables: $($missing -join '; ')`nContinue implementation and validation from the existing project checkpoint. Do not repeat completed expensive processing unnecessarily."
        Write-WorkerStatus 'continuing' $continuationNote $pass
    }
    throw 'Continuation limit reached with work still incomplete. Inspect status, latest result, and WORK_LOG.md before resuming.'
} catch {
    Write-WorkerStatus 'failed' $_.Exception.Message $pass
    exit 1
} finally {
    if ($activeProcess -and -not $activeProcess.HasExited) { $activeProcess.Kill() }
    if ($lockHandle) { $lockHandle.Dispose() }
}
