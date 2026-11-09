# MapService.ORDER -- 투표 카드에 나오는 맵 목록을 바꾼다.
#
# 맵이 안드로이드에서 깨지면 여기서 빼는 것이 유일한 안전장치다.
# M.MAPS 정의는 건드리지 않으므로 언제든 도로 넣을 수 있다.
#
# ★ Lua 파일만 고치면 반영되지 않는다. .ovdrjm 안 스크립트 노드의 Source 가 정본이라
#   Set-OvdrScriptSource 로 밀어넣고 Publish-OvdrLevel 을 해야 한다.
#
# ★ Publish-OvdrLevel 은 level.apply + level.save.file 까지다. 플랫폼 배포가 아니다.
#   안드로이드 기기에 반영하려면 Studio 에서 따로 퍼블리시해야 한다.
#
#   .\map_order.ps1 -Maps jsn,hws,cdg,krm     # 4맵 전부 투표에
#   .\map_order.ps1 -Maps cdg,krm             # 문제 맵 다시 빼기
param(
    [Parameter(Mandatory)][string[]] $Maps,
    [string] $LuaFile = "$env:USERPROFILE\Desktop\onlyoneshot\Lua\MapService_1.lua",
    [string] $NodeName = 'MapService'
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"
. "$PSScriptRoot\ovdr_script.ps1"

$valid = @('jsn', 'hws', 'cdg', 'krm')
foreach ($m in $Maps) { if ($valid -notcontains $m) { throw ("모르는 맵 id: " + $m + "  (가능: " + ($valid -join ', ') + ")") } }
if ($Maps.Count -lt 1) { throw "맵을 최소 하나는 넣어야 한다" }

$utf8 = New-Object System.Text.UTF8Encoding $false
$src = [IO.File]::ReadAllText($LuaFile, $utf8)

$rx = '(?m)^(M\.ORDER\s*=\s*)\{[^}]*\}'
$m = [regex]::Match($src, $rx)
if (-not $m.Success) { throw "M.ORDER 줄을 못 찾았다" }
$was = $m.Value

$want = 'M.ORDER = { ' + (($Maps | ForEach-Object { '"' + $_ + '"' }) -join ', ') + ' }'
Write-Host ("was  : {0}" -f $was) -ForegroundColor DarkGray
Write-Host ("now  : {0}" -f $want) -ForegroundColor Cyan

# ★ DEFAULT 가 목록에 없으면 부팅 맵과 투표 목록이 어긋난다. 경고만 하고 막지는 않는다.
$dm = [regex]::Match($src, '(?m)^M\.DEFAULT\s*=\s*"([^"]+)"')
if ($dm.Success -and ($Maps -notcontains $dm.Groups[1].Value)) {
    Write-Host ("  ! M.DEFAULT = ""{0}"" 가 목록에 없다. 확인해라." -f $dm.Groups[1].Value) -ForegroundColor Yellow
}

if ($was -eq $want) {
    Write-Host "이미 그 상태다. 그래도 레벨에 다시 민다." -ForegroundColor Yellow
} else {
    $new = [regex]::Replace($src, $rx, $want.Replace('$', '$$'))
    [IO.File]::WriteAllText($LuaFile, $new, $utf8)
    Write-Host "Lua 파일 수정됨" -ForegroundColor Green
}

$null = Backup-OvdrLevel -Tag ("order_" + ($Maps -join '-'))
Set-OvdrScriptSource -Name $NodeName -File $LuaFile
$null = Invoke-OvdrRpc -Method 'game.stop' -TimeoutSec 30
Publish-OvdrLevel
Write-Host "`n※ 안드로이드에 반영하려면 Studio 에서 퍼블리시해야 한다." -ForegroundColor Yellow
