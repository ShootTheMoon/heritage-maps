# 화성 건물이 사람 키 대비 얼마나 큰지 잰다.
# 캐릭터 캡슐 높이는 205 cm 다 (MovementSpeedServer : 164 * CHARACTER_SCALE 1.25).
param([string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm")
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"

$PLAYER = 205.0
$NUM = '(-?[\d.]+(?:[eE][-+]?\d+)?)'
$text = Read-OvdrText -Path $LevelPath

$m = [regex]::Match($text, '"Name":\s*"Hwaseong Place"')
$i = $m.Index; $d = 0
while ($i -ge 0) { $c = $text[$i]; if ($c -eq '}') { $d++ } elseif ($c -eq '{') { if ($d -eq 0) { break }; $d-- }; $i-- }
$j = $i; $d = 0; $s = $false
while ($j -lt $text.Length) {
    $c = $text[$j]
    if ($s) { if ($c -eq '\') { $j += 2; continue }; if ($c -eq '"') { $s = $false } }
    else { if ($c -eq '"') { $s = $true } elseif ($c -eq '{') { $d++ } elseif ($c -eq '}') { $d--; if ($d -eq 0) { break } } }
    $j++
}
$blk = $text.Substring($i, $j - $i + 1)

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

$rows = @()
foreach ($mm in [regex]::Matches($blk, '"InstanceType":\s*"MeshPart"')) {
    $ns = Node-Span -Txt $blk -At $mm.Index
    if ($null -eq $ns) { continue }
    $ch = $blk.Substring($ns.Start, $ns.End - $ns.Start + 1)
    $nm = [regex]::Match($ch, '"Name":\s*"([^"]+)"')
    # ★ UnitExtent 가 실치수의 절반이다. Size 는 배율(100=원본)이라 크기를 못 잰다.
    $ue = [regex]::Match($ch, '"UnitExtent":\s*\{[^{}]*?"X":\s*' + $NUM + '[^{}]*?"Y":\s*' + $NUM + '[^{}]*?"Z":\s*' + $NUM)
    if (-not ($nm.Success -and $ue.Success)) { continue }
    $rows += [pscustomobject]@{
        Name = $nm.Groups[1].Value
        W = [Math]::Abs([double]$ue.Groups[1].Value) * 2
        H = [Math]::Abs([double]$ue.Groups[2].Value) * 2
        D = [Math]::Abs([double]$ue.Groups[3].Value) * 2
    }
}

Write-Host ("MeshPart {0} 개  (캐릭터 키 {1} cm 기준)" -f $rows.Count, $PLAYER) -ForegroundColor Cyan

$sorted = $rows | Sort-Object H -Descending
Write-Host "`n== 가장 높은 것 12개 ==" -ForegroundColor Cyan
$sorted | Select-Object -First 12 | ForEach-Object {
    "  {0,-34} 높이 {1,8:N0} cm = {2,5:N1} m   사람 {3,5:N1} 배   (폭 {4:N0} x {5:N0})" -f `
        $_.Name, $_.H, ($_.H / 100), ($_.H / $PLAYER), $_.W, $_.D
}

$hs = $rows | ForEach-Object { $_.H } | Sort-Object
$q = { param($a, $p) $a[[int][Math]::Floor(($a.Count - 1) * $p)] }
Write-Host ("`n높이 분포  중앙값 {0:N0} cm ({1:N1} m, 사람 {2:N1}배)   상위10%% {3:N0} cm ({4:N1} m)" -f `
    (& $q $hs 0.5), ((& $q $hs 0.5) / 100), ((& $q $hs 0.5) / $PLAYER), (& $q $hs 0.9), ((& $q $hs 0.9) / 100))

# 성벽만 따로
$wall = @($rows | Where-Object { $_.Name -match 'Wall' })
if ($wall.Count) {
    $wh = $wall | ForEach-Object { $_.H } | Sort-Object
    Write-Host ("성벽(Wall) {0}장  높이 중앙값 {1:N0} cm = {2:N1} m  (사람 {3:N1}배)" -f `
        $wall.Count, (& $q $wh 0.5), ((& $q $wh 0.5) / 100), ((& $q $wh 0.5) / $PLAYER)) -ForegroundColor Yellow
}
Write-Host "`n참고 : 실제 수원화성 성벽은 약 5 m 다." -ForegroundColor Yellow
