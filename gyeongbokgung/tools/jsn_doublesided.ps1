# 산곡의 비(非)식생 MeshPart 에서 DoubleSided 를 끈다.
#
# ★ 생성기의 원래 의도로 되돌리는 것이다. _ovdr\regen_batches.py:36 을 보면
#     DS = {"MST_PINE", "MST_EULALIA", "MST_ARTEMISIA"}   # 알파 카드
#   식생 3종만 true 고, STATIC 19장(:99)은 false 로 내보냈다.
#   그런데 라이브 레벨에서는 STA_TER 16장 + STA_STEPS + 물 2장이 true 로 뒤집혀 있다.
#   이음매 실험 중에 손으로 바꾼 것이고, 명세서 §4 는 그 실험을 실패로 기록했다 --
#   "확대해선 깨끗했지만 실사용 시야에서는 선이 더 잘 보였다". 되돌린 적이 없다.
#
# ★ 식생 1,613개는 절대 건드리지 않는다. 끄면 잎이 절반 사라진다
#   (SPEC_FOR_OVERDARE_MCP.md:86). 그래서 JSN_Pine_* / JSN_Und_* 는 제외한다.
#
# ★ 부작용 : 타일 이음매에 단차가 있는 자리에서 옆 타일 밑면이 살짝 보일 수 있다.
#   그게 원래 DoubleSided 를 켰던 이유인데, 명세서는 그 시도가 더 나빴다고 적었다.
#   되돌리기는 -On 이다.
#
# ★ DoubleSided 는 레벨 전용 속성이다. FBX/머티리얼에 굽지 않으므로
#   재임포트도 재발행도 필요 없다.
#
#   .\jsn_doublesided.ps1              # 미리보기 (끄기)
#   .\jsn_doublesided.ps1 -Apply
#   .\jsn_doublesided.ps1 -On -Apply   # 되돌리기
param(
    [switch] $On,
    [string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm",
    [switch] $Apply
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"
. "$PSScriptRoot\ovdr_script.ps1"

$Container = 'JSN_Sangok'
$want = if ($On) { 'true' } else { 'false' }

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

$edits = @()
$skipped = 0
foreach ($mm in [regex]::Matches($blk, '"InstanceType":\s*"MeshPart"')) {
    $ns = Node-Span -Txt $blk -At $mm.Index
    if ($null -eq $ns) { continue }
    $ch = $blk.Substring($ns.Start, $ns.End - $ns.Start + 1)
    $nm = [regex]::Match($ch, '"Name":\s*"([^"]+)"')
    if (-not $nm.Success) { continue }
    $name = $nm.Groups[1].Value

    # 알파 카드 식생은 절대 제외
    if ($name -match '^(JSN_Pine_|JSN_Und_)') { $skipped++; continue }

    $new = $ch -replace '"DoubleSided":\s*(true|false)', ('"DoubleSided": ' + $want)
    if ($new -cne $ch) {
        $edits += [pscustomobject]@{ Name = $name; At = $ns.Start; Len = ($ns.End - $ns.Start + 1); New = $new }
    }
}

Write-Host ("{0} : 식생 {1} 개는 건드리지 않았다 (알파 카드)" -f $Container, $skipped) -ForegroundColor DarkGray
Write-Host ("-> 비식생 MeshPart {0} 개를 DoubleSided={1} 로 바꾼다" -f $edits.Count, $want) -ForegroundColor Cyan
if ($edits.Count -eq 0) { Write-Host "바꿀 게 없다 (이미 그 상태다)." -ForegroundColor Yellow; return }
$edits | ForEach-Object { "   " + $_.Name }

$newBlk = $blk
foreach ($e in ($edits | Sort-Object At -Descending)) {
    $newBlk = $newBlk.Substring(0, $e.At) + $e.New + $newBlk.Substring($e.At + $e.Len)
}
$new = $text.Substring(0, $blkStart) + $newBlk + $text.Substring($blkEnd + 1)
$null = $new | ConvertFrom-Json

if (-not $Apply) { Write-Host "`n미리보기만 했다. 반영하려면 -Apply." -ForegroundColor Yellow; return }
$null = Backup-OvdrLevel -Path $LevelPath -Tag ("jsnds_" + $want)
Write-OvdrText -Text $new -Path $LevelPath
$null = Invoke-OvdrRpc -Method 'game.stop' -TimeoutSec 30
Publish-OvdrLevel
