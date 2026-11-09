# JSN_COL 충돌 슬래브의 Material 을 바꾼다.
#
# ★ 2026-08-30 : 산곡에만 Transparency=1 + Material="Basic" 파트가 1,669개 있다.
#   화성 HWS_COL 992장과 크렘린 KRM_COL 164장은 전부 "Unlit" 이고,
#   그 두 맵은 안드로이드에서 멀쩡하다. 산곡만 깨진다.
#
#   불투명도 0 인 lit 머티리얼이 컬링되지 않고 translucent 드로우로 분류되면
#   매 프레임 1,669개를 카메라 거리로 정렬해야 한다 -- 정지 시 안정, 이동 시 요동.
#   "움직이면 깨지고 투명해지는데 멈추면 멀쩡" 이라는 증상과 정확히 맞는다.
#
#   되돌리기는 -Material Basic 이다. 백업도 남는다.
#
#   .\jsn_col_material.ps1                          # 미리보기
#   .\jsn_col_material.ps1 -Apply
#   .\jsn_col_material.ps1 -Material Basic -Apply   # 되돌리기
param(
    [ValidateSet('Unlit', 'Basic')][string] $Material = 'Unlit',
    [string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm",
    [switch] $Apply
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"
. "$PSScriptRoot\ovdr_script.ps1"

$Container = 'JSN_Sangok'
$Expect = 1669

$text = Read-OvdrText -Path $LevelPath

# 컨테이너 블록을 통째로 잘라낸다 (col_enable.ps1 과 같은 방식)
$m = [regex]::Match($text, '"Name":\s*"' + [regex]::Escape($Container) + '"')
if (-not $m.Success) { throw ("컨테이너를 못 찾았다: " + $Container) }
$i = $m.Index; $d = 0
while ($i -ge 0) { $c = $text[$i]; if ($c -eq '}') { $d++ } elseif ($c -eq '{') { if ($d -eq 0) { break }; $d-- }; $i-- }
$j = $i; $d = 0; $s = $false
while ($j -lt $text.Length) {
    $c = $text[$j]
    if ($s) { if ($c -eq '\') { $j += 2; continue }; if ($c -eq '"') { $s = $false } }
    else { if ($c -eq '"') { $s = $true } elseif ($c -eq '{') { $d++ } elseif ($c -eq '}') { $d--; if ($d -eq 0) { break } } }
    $j++
}
$blkStart = $i; $blkEnd = $j
$blk = $text.Substring($blkStart, $blkEnd - $blkStart + 1)

function Node-Span {
    param([string] $Txt, [int] $At)
    $i = $At; $d = 0
    while ($i -ge 0) { $c = $Txt[$i]; if ($c -eq '}') { $d++ } elseif ($c -eq '{') { if ($d -eq 0) { break }; $d-- }; $i-- }
    if ($i -lt 0) { return $null }
    $j = $i; $d = 0; $s = $false
    while ($j -lt $Txt.Length) {
        $c = $Txt[$j]
        if ($s) { if ($c -eq '\') { $j += 2; continue }; if ($c -eq '"') { $s = $false } }
        else { if ($c -eq '"') { $s = $true } elseif ($c -eq '{') { $d++ } elseif ($c -eq '}') { $d--; if ($d -eq 0) { return [pscustomobject]@{ Start = $i; End = $j } } } }
        $j++
    }
    return $null
}

# JSN_COL_* Part 잎 노드만 고른다
$edits = @()
$seen = @{}
foreach ($mm in [regex]::Matches($blk, '"InstanceType":\s*"Part"')) {
    $ns = Node-Span -Txt $blk -At $mm.Index
    if ($null -eq $ns) { continue }
    $ch = $blk.Substring($ns.Start, $ns.End - $ns.Start + 1)
    $nm = [regex]::Match($ch, '"Name":\s*"(JSN_COL_[^"]*)"')
    if (-not $nm.Success) { continue }

    $cur = [regex]::Match($ch, '"Material":\s*"([^"]*)"')
    if ($cur.Success) { $k = $cur.Groups[1].Value; $seen[$k] = 1 + $(if ($seen.ContainsKey($k)) { $seen[$k] } else { 0 }) }

    $new = $ch -replace '"Material":\s*"[^"]*"', ('"Material": "' + $Material + '"')
    if ($new -cne $ch) {
        $edits += [pscustomobject]@{ Name = $nm.Groups[1].Value; At = $ns.Start; Len = ($ns.End - $ns.Start + 1); New = $new }
    }
}

Write-Host ("{0} : JSN_COL Part 의 현재 Material 분포" -f $Container) -ForegroundColor Cyan
$seen.GetEnumerator() | Sort-Object Value -Descending | ForEach-Object { "   {0,-10} {1,5}개" -f $_.Key, $_.Value }
Write-Host ("-> {0} 개를 Material=""{1}"" 로 바꾼다" -f $edits.Count, $Material) -ForegroundColor Cyan
if ($edits.Count -eq 0) { Write-Host "바꿀 게 없다 (이미 그 상태다)." -ForegroundColor Yellow; return }
$edits | Select-Object -First 5 | ForEach-Object { "   " + $_.Name }
if ($edits.Count -gt 5) { "   ... +{0}개" -f ($edits.Count - 5) }
if ($edits.Count -ne $Expect) {
    Write-Host ("  ! 기대한 개수({0})와 다르다. 확인해라." -f $Expect) -ForegroundColor Yellow
}

$newBlk = $blk
foreach ($e in ($edits | Sort-Object At -Descending)) {
    $newBlk = $newBlk.Substring(0, $e.At) + $e.New + $newBlk.Substring($e.At + $e.Len)
}
$new = $text.Substring(0, $blkStart) + $newBlk + $text.Substring($blkEnd + 1)
$null = $new | ConvertFrom-Json

if (-not $Apply) { Write-Host "`n미리보기만 했다. 반영하려면 -Apply." -ForegroundColor Yellow; return }
$null = Backup-OvdrLevel -Path $LevelPath -Tag ("jsncol_" + $Material)
Write-OvdrText -Text $new -Path $LevelPath
$null = Invoke-OvdrRpc -Method 'game.stop' -TimeoutSec 30
Publish-OvdrLevel
