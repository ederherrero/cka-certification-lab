param()

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$vagrantPath = Join-Path $root 'vagrant'

Push-Location $vagrantPath
try {
    vagrant status
}
finally {
    Pop-Location
}
