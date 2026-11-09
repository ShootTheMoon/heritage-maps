# 레벨의 Camera 인스턴스를 옮긴다. game.screenshot 이 이걸 쓰는지 시험용.
param(
    [double] $PX, [double] $PY, [double] $PZ,
    [double] $OX = 0, [double] $OY = 0, [double] $OZ = 0,
    [double] $Fov = -1,
    [string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm"
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"; . "$PSScriptRoot\ovdr_level.ps1"; . "$PSScriptRoot\ovdr_script.ps1"
$t = Read-OvdrText -Path $LevelPath
# Workspace 밑 Camera 노드의 CFrame 을 찾아 위치·회전만 바꾼다
$m = [regex]::Match($t, '"InstanceType":\s*"Camera"[\s\S]{0,3000}?"CFrame":\s*\{\s*"ObjectType":\s*"CFrame",\s*"Position":\s*\{[^}]*\},\s*"Orientation":\s*\{[^}]*\}\s*\}')
if (-not $m.Success) { throw 'Camera 노드의 CFrame 을 못 찾았다' }
$new = '"CFrame": { "ObjectType": "CFrame", "Position": ' + (New-OvdrVector3 $PX $PY $PZ) + ', "Orientation": ' + (New-OvdrVector3 $OX $OY $OZ) + ' }'
$old = $m.Value
$idx = $old.IndexOf('"CFrame"')
$rep = $old.Substring(0, $idx) + $new
$t = $t.Substring(0, $m.Index) + $rep + $t.Substring($m.Index + $m.Length)
if ($Fov -ge 0) {
    $t = [regex]::Replace($t, '("InstanceType":\s*"Camera"[\s\S]{0,3000}?"FieldOfView":\s*)[-0-9.]+', ('${1}' + $Fov), 1)
}
$null = $t | ConvertFrom-Json
Write-OvdrText -Text $t -Path $LevelPath
$r = Invoke-OvdrRpc -Method 'level.apply' -TimeoutSec 120
Write-Host ("카메라 -> ({0}, {1}, {2}) 회전 ({3}, {4}, {5})" -f $PX,$PY,$PZ,$OX,$OY,$OZ) -ForegroundColor Green
