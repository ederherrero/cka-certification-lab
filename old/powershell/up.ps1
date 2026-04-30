param()

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$vagrantPath = Join-Path $root 'vagrant'

Push-Location $vagrantPath
try {
    Write-Host "Validando plugins do Vagrant..." -ForegroundColor Cyan
    vagrant plugin list | Out-Null

    Write-Host "Subindo o laboratório Kubernetes..." -ForegroundColor Cyan
    vagrant up
}
finally {
    Pop-Location
}
