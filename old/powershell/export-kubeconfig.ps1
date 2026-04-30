param()

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$vagrantPath = Join-Path $root 'vagrant'
$outputDir = Join-Path $root 'output\kubeconfig'
$outputFile = Join-Path $outputDir 'config'

New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

Push-Location $vagrantPath
try {
    $content = vagrant ssh cp-1 -c "sudo cat /etc/kubernetes/admin.conf"
    $content | Out-File -FilePath $outputFile -Encoding ascii
    Write-Host "Kubeconfig exportado para: $outputFile" -ForegroundColor Green
}
finally {
    Pop-Location
}
