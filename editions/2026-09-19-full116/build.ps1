param([ValidateRange(1,60)][int]$MutexTimeoutSeconds=60,[ValidateRange(3,6)][int]$MaxPasses=5)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$run=$PSScriptRoot
$src=Join-Path $run 'src'
$out=Join-Path $run 'output'
$job='stacks-ko-kr-116'
$launcher=Join-Path $PSScriptRoot 'CapturedTeXTree20260909.cs'
if(Test-Path -LiteralPath (Join-Path $run 'BUILD_RECEIPT.json')){throw 'Existing attempt preserved; choose an additive run for a repair'}
$a=Get-Content -Raw -LiteralPath (Join-Path $run 'ASSEMBLY.json') | ConvertFrom-Json
function Record([string]$p){$i=Get-Item -LiteralPath $p;[ordered]@{path=$i.FullName;bytes=$i.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash}}
function Save { [IO.File]::WriteAllText((Join-Path $run 'BUILD_RECEIPT.json'),(($receipt|ConvertTo-Json -Depth 15)+"`n"),[Text.UTF8Encoding]::new($false)) }
function Preserve {foreach($r in $a.source_files){$x=Record (Join-Path $src $r.path);if($x.bytes -ne $r.bytes -or $x.sha256 -ne $r.sha256){throw ('Source drift: '+$r.path)}}}
Preserve
Add-Type -Path $launcher
$mutex=[Threading.Mutex]::new($false,'Global\InterlanguageTeXSlotV1')
$held=$false;$tree=$null;$saved=@{}
$receipt=[ordered]@{status='NOT_STARTED';started_utc=[DateTime]::UtcNow.ToString('o');assembly=Record (Join-Path $run 'ASSEMBLY.json');chapter_count=116;source_count=$a.source_files.Count;mutex=[ordered]@{name='Global\InterlanguageTeXSlotV1';acquired=$false;abandoned=$false;released=$false};phases=@();driver=Record $PSCommandPath}
function Execute([string]$name,[string]$exe,[string]$arguments,[string]$cwd){
 $phase=[ordered]@{name=$name;started_utc=[DateTime]::UtcNow.ToString('o');executable=Record $exe;arguments=$arguments}
 $script:tree=[CapturedTeXTree20260909]::new($exe,$arguments,$cwd,(Join-Path $run ($name+'.stdout.log')),(Join-Path $run ($name+'.stderr.log')))
 $phase.pid=$tree.Id;$receipt.status='RUNNING';$receipt.active_phase=$name;$receipt.active_pid=$tree.Id;Save
 Write-Output ('START '+$name+' PID '+$tree.Id)
 $watch=[Diagnostics.Stopwatch]::StartNew()
 try{
  while(-not $tree.WaitForExit(15000)){
   Write-Output ('RUNNING '+$name+' '+[int]$watch.Elapsed.TotalSeconds+'s')
   if($watch.Elapsed.TotalSeconds -gt 1800){throw 'Captured TeX phase exceeded 30-minute bound'}
  }
  $phase.exit_code=$tree.ExitCode
 }finally{$tree.Dispose();$script:tree=$null}
 $phase.finished_utc=[DateTime]::UtcNow.ToString('o');$receipt.phases+=,$phase;Save
 if($phase.exit_code -ne 0){throw ($name+' returned '+$phase.exit_code)}
 Write-Output ('DONE '+$name)
}
try{
 try{$held=$mutex.WaitOne([TimeSpan]::FromSeconds($MutexTimeoutSeconds))}catch [Threading.AbandonedMutexException]{$held=$true;$receipt.mutex.abandoned=$true}
 $receipt.mutex.acquired=$held;Save
 if(-not $held){throw 'Mutex timeout; no TeX launched'}
 New-Item -ItemType Directory -Path $out -ErrorAction Stop | Out-Null
 $envs=@{SOURCE_DATE_EPOCH='1789776000';FORCE_SOURCE_DATE='1';TZ='UTC';TEXINPUTS=($src+';');BIBINPUTS=($src+';')}
 foreach($k in $envs.Keys){$saved[$k]=[Environment]::GetEnvironmentVariable($k,'Process');[Environment]::SetEnvironmentVariable($k,$envs[$k],'Process')}
 $engine=(Get-Command xelatex -CommandType Application).Source;$bib=(Get-Command bibtex -CommandType Application).Source
 $args='-interaction=nonstopmode -halt-on-error -file-line-error -recorder -no-shell-escape -jobname='+$job+' -output-directory="'+$out+'" reader.tex'
 $prior=@{};$stable=$false
 for($n=1;$n -le $MaxPasses;$n++){
  Execute ('pass-'+$n) $engine $args $src
  $log=Get-Content -Raw -LiteralPath (Join-Path $out ($job+'.log'))
  Copy-Item -LiteralPath (Join-Path $out ($job+'.log')) -Destination (Join-Path $run ('pass-'+$n+'.tex.log'))
  if($log -match '(?m)^!|Undefined control sequence|Emergency stop|Missing character:'){throw 'Fatal or missing-glyph TeX diagnostic'}
  Preserve
  if($n -eq 1){Execute 'bibtex' $bib $job $out;continue}
  $current=@{};foreach($ext in @('pdf','aux','out','toc','bbl')){$current[$ext]=(Record (Join-Path $out ($job+'.'+$ext))).sha256}
  $equal=$prior.Count -gt 0;foreach($k in $current.Keys){if($current[$k] -ne $prior[$k]){$equal=$false}}
  $rerun=$log -match 'Rerun to get|Label\(s\) may have changed|Please \(re\)run|There were undefined|Citation .* undefined|Reference .* undefined'
  $receipt.stable_bytes=$equal;$receipt.rerun_or_undefined=$rerun;Save
  if($equal -and -not $rerun){$stable=$true;break}
  $prior=$current
 }
 if(-not $stable){throw 'No exact PDF/auxiliary convergence within bounded passes'}
 $inputs=@{};$outputs=@{}
 foreach($line in Get-Content -LiteralPath (Join-Path $out ($job+'.fls'))){
  if($line.StartsWith('INPUT ')){$kind='input';$p=$line.Substring(6).Trim('"')}elseif($line.StartsWith('OUTPUT ')){$kind='output';$p=$line.Substring(7).Trim('"')}else{continue}
  if(-not [IO.Path]::IsPathRooted($p)){$p=Join-Path $src $p};$p=[IO.Path]::GetFullPath($p)
  if($kind -eq 'output'){if(-not $p.StartsWith($out+'\',[StringComparison]::OrdinalIgnoreCase)){throw ('Output escaped: '+$p)};$outputs[$p]=$true}
  elseif(Test-Path -LiteralPath $p -PathType Leaf){$inputs[$p]=$true}else{throw ('Missing recorder input: '+$p)}
 }
 foreach($r in $a.source_files){if([IO.Path]::GetExtension($r.path) -in @('.tex','.cls')){if(-not $inputs.ContainsKey([IO.Path]::GetFullPath((Join-Path $src $r.path)))){throw ('Unconsumed chapter/support: '+$r.path)}}}
 $receipt.recorder_inputs=@(foreach($p in $inputs.Keys|Sort-Object){Record $p})
 $receipt.recorder_outputs=@($outputs.Keys|Sort-Object)
 $receipt.final_artifacts=@(Get-ChildItem -LiteralPath $out -File | ForEach-Object {Record $_.FullName})
 $receipt.status='CONVERGED_SOURCE_AND_RECORDER_PASS_PDF_QA_PENDING'
 $receipt.log_counts=[ordered]@{overfull_hbox=[regex]::Matches($log,'Overfull \\hbox').Count;overfull_vbox=[regex]::Matches($log,'Overfull \\vbox').Count;missing_characters=0;undefined_references=0}
}catch{$receipt.status='FAILED';$receipt.error=$_.Exception.Message;Write-Output ('FAILED '+$receipt.error)}finally{
 if($null -ne $tree){$tree.Dispose()}
 foreach($k in $saved.Keys){[Environment]::SetEnvironmentVariable($k,$saved[$k],'Process')}
 if($held){$mutex.ReleaseMutex();$receipt.mutex.released=$true};$mutex.Dispose()
 $receipt.finished_utc=[DateTime]::UtcNow.ToString('o');Save
}
Write-Output ('FINAL '+$receipt.status)
if($receipt.status -eq 'FAILED'){exit 1}
