# MapService.DEBUG_FORCE 를 바꿔서 부팅 직후 특정 맵으로 강제 스왑시킨다.
#
# 투표에서 빠진 맵(산곡·화성)을 안드로이드 실기에서 확인하려면 이게 유일한 경로다.
# CaptureServer.lua:930 이 부팅 5초 뒤에 swap() 을 부르고 전원을 전장으로 내보낸다.
#
# ★ Lua 파일만 고치면 반영되지 않는다. .ovdrjm 안 스크립트 노드의 Source 가 정본이라
#   Set-OvdrScriptSource 로 밀어넣고 Publish-OvdrLevel 을 해야 한다.
#
# ★ 확인이 끝나면 -Map none 으로 되돌려라 (MapService_1.lua 주석의 지시).
#
#   .\map_force.ps1 -Map hws          # 화성으로 강제
#   .\map_force.ps1 -Map jsn          # 산곡으로 강제
#   .\map_force.ps1 -Map none         # 해제 (투표 정상 동작)
param(
    [Parameter(Mandatory)][ValidateSet('jsn', 'hws', 'cdg', 'krm', 'none')][string] $Map,
    [string] $LuaFile = "$env:USERPROFILE\Desktop\onlyoneshot\Lua\MapService_1.lua",
    [string] $NodeName = 'MapService'
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"
. "$PSScriptRoot\ovdr_script.ps1"

if (-not (Test-Path $LuaFile)) { throw "Lua 파일이 없다: $LuaFile" }

$want = if ($Map -eq 'none') { 'nil' } else { '"' + $Map + '"' }
$utf8 = New-Object System.Text.UTF8Encoding $false
$src = [IO.File]::ReadAllText($LuaFile, $utf8)

$rx = '(?m)^(M\.DEBUG_FORCE\s*=\s*)(.+)$'
$m = [regex]::Match($src, $rx)
if (-not $m.Success) { throw "M.DEBUG_FORCE 줄을 못 찾았다" }
$was = $m.Groups[2].Value.Trim()

Write-Host ("M.DEBUG_FORCE : {0}  ->  {1}" -f $was, $want) -ForegroundColor Cyan
if ($was -eq $want) {
    Write-Host "이미 그 상태다. 그래도 레벨에 다시 민다." -ForegroundColor Yellow
} else {
    $new = [regex]::Replace($src, $rx, ('${1}' + $want))
    [IO.File]::WriteAllText($LuaFile, $new, $utf8)
    Write-Host "Lua 파일 수정됨" -ForegroundColor Green
}

$null = Backup-OvdrLevel -Tag ("force_" + $Map)
Set-OvdrScriptSource -Name $NodeName -File $LuaFile
$null = Invoke-OvdrRpc -Method 'game.stop' -TimeoutSec 30
Publish-OvdrLevel
Write-Host ("`n이제 플레이하면 부팅 5초 뒤 {0} 로 간다." -f $Map) -ForegroundColor Green
