$ErrorActionPreference = 'Stop'
$root = Split-Path (Split-Path $PSScriptRoot)
$receiptPath = Join-Path $root 'cumulative\receipts\TEX_MUTEX_RECEIPT.json'
$mutexName = 'Global\InterlanguageTeXSlotV1'
$python = if ($env:STACKS_PYTHON) { $env:STACKS_PYTHON } else { 'python' }
$driver = Join-Path $PSScriptRoot 'build_reader.py'
$mutex = [Threading.Mutex]::new($false, $mutexName)
$acquired = $false
$abandoned = $false
$started = [DateTime]::UtcNow
$windowsAudit = @()
$wslAudit = @()
$pythonExit = $null
$driverPid = $null
$caught = $null
try {
    try {
        $acquired = $mutex.WaitOne([TimeSpan]::FromSeconds(30))
    } catch [Threading.AbandonedMutexException] {
        $acquired = $true
        $abandoned = $true
    }
    if (-not $acquired) {
        throw 'Global TeX mutex acquisition timed out; no TeX process launched'
    }

    $windowsAudit = @(Get-Process -Name xelatex,bibtex,latexmk,pdflatex,lualatex -ErrorAction SilentlyContinue |
        Select-Object Id,ProcessName,StartTime)
    if ($windowsAudit.Count -ne 0) {
        throw 'Foreign Windows TeX worker found while mutex held; no process touched and no build launched'
    }

    $wslNames = @(& wsl.exe --list --quiet 2>$null | ForEach-Object { $_.Replace("`0", '').Trim() } | Where-Object { $_ })
    foreach ($wslName in $wslNames) {
        $observed = @(& wsl.exe -d $wslName -- sh -lc 'for p in xelatex bibtex latexmk pdflatex lualatex; do pgrep -a -x "$p" || true; done' 2>$null)
        $wslAudit += [pscustomobject]@{ distribution = $wslName; matching_processes = $observed }
        if ($observed.Count -ne 0) {
            throw "Foreign WSL TeX worker found in $wslName; no process touched and no build launched"
        }
    }

    $process = Start-Process -FilePath $python -ArgumentList @('-B', $driver) -NoNewWindow -Wait -PassThru
    $driverPid = $process.Id
    $pythonExit = $process.ExitCode
    if ($pythonExit -ne 0) {
        throw "Serialized cumulative build driver exited $pythonExit"
    }
} catch {
    $caught = $_.Exception.Message
    throw
} finally {
    $ended = [DateTime]::UtcNow
    $receipt = [ordered]@{
        schema = 'interlanguage.stacks_cjk.global_tex_mutex_receipt/v1'
        record_id = 'STACKS-CJK-KO-CUMULATIVE-R3-TEX-20260905'
        mutex = $mutexName
        acquisition_timeout_seconds = 30
        acquired = $acquired
        abandoned_mutex_recovered = $abandoned
        started_utc = $started.ToString('o')
        ended_utc = $ended.ToString('o')
        windows_prelaunch_audit = $windowsAudit
        wsl_prelaunch_audit = $wslAudit
        foreign_processes_touched = $false
        driver_path = $driver
        driver_pid = $driverPid
        python_exit_code = $pythonExit
        error = $caught
        complete_tex_process_tree_lifetime_and_immediate_checks_covered = ($acquired -and $pythonExit -eq 0)
        result = if ($acquired -and $pythonExit -eq 0) { 'PASS_SERIALIZED_TEX_BUILD' } else { 'FAIL_CLOSED' }
    }
    [IO.File]::WriteAllText($receiptPath, ($receipt | ConvertTo-Json -Depth 8) + "`n", [Text.UTF8Encoding]::new($false))
    if ($acquired) {
        $mutex.ReleaseMutex()
    }
    $mutex.Dispose()
}
