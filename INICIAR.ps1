# Ejecutar desde PowerShell con Node 22.12+ y npm en PATH.
$projectDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath (Join-Path $projectDirectory 'frontend')
if (-not (Test-Path -LiteralPath 'node_modules')) {
    & npm.cmd install
    if ($LASTEXITCODE -ne 0) { throw 'No se pudieron instalar las dependencias.' }
}
Start-Process 'http://localhost:5173'
& npm.cmd run dev
