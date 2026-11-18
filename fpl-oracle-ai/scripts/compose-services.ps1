param([ValidateSet('up','ps','stop')][string]$Action='up')
$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent $PSScriptRoot
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot '.env'))) {
    throw 'Create .env from .env.example and set local secrets before starting services.'
}
$composeArgs=@('--project-name','fpl-oracle','--project-directory',$projectRoot,'-f',(Join-Path $projectRoot 'docker-compose.yml'),'--env-file',(Join-Path $projectRoot '.env'))
if (Get-Command docker -ErrorAction SilentlyContinue) {
    if ($Action -eq 'up') { & docker compose @composeArgs up -d --wait postgres redis }
    elseif ($Action -eq 'ps') { & docker compose @composeArgs ps }
    else { & docker compose @composeArgs stop postgres redis }
} else {
    # Systemd services alone do not keep a WSL distribution alive.
    # Retain one hidden, project-owned WSL process while local containers run.
    if ($Action -eq 'up') {
        $stateDirectory=Join-Path $projectRoot 'data'
        New-Item -ItemType Directory -Path $stateDirectory -Force | Out-Null
        $stateFile=Join-Path $stateDirectory 'wsl-keepalive.pid'
        $existingProcess=$null
        if (Test-Path -LiteralPath $stateFile) {
            $existingProcess=Get-Process -Id ([int](Get-Content -LiteralPath $stateFile)) -ErrorAction SilentlyContinue
        }
        if (-not $existingProcess -or $existingProcess.ProcessName -ne 'wsl') {
            $keepAlive=Start-Process -FilePath 'wsl.exe' -ArgumentList '-d','Ubuntu','--','sleep','infinity' -WindowStyle Hidden -PassThru
            $keepAlive.Id | Set-Content -LiteralPath $stateFile
        }
    }
    $linuxRoot=(& wsl -d Ubuntu -- wslpath -a $projectRoot).Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Ubuntu WSL2 and Docker Engine are required.' }
    & wsl -d Ubuntu -u root -- systemctl start docker
    if ($LASTEXITCODE -ne 0) { throw 'Docker Engine did not start inside Ubuntu.' }
    $linuxArgs=@('--project-name','fpl-oracle','--project-directory',$linuxRoot,'-f',"$linuxRoot/docker-compose.yml",'--env-file',"$linuxRoot/.env")
    if ($Action -eq 'up') { & wsl -d Ubuntu -u root -- docker compose @linuxArgs up -d --wait postgres redis }
    elseif ($Action -eq 'ps') { & wsl -d Ubuntu -u root -- docker compose @linuxArgs ps }
    else { & wsl -d Ubuntu -u root -- docker compose @linuxArgs stop postgres redis }
}
exit $LASTEXITCODE
