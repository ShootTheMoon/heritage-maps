# 화성 도로 3장(dirt_road / dirt_path / dirt_verge)의 CFrame.Position.Y 를 올린다.
#
# ★ 왜 : 출하 FBX 실측(정점마다 지면에 수직 레이캐스트)
#     dirt_road   min  2.97 cm   p05 13.2 cm   p50 21.4 cm
#     dirt_path   min  9.56 cm   p05 22.1 cm   p50 32.3 cm
#     dirt_verge  min -5.99 cm   p05  8.6 cm   p50 22.3 cm   ← 17개 정점이 지면 아래
#   근본 원인은 city.py 의 ROAD_CLEAR(0.06) - ROAD_SHOULDER(0.055) = 0.005 m 다.
#   깊이버퍼 해상도가 near 10cm/24-bit 기준 300 m 에서 5.4 cm, 16-bit 면 14 m 에서 3 cm 라
#   이 여유는 해상도 이하로 들어간다. iOS(reversed-Z float32)는 세 자릿수 여유가 있다.
#
# ★ 이건 진단용 강수(強手)다. 델타를 크게 줘서 Z-파이팅이 원인인지 아닌지부터 가른다.
#   원인이 맞으면 그 다음에 값을 낮춰 최소치를 찾는다. 원인이 아니면 여기서 끝내고
#   다른 데를 판다 -- 되돌리기가 -Delta 음수 한 줄이라 싸다.
#
# ★ 부작용 : 갓길 바깥은 스커트 면이 없는 열린 자유 모서리다(city.py:424-436).
#   많이 올리면 얕은 각도에서 턱과 그 밑이 보인다. 진단이 끝나면 최소치로 낮춰라.
#
# ★ 안전 : 임포터가 메시를 bbox 로 재중심화하므로 FBX 는 월드 위치를 안 들고 있다.
#   위치는 전적으로 CFrame 이 정한다(make_placement.py:34). 순수 Y 이동은 안전하다.
#   Orientation.Y = -180 은 그대로 둔다 -- 명세서 §1-2 의 경고다. 건드리지 마라.
#
#   .\hws_road_lift.ps1                 # 미리보기 (+25)
#   .\hws_road_lift.ps1 -Apply
#   .\hws_road_lift.ps1 -Delta -25 -Apply    # 되돌리기
param(
    [double] $Delta = 25,
    [string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm",
    [switch] $Apply
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"
. "$PSScriptRoot\ovdr_script.ps1"

$Container = 'Hwaseong Place'
$Expect = 3

$text = Read-OvdrText -Path $LevelPath

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

# ★ "PivotOffsetCFrame" 안에는 부분문자열 '"CFrame":' 이 없다 (C 앞 글자가 t 다).
#   그래서 여는 따옴표까지 포함해 매치하면 진짜 CFrame 만 잡힌다.
$edits = @()
foreach ($mm in [regex]::Matches($blk, '"InstanceType":\s*"MeshPart"')) {
    $ns = Node-Span -Txt $blk -At $mm.Index
    if ($null -eq $ns) { continue }
    $ch = $blk.Substring($ns.Start, $ns.End - $ns.Start + 1)
    $nm = [regex]::Match($ch, '"Name":\s*"(dirt_[^"]*)"')
    if (-not $nm.Success) { continue }

    $cf = [regex]::Match($ch, '"CFrame"\s*:\s*\{')
    if (-not $cf.Success) { throw ("CFrame 을 못 찾았다: " + $nm.Groups[1].Value) }
    $py = [regex]::Match($ch.Substring($cf.Index), '"Position"\s*:\s*\{[^{}]*?"Y"\s*:\s*(-?[\d.eE+]+)')
    if (-not $py.Success) { throw ("Position.Y 를 못 찾았다: " + $nm.Groups[1].Value) }

    $old = [double] $py.Groups[1].Value
    $new = $old + $Delta
    $gi = $cf.Index + $py.Groups[1].Index
    $gl = $py.Groups[1].Length
    $newCh = $ch.Substring(0, $gi) + $new.ToString([Globalization.CultureInfo]::InvariantCulture) + $ch.Substring($gi + $gl)

    $edits += [pscustomobject]@{ Name = $nm.Groups[1].Value; Old = $old; New = $new; At = $ns.Start; Len = ($ns.End - $ns.Start + 1); Txt = $newCh }
}

Write-Host ("{0} : dirt_* MeshPart {1} 개, Position.Y {2:+0.##;-0.##} 이동" -f $Container, $edits.Count, $Delta) -ForegroundColor Cyan
$edits | ForEach-Object { "   {0,-22} {1,10:F3}  ->  {2,10:F3}" -f $_.Name, $_.Old, $_.New }
if ($edits.Count -ne $Expect) { Write-Host ("  ! 기대한 개수({0})와 다르다. 확인해라." -f $Expect) -ForegroundColor Yellow; return }

$newBlk = $blk
foreach ($e in ($edits | Sort-Object At -Descending)) {
    $newBlk = $newBlk.Substring(0, $e.At) + $e.Txt + $newBlk.Substring($e.At + $e.Len)
}
$new = $text.Substring(0, $blkStart) + $newBlk + $text.Substring($blkEnd + 1)
$null = $new | ConvertFrom-Json

if (-not $Apply) { Write-Host "`n미리보기만 했다. 반영하려면 -Apply." -ForegroundColor Yellow; return }
$null = Backup-OvdrLevel -Path $LevelPath -Tag ("roadlift_" + $Delta)
Write-OvdrText -Text $new -Path $LevelPath
$null = Invoke-OvdrRpc -Method 'game.stop' -TimeoutSec 30
Publish-OvdrLevel
