# 화성 MeshPart 189장의 CFrame.Orientation 을 (0,0,0) 으로 되돌린다.
#
# ★ 폐가 현상의 원인 #1 이다. 화성_인계프롬프트_v2.md §1 이 진단해 놓고
#   적용된 적이 없다 (2026-08-30 실측: 189/189 이 여전히 (0,-180,0)).
#
#   이 맵은 회전이 이미 메시 정점에 구워져 있다 -- export_overdare.py 가 오브젝트마다
#   matrix_world 를 정점에 적용해 내보내고, 임포터는 각 메시를 제 bbox 중심으로
#   재중심화한다. 그 상태에서 Y 180 도를 주면 **조각 하나하나가 제자리에서 뒤집힌다.**
#   지붕 조각이 이웃과 반대로 돌고, 서까래가 바깥을 향하고, 조립이 흩어진다.
#
#   (0,-180,0) 은 산곡의 보정값이다. 산곡은 마스터를 인스턴싱해 배치하므로 회전을
#   CFrame 이 정하지만, 화성은 그 방식이 아니다. 규약을 섞은 것이 원인이다.
#
# ★ 위치와 Size 는 절대 손대지 않는다. 재발행도 재익스포트도 필요 없다.
#
# ★ 고친 뒤 부재 하나가 여전히 틀어져 보여도 **그것만 따로 돌리지 마라.**
#   좌표계 오류를 가려서 다음에 같은 문제가 다시 난다. 보고할 것.
#
#   .\hws_orient_fix.ps1                    # 미리보기
#   .\hws_orient_fix.ps1 -Apply
#   .\hws_orient_fix.ps1 -YawY -180 -Apply  # 되돌리기
param(
    [double] $YawY = 0,
    [string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm",
    [switch] $Apply
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"
. "$PSScriptRoot\ovdr_script.ps1"

$Container = 'Hwaseong Place'
$Expect = 189
$inv = [Globalization.CultureInfo]::InvariantCulture

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
#   여는 따옴표까지 포함해 매치하면 진짜 CFrame 만 잡힌다.
$edits = @()
$was = @{}
foreach ($mm in [regex]::Matches($blk, '"InstanceType":\s*"MeshPart"')) {
    $ns = Node-Span -Txt $blk -At $mm.Index
    if ($null -eq $ns) { continue }
    $ch = $blk.Substring($ns.Start, $ns.End - $ns.Start + 1)
    $nm = [regex]::Match($ch, '"Name":\s*"([^"]+)"')
    if (-not $nm.Success) { continue }

    $cf = [regex]::Match($ch, '"CFrame"\s*:\s*\{')
    if (-not $cf.Success) { throw ("CFrame 을 못 찾았다: " + $nm.Groups[1].Value) }
    $tail = $ch.Substring($cf.Index)
    $om = [regex]::Match($tail, '"Orientation"\s*:\s*\{[^{}]*\}')
    if (-not $om.Success) { throw ("Orientation 을 못 찾았다: " + $nm.Groups[1].Value) }

    $ob = $om.Value
    $ox = [regex]::Match($ob, '"X"\s*:\s*(-?[\d.eE+]+)').Groups[1].Value
    $oy = [regex]::Match($ob, '"Y"\s*:\s*(-?[\d.eE+]+)').Groups[1].Value
    $oz = [regex]::Match($ob, '"Z"\s*:\s*(-?[\d.eE+]+)').Groups[1].Value
    $key = "$ox,$oy,$oz"
    $was[$key] = 1 + $(if ($was.ContainsKey($key)) { $was[$key] } else { 0 })

    # Orientation 블록 안에서만 세 값을 바꾼다. Position 은 건드리지 않는다.
    $nb = $ob
    $nb = [regex]::Replace($nb, '("X"\s*:\s*)-?[\d.eE+]+', ('${1}0'))
    $nb = [regex]::Replace($nb, '("Y"\s*:\s*)-?[\d.eE+]+', ('${1}' + $YawY.ToString($inv)))
    $nb = [regex]::Replace($nb, '("Z"\s*:\s*)-?[\d.eE+]+', ('${1}0'))
    if ($nb -ceq $ob) { continue }

    $gi = $cf.Index + $om.Index
    $newCh = $ch.Substring(0, $gi) + $nb + $ch.Substring($gi + $om.Length)
    $edits += [pscustomobject]@{ Name = $nm.Groups[1].Value; At = $ns.Start; Len = ($ns.End - $ns.Start + 1); Txt = $newCh }
}

Write-Host ("{0} : 현재 Orientation 분포" -f $Container) -ForegroundColor Cyan
$was.GetEnumerator() | Sort-Object Value -Descending | ForEach-Object { "   ({0}) {1,5}개" -f $_.Key, $_.Value }
Write-Host ("-> {0} 개를 (0, {1}, 0) 으로 바꾼다" -f $edits.Count, $YawY) -ForegroundColor Cyan
if ($edits.Count -eq 0) { Write-Host "바꿀 게 없다 (이미 그 상태다)." -ForegroundColor Yellow; return }
$edits | Select-Object -First 5 | ForEach-Object { "   " + $_.Name }
if ($edits.Count -gt 5) { "   ... +{0}개" -f ($edits.Count - 5) }
if ($edits.Count -ne $Expect) { Write-Host ("  ! 기대한 개수({0})와 다르다. 확인해라." -f $Expect) -ForegroundColor Yellow }

$newBlk = $blk
foreach ($e in ($edits | Sort-Object At -Descending)) {
    $newBlk = $newBlk.Substring(0, $e.At) + $e.Txt + $newBlk.Substring($e.At + $e.Len)
}
$new = $text.Substring(0, $blkStart) + $newBlk + $text.Substring($blkEnd + 1)
$null = $new | ConvertFrom-Json

if (-not $Apply) { Write-Host "`n미리보기만 했다. 반영하려면 -Apply." -ForegroundColor Yellow; return }
$null = Backup-OvdrLevel -Path $LevelPath -Tag ("hwsorient_" + $YawY)
Write-OvdrText -Text $new -Path $LevelPath
$null = Invoke-OvdrRpc -Method 'game.stop' -TimeoutSec 30
Publish-OvdrLevel
