# 지정한 MeshPart 무리의 충돌을 켜거나 끈다.
#
# ★ 이 엔진에서 **지형 메시**는 CanCollide 를 켜도 뚫고 떨어진다.
#   엔진이 알아서 하는 convex 분해가 높이맵을 볼록 덩어리 30개로 쪼개서
#   골짜기를 메우고 능선을 뭉갠다 (2026-08-18 실측, memory: overdare-terrain-collision).
#   그래서 지형은 Part 슬래브로 깐다.
#
#   반대로 **건물·바위처럼 convex 에 가까운 것은 켜면 먹는다.** 같은 기록에 적혀 있다.
#   화성 건물 189장과 크렘린 소품 98장이 여기 해당한다.
#
# ★ 정확한 Part 슬래브가 이미 덮고 있는 곳은 켜지 마라.
#   "엉성한 hull 이 정확한 Part 층과 싸운다" -- 크렘린 셸 25장이 그 경우다.
#
# ★ 2026-08-30 : hws-place 의 매처 `-notlike 'HWS_*'` 는 건물만 잡는 게 아니었다.
#   지면 HGD_01(372x384 m), 도로 3장, 알파카드 VEG/CTP 8장까지 같이 켰다.
#   그래서 안드로이드에서 바닥을 뚫고 떨어졌다 -- 위 ★ 그대로다.
#   hws-terrain 은 그 12장만 골라낸다. 건물 177장은 건드리지 않는다.
#
# 대상 :
#   hws-place   화성 건물 189장            (지금 충돌 0)
#   hws-terrain 화성 지면·도로·수목 12장   (건물 제외. 이건 꺼야 한다)
#   krm-prop    크렘린 소품 98장           (엄폐물 0)
#
#   .\col_enable.ps1 -Target hws-place            # 미리보기
#   .\col_enable.ps1 -Target hws-place -Apply
#   .\col_enable.ps1 -Target hws-place -Off -Apply
param(
    [Parameter(Mandatory)][ValidateSet('hws-place', 'hws-terrain', 'krm-prop')][string] $Target,
    [string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm",
    [switch] $Off,
    [switch] $Apply
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"
. "$PSScriptRoot\ovdr_script.ps1"

$spec = @{
    'hws-place' = @{ Container = 'Hwaseong Place'; Match = { param($n) $n -notlike 'HWS_*' }; Expect = 189 }
    'hws-terrain' = @{ Container = 'Hwaseong Place'; Match = { param($n) $n -match '^(HGD_|dirt_|VEG_|CTP_)' }; Expect = 12 }
    'krm-prop'  = @{ Container = 'KRM_Palace';     Match = { param($n) $n -like 'KRMM_KRM_PROP*' }; Expect = 98 }
}[$Target]

$want = -not $Off
$wantCC = if ($want) { 'true' } else { 'false' }
$wantProf = if ($want) { 'BlockAll' } else { 'NoCollision' }

$text = Read-OvdrText -Path $LevelPath

# 컨테이너 블록
$m = [regex]::Match($text, '"Name":\s*"' + [regex]::Escape($spec.Container) + '"')
if (-not $m.Success) { throw ("컨테이너를 못 찾았다: " + $spec.Container) }
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

# MeshPart 잎 노드만 고른다
$edits = @()
foreach ($mm in [regex]::Matches($blk, '"InstanceType":\s*"MeshPart"')) {
    $ns = Node-Span -Txt $blk -At $mm.Index
    if ($null -eq $ns) { continue }
    $ch = $blk.Substring($ns.Start, $ns.End - $ns.Start + 1)
    $nm = [regex]::Match($ch, '"Name":\s*"([^"]+)"')
    $name = if ($nm.Success) { $nm.Groups[1].Value } else { '' }
    if (-not (& $spec.Match $name)) { continue }

    $new = $ch
    $new = $new -replace '"CanCollide":\s*(true|false)', ('"CanCollide": ' + $wantCC)
    $new = $new -replace '"CollisionProfile":\s*"[^"]*"', ('"CollisionProfile": "' + $wantProf + '"')
    if ($new -cne $ch) {
        $edits += [pscustomobject]@{ Name = $name; At = $ns.Start; Len = ($ns.End - $ns.Start + 1); New = $new }
    }
}

Write-Host ("{0} : MeshPart {1} 개를 CanCollide={2} / {3} 로 바꾼다" -f `
    $spec.Container, $edits.Count, $wantCC, $wantProf) -ForegroundColor Cyan
if ($edits.Count -eq 0) { Write-Host "바꿀 게 없다 (이미 그 상태다)." -ForegroundColor Yellow; return }
$edits | Select-Object -First 6 | ForEach-Object { "   " + $_.Name }
if ($edits.Count -gt 6) { "   ... +{0}개" -f ($edits.Count - 6) }

if ($edits.Count -ne $spec.Expect) {
    Write-Host ("  ⚠ 기대한 개수({0})와 다르다. 확인해라." -f $spec.Expect) -ForegroundColor Yellow
}

$newBlk = $blk
foreach ($e in ($edits | Sort-Object At -Descending)) {
    $newBlk = $newBlk.Substring(0, $e.At) + $e.New + $newBlk.Substring($e.At + $e.Len)
}
$new = $text.Substring(0, $blkStart) + $newBlk + $text.Substring($blkEnd + 1)
$null = $new | ConvertFrom-Json

if (-not $Apply) { Write-Host "`n미리보기만 했다. 반영하려면 -Apply." -ForegroundColor Yellow; return }
$null = Backup-OvdrLevel -Path $LevelPath -Tag ("col_" + $Target + "_" + $wantCC)
Write-OvdrText -Text $new -Path $LevelPath
$null = Invoke-OvdrRpc -Method 'game.stop' -TimeoutSec 30
Publish-OvdrLevel
