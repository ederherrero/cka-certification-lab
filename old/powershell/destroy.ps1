param(
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$vagrantPath = Join-Path $root 'vagrant'

Push-Location $vagrantPath
try {
    if ($Force) {
        vagrant destroy -f
    }
    else {
        vagrant destroy
    }
}
finally {
    Pop-Location
}
