$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\models\TripoSR

$outputDir = Join-Path $PSScriptRoot "data\triposr_manual_test"
$modelDir = Join-Path $PSScriptRoot "models\TripoSR\pretrained\TripoSR"

python run.py examples\chair.png `
  --output-dir $outputDir `
  --pretrained-model-name-or-path $modelDir `
  --model-save-format obj `
  --mc-resolution 256

