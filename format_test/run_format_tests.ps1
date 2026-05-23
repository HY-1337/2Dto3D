$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Inputs = Join-Path $PSScriptRoot "inputs"
$Results = Join-Path $PSScriptRoot "results"
$BackendDir = Join-Path $Root "backend"
$Port = 8010

New-Item -ItemType Directory -Force -Path $Results | Out-Null

$env:TRIPOSR_PYTHON = "C:\Users\Lenovo\scoop\apps\python\current\python.exe"
$env:TRIPOSR_MC_RESOLUTION = "96"
$env:GENERATOR_MODE = "placeholder"

$server = Start-Process `
  -FilePath "python" `
  -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$Port" `
  -WorkingDirectory $BackendDir `
  -PassThru `
  -WindowStyle Hidden

try {
  Start-Sleep -Seconds 4
  Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/system/check" -Method Get | Out-Null

  $summary = @()
  $files = Get-ChildItem $Inputs | Where-Object { $_.Extension -in ".webp", ".jpg", ".jpeg", ".png", ".svg", ".pdf" } | Sort-Object Extension

  foreach ($file in $files) {
    $format = $file.Extension.TrimStart(".").ToLowerInvariant()
    Write-Host "Testing .$format -> OBJ/3MF ..."
    $resultDir = Join-Path $Results $format
    New-Item -ItemType Directory -Force -Path $resultDir | Out-Null

    Copy-Item -LiteralPath $file.FullName -Destination (Join-Path $resultDir $file.Name) -Force

    $jobRaw = & curl.exe -s -X POST "http://127.0.0.1:$Port/api/jobs" `
      -F "file=@$($file.FullName)" `
      -F "profile=print" `
      -F "backend=local" `
      -F "pdf_page=1"
    $job = $jobRaw | ConvertFrom-Json

    $state = $null
    for ($i = 0; $i -lt 180; $i++) {
      Start-Sleep -Seconds 2
      $state = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/jobs/$($job.job_id)" -Method Get
      Write-Host "  $($state.status) $($state.progress)"
      if ($state.status -eq "done" -or $state.status -eq "failed") {
        break
      }
    }

    $jobDir = Join-Path $Root "data\jobs\$($job.job_id)"
    if (Test-Path $jobDir) {
      Copy-Item -Path (Join-Path $jobDir "*") -Destination $resultDir -Recurse -Force
    }

    if ($state.status -eq "done") {
      Invoke-WebRequest -Uri "http://127.0.0.1:$Port/api/jobs/$($job.job_id)/download?format=3mf" -OutFile (Join-Path $resultDir "downloaded_output.3mf") -UseBasicParsing
      Invoke-WebRequest -Uri "http://127.0.0.1:$Port/api/jobs/$($job.job_id)/download?format=obj" -OutFile (Join-Path $resultDir "downloaded_model.zip") -UseBasicParsing
    }

    $summary += [pscustomobject]@{
      format = $format
      input = $file.FullName
      job_id = $job.job_id
      status = $state.status
      error = $state.error
      outputs = $state.outputs
      result_dir = $resultDir
    }
  }

  $summary | ConvertTo-Json -Depth 8 | Set-Content -Path (Join-Path $Results "summary.json") -Encoding UTF8
  $summary | Format-Table -AutoSize
}
finally {
  Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue
}
