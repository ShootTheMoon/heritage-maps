# 화성 지면 -- 창덕궁 방식(축정렬 평면 + 재질 오버레이)으로 다시 깐다.
#
# ★ 왜 바꿨나 : 기울인 슬래브 992장은 각자 자기 최소자승 평면에 맞춰 따로 돌아가서
#   인접 판끼리 각이 안 맞고 경계마다 턱이 진다. "삐뚤빼뚤" 하다는 실사용 판정을 받았다.
#   기복이 372 m 에 7.5 m (경사 2%) 라 눈에 거의 안 보이는데 그걸 표현하려고
#   992번 꺾은 대가가 너무 컸다.
#
# ★ 창덕궁이 정답을 보여준다 -- Part 727장 전부 Orientation (0,0,0), 축정렬 박스,
#   재질 오버레이를 서로 다른 Y 로 얹어 동일평면을 안 만든다(Z-파이팅 원천 차단).
#   여기서도 같은 규약을 따른다. 구역마다 dy 6/8/12/16/20 cm 로 층을 갈랐다.
#
# ★ 판 수 992 -> 280 (72% 감소). 남는 712장은 나중에 올릴 건물 임포트 예산이다.
#
#   .\hws_flat.ps1           # 미리보기
#   .\hws_flat.ps1 -Apply
param(
    [string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm",
    [string] $PartJson  = "$env:USERPROFILE\Desktop\blender\hwaseong_rebuild\hws_flat.json",
    [switch] $Apply
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"
. "$PSScriptRoot\ovdr_script.ps1"

$PREFIX = 'HWS_GND_'
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
    $br = $Text.IndexOf('[', $lc)
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
    Write-Host "기존 지면 $had 장을 지운다" -ForegroundColor Yellow
    $text = Remove-OvdrInstancesByName -Text $text -NamePrefix $PREFIX
}

$parts = Get-Content -Raw -Path $PartJson | ConvertFrom-Json
$k = Get-OvdrKeyIndex -Text $text
$items = New-Object System.Collections.Generic.List[string]
$tally = @{}
foreach ($p in $parts) {
    $k++
    $tally[$p.mat] = 1 + $(if ($tally.ContainsKey($p.mat)) { $tally[$p.mat] } else { 0 })
    $items.Add((New-OvdrPartJson -Name $p.name -ObjectKey $k `
        -PX $p.px -PY $p.py -PZ $p.pz `
        -OX 0 -OY 0 -OZ 0 `
        -SX $p.sx -SY $p.sy -SZ $p.sz `
        -Material $p.mat -Transparency 0 -CanCollide $true `
        -R $p.col[0] -G $p.col[1] -B $p.col[2]))
}
Write-Host ("Part {0} 장  (전부 Orientation 0, 축정렬)" -f $parts.Count) -ForegroundColor Cyan
foreach ($e in ($tally.GetEnumerator() | Sort-Object Value -Descending)) {
    Write-Host ("   {0,-16} {1,4} 장" -f $e.Key, $e.Value) -ForegroundColor DarkGray
}

$new = Insert-IntoNamedNode -Text $text -Name $CONTAINER -Blob ($items -join ",`r`n")
$new = Set-OvdrKeyIndex -Text $new -Value $k
$null = $new | ConvertFrom-Json
foreach ($g in @('HWS_Bound_North','HWS_Spawn_Red','HWS_Spawn_Blue','JSN_Sangok',
                 'Changdeokgung Place','KRM_Palace','Lobby')) {
    if ($new -notmatch ('"Name":\s*"' + [regex]::Escape($g) + '"')) { throw "사라지면 안 되는 것: $g" }
}
Write-Host ("텍스트 {0:N0} -> {1:N0} 자   ObjectKey {2} 까지" -f $text.Length, $new.Length, $k) -ForegroundColor Green

if (-not $Apply) { Write-Host "`n미리보기만 했다. 반영하려면 -Apply." -ForegroundColor Yellow; return }
$null = Backup-OvdrLevel -Path $LevelPath -Tag 'hws_flat'
Write-OvdrText -Text $new -Path $LevelPath
$null = Invoke-OvdrRpc -Method 'game.stop' -TimeoutSec 30
Publish-OvdrLevel
