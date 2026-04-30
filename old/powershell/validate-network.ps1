param()

$root = Split-Path -Parent $PSScriptRoot
$configPath = Join-Path $root 'config\cluster.yaml'

if (-not (Test-Path $configPath)) {
    throw "Arquivo de configuração não encontrado: $configPath"
}

Write-Host "Interfaces de rede disponíveis no host:" -ForegroundColor Cyan
Get-NetAdapter | Sort-Object Status, Name | Format-Table -Auto Name, InterfaceDescription, Status, LinkSpeed, MacAddress

Write-Host "`nAbra config\cluster.yaml e ajuste o campo network.bridge_interface com o nome exato da interface desejada." -ForegroundColor Yellow
