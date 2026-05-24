$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$env:TRIPOSR_PYTHON = "C:\Users\Lenovo\scoop\apps\python\current\python.exe"
$env:BAMBU_STUDIO_EXE = "E:\BambuStudio\Bambu Studio\bambu-studio.exe"

$port = 8000
while ($true) {
  $busy = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
  if (-not $busy) {
    break
  }
  Write-Host "Port $port is busy; trying $($port + 1) ..."
  $port += 1
}

Write-Host ""
Write-Host "2Dto3D server starting at: http://127.0.0.1:$port"
Write-Host "Keep this window open while using the web page."
Write-Host ""

python -m uvicorn app.main:app --host 127.0.0.1 --port $port --app-dir backend
