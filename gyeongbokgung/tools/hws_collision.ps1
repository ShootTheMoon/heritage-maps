# 화성 충돌층 -- 기울인 슬래브 992장을 되살린다.
#
# ★ 이 슬래브들이 못생겼던 건 "보이게 만들어서"였다. 각자 자기 최소자승 평면에 맞춰
#   따로 돌아가니 경계마다 턱이 졌다. 그런데 **안 보이는 충돌층으로는 정확히 옳은 물건**이다 --
#   지형을 매끄럽게 따라가고, 이미 걸어서 검증됐다.
#   시각은 위에 얹을 텍스처 MeshPart 가 담당한다.
#
# ★ 출처 : ovdr_export\hwaseong_v23\collision_parts.json (992셀, 최종 엔진 좌표)
#
# ★★ Orientation.Y 부호를 뒤집는다 (json.ori[1] -> -ori[1]). X·Z 는 그대로.
#   실제로 걸어보고 통과했던 예전 레벨이 그 부호였다 (뒤집으면 5e-4 로 일치,
#   안 뒤집으면 0.31도 어긋남). regen_batches.py:49 의 yaw = -rot_z 와
#   krm_build.ps1 의 -FlipYaw 가 같은 함정이다.
#   Part 는 임포트 에셋이 아니므로 "Orientation 0" 규약이 아니다. 180도류 보정 없음.
#
# ★ 명세서 §3-2 step 4 : 처음엔 -Visible 로 불투명·형광색으로 넣고 눈으로 확인한 뒤
#   투명으로 돌린다. "처음부터 투명하게 넣으면 틀려도 안 보인다."
#
#   .\hws_collision.ps1 -Visible          # 미리보기 (불투명 형광)
#   .\hws_collision.ps1 -Visible -Apply
#   .\hws_collision.ps1 -Apply            # 확인 끝난 뒤 투명으로
param(
    [string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm",
    [string] $CellJson  = "$env:USERPROFILE\Desktop\blender\ovdr_export\hwaseong_v23\collision_parts.json",
    [switch] $Visible,
    [switch] $Apply
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"
. "$PSScriptRoot\ovdr_script.ps1"

$CONTAINER = 'Hwaseong Place'

function Insert-IntoNamedNode {
    param([string] $Text, [string] $Name, [string] $Blob)
    $m = [regex]::Match($Text, '"Name":\s*"' + [regex]::Escape($Name) + '"')
    if (-not $m.Success) { throw "노드를 못 찾았다: $Name" }
    $start = $Text.LastIndexOf('{', $m.Index)
    $d = 0; $end = -1
    for ($i = $start; $i -lt $Text.Length; $i++) {
        if ($Text[$i] -eq '{') { $d++ }
        elseif ($Text[$i] -eq '}') { $d--; if ($d -eq 0) { $end = $i; break } }
    }
    if ($end -lt 0) { throw "노드 끝을 못 찾았다: $Name" }
    $lc = $Text.IndexOf('"LuaChildren"', $start)
    if ($lc -lt 0 -or $lc -gt $end) { throw "$Name 안에 LuaChildren 이 없다" }
    $at = $Text.IndexOf('[', $lc) + 1
    $k = $at
    while ($k -lt $Text.Length -and $Text[$k] -match '[\s\r\n]') { $k++ }
    $isEmpty = ($k -lt $Text.Length -and $Text[$k] -eq ']')
    $b = $Blob
    if (-not $isEmpty) { $b += ',' }
    return $Text.Substring(0, $at) + "`r`n" + $b + $Text.Substring($at)
}

$text = Read-OvdrText -Path $LevelPath

# 앞서 깐 평면 지면 Part 를 걷어낸다
$gnd = ([regex]::Matches($text, '"Name":\s*"HWS_GND_')).Count
if ($gnd -gt 0) {
    Write-Host "평면 지면 Part $gnd 장을 지운다" -ForegroundColor Yellow
    $text = Remove-OvdrInstancesByName -Text $text -NamePrefix 'HWS_GND_'
}
# 기존 충돌층이 있으면 지운다 (재실행 가능하게)
$col = ([regex]::Matches($text, '"Name":\s*"HWS_COL_')).Count
if ($col -gt 0) {
    Write-Host "기존 충돌 슬래브 $col 장을 지운다" -ForegroundColor Yellow
    $text = Remove-OvdrInstancesByName -Text $text -NamePrefix 'HWS_COL_'
}

$cells = Get-Content -Raw -Path $CellJson | ConvertFrom-Json
$mat  = if ($Visible) { 'Basic' } else { 'Unlit' }
$tr   = if ($Visible) { 0 } else { 1 }
$k = Get-OvdrKeyIndex -Text $text
$items = New-Object System.Collections.Generic.List[string]
foreach ($c in $cells) {
    $k++
    # 형광 라임(0,255,120)은 예전 레벨이 검증 때 쓴 색 그대로다
    $items.Add((New-OvdrPartJson -Name $c.name -ObjectKey $k `
        -PX $c.pos[0] -PY $c.pos[1] -PZ $c.pos[2] `
        -OX $c.ori[0] -OY (-$c.ori[1]) -OZ $c.ori[2] `
        -SX $c.size[0] -SY $c.size[1] -SZ $c.size[2] `
        -Material $mat -Transparency $tr -CanCollide $true `
        -R 0 -G 255 -B 120))
}
Write-Host ("충돌 슬래브 {0} 장   재질 {1}  Transparency {2}  ({3})" -f
    $cells.Count, $mat, $tr, $(if ($Visible) { '눈으로 확인하는 단계' } else { '최종 투명' })) -ForegroundColor Cyan

$new = Insert-IntoNamedNode -Text $text -Name $CONTAINER -Blob ($items -join ",`r`n")
$new = Set-OvdrKeyIndex -Text $new -Value $k
$null = $new | ConvertFrom-Json
foreach ($g in @('HWS_Bound_North','HWS_Spawn_Red','HWS_Spawn_Blue','JSN_Sangok',
                 'Changdeokgung Place','KRM_Palace','Lobby')) {
    if ($new -notmatch ('"Name":\s*"' + [regex]::Escape($g) + '"')) { throw "사라지면 안 되는 것: $g" }
}
Write-Host ("텍스트 {0:N0} -> {1:N0} 자   ObjectKey {2} 까지" -f $text.Length, $new.Length, $k) -ForegroundColor Green

if (-not $Apply) { Write-Host "`n미리보기만 했다. 반영하려면 -Apply." -ForegroundColor Yellow; return }
$null = Backup-OvdrLevel -Path $LevelPath -Tag ('hws_col_' + $(if ($Visible) { 'visible' } else { 'final' }))
Write-OvdrText -Text $new -Path $LevelPath
$null = Invoke-OvdrRpc -Method 'game.stop' -TimeoutSec 30
Publish-OvdrLevel
