# 화성 지면을 OVERDARE 네이티브 Part 로 만든다.
#
# ★ 출처 : ovdr_export\hwaseong_v23\collision_parts.json (992셀)
#   이 파일에는 각 셀의 최종 엔진 좌표(pos/ori/size)와 지표중심·법선·잔차가 들어 있다.
#   ΔX/ΔY/ΔZ 가 이미 반영된 값이라 그대로 쓰면 된다.
#
# ★ 왜 12 m 격자를 더 안 쪼개는가
#   잔차가 p50 2.95 cm / max 13.91 cm 다. 12 m 에서 지형이 이미 거의 평면이라
#   더 잘게 쪼개도 형상이 안 좋아진다. 품질은 재질 구역화에서 나와야 한다.
#   경사도 p50 2.40° / max 6.64° 로 MaxSlopeAngle 45° 에 한참 못 미친다.
#
# ★★ Orientation.Y 부호
#   실제로 걸어보고 통과했던 레벨은 ori[1] 의 **부호가 뒤집혀** 있었다
#   (json.ori[1] vs level.OriY 가 최대 0.31° 어긋나고, 부호를 뒤집으면 5e-4 로 일치).
#   regen_batches.py:49 의 `yaw = -rot_z` 와 krm_build.ps1 의 -FlipYaw 가 같은 함정이다.
#   그래서 여기서도 Y 만 뒤집는다. X·Z 는 그대로.
#
# ★ 삽입은 직접 한다. Find-OvdrChildrenInsertPoint 는 "InstanceType":"Model" 뒤
#   4000자 안에서 이름을 찾는데, 비어버린 Hwaseong Collision 이 바로 앞에 있어
#   엉뚱한 컨테이너에 꽂힐 수 있다. 이름을 먼저 앵커로 잡는다.
#
#   .\hws_ground.ps1                    # 미리보기
#   .\hws_ground.ps1 -Apply
#   .\hws_ground.ps1 -Wipe -Apply       # 지면만 지우기
param(
    [string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm",
    [string] $CellJson  = "$env:USERPROFILE\Desktop\blender\ovdr_export\hwaseong_v23\collision_parts.json",
    [string] $ZoneJson  = "$env:USERPROFILE/Desktop/blender/hwaseong_rebuild/hws_zones.json",
    [switch] $Wipe,
    [switch] $Apply
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"
. "$PSScriptRoot\ovdr_script.ps1"

$PREFIX = 'HWS_GND_'
$CONTAINER = 'Hwaseong Place'

function Insert-IntoNamedNode {
    <# 이름으로 노드를 먼저 찾고, 그 노드의 LuaChildren 배열에만 꽂는다. #>
    param([string] $Text, [string] $Name, [string] $Blob)
    $m = [regex]::Match($Text, '"Name":\s*"' + [regex]::Escape($Name) + '"')
    if (-not $m.Success) { throw "노드를 못 찾았다: $Name" }
    $start = $Text.LastIndexOf('{', $m.Index)
    # 이 노드의 끝을 찾아 그 안에서만 LuaChildren 을 찾는다
    $d = 0; $end = -1
    for ($i = $start; $i -lt $Text.Length; $i++) {
        if ($Text[$i] -eq '{') { $d++ }
        elseif ($Text[$i] -eq '}') { $d--; if ($d -eq 0) { $end = $i; break } }
    }
    if ($end -lt 0) { throw "노드 끝을 못 찾았다: $Name" }
    $lc = $Text.IndexOf('"LuaChildren"', $start)
    if ($lc -lt 0 -or $lc -gt $end) { throw "$Name 안에 LuaChildren 이 없다" }
    $br = $Text.IndexOf('[', $lc)
    if ($br -lt 0 -or $br -gt $end) { throw "$Name 의 LuaChildren 배열을 못 찾았다" }
    $at = $br + 1
    $k = $at
    while ($k -lt $Text.Length -and $Text[$k] -match '[\s\r\n]') { $k++ }
    $isEmpty = ($k -lt $Text.Length -and $Text[$k] -eq ']')
    $b = $Blob
    if (-not $isEmpty) { $b += ',' }
    return $Text.Substring(0, $at) + "`r`n" + $b + $Text.Substring($at)
}

$text = Read-OvdrText -Path $LevelPath
$had = ([regex]::Matches($text, '"Name":\s*"' + $PREFIX)).Count
if ($had -gt 0) {
    Write-Host "기존 지면 $had 장을 먼저 지운다" -ForegroundColor Yellow
    $text = Remove-OvdrInstancesByName -Text $text -NamePrefix $PREFIX
}
if ($Wipe) {
    if (-not $Apply) { Write-Host "미리보기: 지면 $had 장 삭제. -Apply 로 반영." -ForegroundColor Yellow; return }
    $null = $text | ConvertFrom-Json
    $null = Backup-OvdrLevel -Path $LevelPath -Tag 'hws_ground_wipe'
    Write-OvdrText -Text $text -Path $LevelPath
    $null = Invoke-OvdrRpc -Method 'game.stop' -TimeoutSec 30
    Publish-OvdrLevel
    return
}

$cells = Get-Content -Raw -Path $CellJson | ConvertFrom-Json
Write-Host ("셀 {0} 개 읽음" -f $cells.Count) -ForegroundColor Cyan

# 구역표를 읽어 재질과 색을 정한다. 없으면 전부 Ground 로 간다.
$zoneOf = @{}
if (Test-Path $ZoneJson) {
    foreach ($z in (Get-Content -Raw -Path $ZoneJson | ConvertFrom-Json)) { $zoneOf[$z.name] = $z.zone }
    Write-Host ("구역표 {0} 항목" -f $zoneOf.Count) -ForegroundColor Cyan
}
# 재질과 기본색. 색은 아래에서 지표 높이로 다시 변조한다.
$MAT = @{
    outer = @('Grass',          92, 108,  70)   # 성 밖 들판
    inner = @('Ground',        112, 100,  80)   # 성 안 다진 흙
    road  = @('Sand',          158, 140, 110)   # 흙길
    path  = @('SoilRockGround',134, 120,  98)   # 샛길
    wall  = @('Rock',          122, 120, 116)   # 성벽 접지부
}

# 지표 높이로 밝기를 흔들어 기복이 읽히게 한다 (같은 재질 안에서의 변화)
$ys = $cells | ForEach-Object { $_.surface_center[1] }
$ymin = ($ys | Measure-Object -Minimum).Minimum
$ymax = ($ys | Measure-Object -Maximum).Maximum
$span = [Math]::Max(1.0, $ymax - $ymin)

$k = Get-OvdrKeyIndex -Text $text
$items = New-Object System.Collections.Generic.List[string]
$tally = @{}
$n = 0
foreach ($c in $cells) {
    $k++
    $nm = $PREFIX + ('{0:D4}' -f $n)
    $z = $zoneOf[$c.name]
    if (-not $z -or -not $MAT.ContainsKey($z)) { $z = 'inner' }
    $tally[$z] = 1 + $(if ($tally.ContainsKey($z)) { $tally[$z] } else { 0 })
    $m = $MAT[$z]
    $t = ($c.surface_center[1] - $ymin) / $span      # 0 = 골, 1 = 마루
    $f = 0.88 + 0.24 * $t                            # 골은 어둡게, 마루는 밝게
    $r = [int][Math]::Min(255, $m[1] * $f)
    $g = [int][Math]::Min(255, $m[2] * $f)
    $b = [int][Math]::Min(255, $m[3] * $f)
    $items.Add((New-OvdrPartJson -Name $nm -ObjectKey $k `
        -PX $c.pos[0] -PY $c.pos[1] -PZ $c.pos[2] `
        -OX $c.ori[0] -OY (-$c.ori[1]) -OZ $c.ori[2] `
        -SX $c.size[0] -SY $c.size[1] -SZ $c.size[2] `
        -Material $m[0] -Transparency 0 -CanCollide $true `
        -R $r -G $g -B $b))
    $n++
}
foreach ($e in ($tally.GetEnumerator() | Sort-Object Value -Descending)) {
    Write-Host ("   {0,-7} {1,4} 장  재질 {2}" -f $e.Key, $e.Value, $MAT[$e.Key][0]) -ForegroundColor DarkGray
}
Write-Host ("Part {0} 장 생성" -f $n) -ForegroundColor Cyan

$blob = ($items -join ",`r`n")
$new = Insert-IntoNamedNode -Text $text -Name $CONTAINER -Blob $blob
$new = Set-OvdrKeyIndex -Text $new -Value $k

$null = $new | ConvertFrom-Json
foreach ($g in @('HWS_Bound_North','HWS_Spawn_Red','HWS_Spawn_Blue','JSN_Sangok',
                 'Changdeokgung Place','KRM_Palace','Lobby')) {
    if ($new -notmatch ('"Name":\s*"' + [regex]::Escape($g) + '"')) { throw "사라지면 안 되는 것: $g" }
}
Write-Host ("텍스트 {0:N0} -> {1:N0} 자   ObjectKey {2} 까지 사용" -f $text.Length, $new.Length, $k) -ForegroundColor Green

if (-not $Apply) { Write-Host "`n미리보기만 했다. 반영하려면 -Apply." -ForegroundColor Yellow; return }
$null = Backup-OvdrLevel -Path $LevelPath -Tag 'hws_ground'
Write-OvdrText -Text $new -Path $LevelPath
$null = Invoke-OvdrRpc -Method 'game.stop' -TimeoutSec 30
Publish-OvdrLevel
