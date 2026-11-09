# 수원화성을 통째로 배율 조정한다.
#
# 지금은 0.25배 빌드라 93.2 x 96.2 m 밖에 안 된다 (크렘린 실내 96m 와 비슷하다).
# 야외 맵으로 쓰기엔 너무 좁아서 키운다.
#
# ★ Hwaseong Place 는 자식이 Model 150개이고 MeshPart 189장은 그 **안**에 있다.
#   깊이 1만 훑으면 안 된다. 잎 노드(MeshPart / Part / SpawnLocation)를 직접 찾아 옮긴다.
#
# ★ 문서 003 의 경고를 지킨다 :
#   "Model.WorldPivot 을 바꿔도 자손이 안 움직인다. 그래서 보정은 각 MeshPart 의 CFrame 에
#    똑같은 강체 변환을 하나씩 적용하는 방식으로 넣었다."
#   -> Model 노드는 손대지 않는다. 잎 노드만 옮긴다.
#
# ★ MeshPart 의 Size 는 배율이다 (100 = 원본 메시 크기).
#   Part(콜리전)의 Size 는 실치수 cm 다. 둘 다 같은 인수를 곱하면 되지만
#   의미가 다르다는 걸 알고 있어야 한다.
#
# 스폰 발판은 자리만 옮기고 크기는 그대로 둔다 (게임용 표시라 커질 이유가 없다).
# 경기구역 벽(HWS_Bound_*)은 건드리지 않는다. vote_bounds.ps1 이 새 범위로 다시 만든다.
#
#   .\hws_scale.ps1 -Factor 2            # 미리보기
#   .\hws_scale.ps1 -Factor 2 -Apply
param(
    [Parameter(Mandatory)][double] $Factor,
    [double] $OX = 61400,        # 배율 기준점. 콜리전 X 중심
    [double] $OY = 0,
    [double] $OZ = 0,
    [string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm",
    [switch] $Apply
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"
. "$PSScriptRoot\ovdr_script.ps1"

if ($Factor -le 0) { throw "Factor 는 0보다 커야 한다" }
$NUM = '(-?[\d.]+(?:[eE][-+]?\d+)?)'
$text = Read-OvdrText -Path $LevelPath

function Get-Span {
    param([string] $Txt, [string] $Name)
    $m = [regex]::Match($Txt, '"Name":\s*"' + [regex]::Escape($Name) + '"')
    if (-not $m.Success) { return $null }
    $i = $m.Index; $d = 0
    while ($i -ge 0) { $c = $Txt[$i]; if ($c -eq '}') { $d++ } elseif ($c -eq '{') { if ($d -eq 0) { break }; $d-- }; $i-- }
    $j = $i; $d = 0; $s = $false
    while ($j -lt $Txt.Length) {
        $c = $Txt[$j]
        if ($s) { if ($c -eq '\') { $j += 2; continue }; if ($c -eq '"') { $s = $false } }
        else { if ($c -eq '"') { $s = $true } elseif ($c -eq '{') { $d++ } elseif ($c -eq '}') { $d--; if ($d -eq 0) { return [pscustomobject]@{ Start = $i; End = $j } } } }
        $j++
    }
    return $null
}

# 어떤 위치에서 그 노드의 여는 중괄호를 거슬러 찾고, 짝이 맞는 닫는 중괄호까지의 범위를 준다
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

$stat = @{ mesh = 0; part = 0; spawn = 0; skip = 0; pos = 0; size = 0; ue = 0 }

foreach ($container in 'Hwaseong Place', 'Hwaseong Collision') {
    $sp = Get-Span -Txt $text -Name $container
    if ($null -eq $sp) { throw "$container 를 못 찾았다" }
    $blk = $text.Substring($sp.Start, $sp.End - $sp.Start + 1)

    # 잎 노드를 전부 찾는다 (깊이 무관). 뒤에서부터 고쳐야 인덱스가 안 밀린다.
    $leaves = @()
    foreach ($m in [regex]::Matches($blk, '"InstanceType":\s*"(MeshPart|Part|SpawnLocation)"')) {
        $ns = Node-Span -Txt $blk -At $m.Index
        if ($null -ne $ns) { $leaves += [pscustomobject]@{ Kind = $m.Groups[1].Value; Start = $ns.Start; Len = ($ns.End - $ns.Start + 1) } }
    }

    $newBlk = $blk
    foreach ($lf in ($leaves | Sort-Object Start -Descending)) {
        $ch = $blk.Substring($lf.Start, $lf.Len)
        $nm = [regex]::Match($ch, '"Name":\s*"([^"]+)"')
        $name = if ($nm.Success) { $nm.Groups[1].Value } else { '' }
        if ($name -like 'HWS_Bound_*') { $stat.skip++; continue }

        $isSpawn = ($lf.Kind -eq 'SpawnLocation')
        $new = $ch

        # CFrame.Position (PivotOffsetCFrame 이 아니라 진짜 CFrame 하나만)
        $new = [regex]::Replace($new,
            '("CFrame":\s*\{[\s\S]{0,200}?"Position":\s*\{[^{}]*?"X":\s*)' + $NUM + '([^{}]*?"Y":\s*)' + $NUM + '([^{}]*?"Z":\s*)' + $NUM,
            {
                param($m)
                $script:hitPos = $true
                $x = $OX + ([double]$m.Groups[2].Value - $OX) * $Factor
                $y = $OY + ([double]$m.Groups[4].Value - $OY) * $Factor
                $z = $OZ + ([double]$m.Groups[6].Value - $OZ) * $Factor
                $m.Groups[1].Value + ('{0:0.####}' -f $x) + $m.Groups[3].Value + ('{0:0.####}' -f $y) + $m.Groups[5].Value + ('{0:0.####}' -f $z)
            }, 1)
        if ($script:hitPos) { $stat.pos++; $script:hitPos = $false }

        if (-not $isSpawn) {
            $new = [regex]::Replace($new,
                '("Size":\s*\{[^{}]*?"X":\s*)' + $NUM + '([^{}]*?"Y":\s*)' + $NUM + '([^{}]*?"Z":\s*)' + $NUM,
                {
                    param($m)
                    $script:hitSize = $true
                    $m.Groups[1].Value + ('{0:0.####}' -f ([double]$m.Groups[2].Value * $Factor)) +
                    $m.Groups[3].Value + ('{0:0.####}' -f ([double]$m.Groups[4].Value * $Factor)) +
                    $m.Groups[5].Value + ('{0:0.####}' -f ([double]$m.Groups[6].Value * $Factor))
                }, 1)
            if ($script:hitSize) { $stat.size++; $script:hitSize = $false }

            $new = [regex]::Replace($new,
                '("UnitExtent":\s*\{[^{}]*?"X":\s*)' + $NUM + '([^{}]*?"Y":\s*)' + $NUM + '([^{}]*?"Z":\s*)' + $NUM,
                {
                    param($m)
                    $script:hitUe = $true
                    $m.Groups[1].Value + ('{0:0.####}' -f ([double]$m.Groups[2].Value * $Factor)) +
                    $m.Groups[3].Value + ('{0:0.####}' -f ([double]$m.Groups[4].Value * $Factor)) +
                    $m.Groups[5].Value + ('{0:0.####}' -f ([double]$m.Groups[6].Value * $Factor))
                }, 1)
            if ($script:hitUe) { $stat.ue++; $script:hitUe = $false }
        }

        if ($new -cne $ch) { $newBlk = $newBlk.Substring(0, $lf.Start) + $new + $newBlk.Substring($lf.Start + $lf.Len) }
        switch ($lf.Kind) { 'MeshPart' { $stat.mesh++ } 'SpawnLocation' { $stat.spawn++ } default { $stat.part++ } }
    }

    $text = $text.Substring(0, $sp.Start) + $newBlk + $text.Substring($sp.End + 1)
    Write-Host ("  {0,-20} 잎 노드 {1} 개" -f $container, $leaves.Count)
}

Write-Host ("`n배율 {0}x  기준점 ({1}, {2}, {3})" -f $Factor, $OX, $OY, $OZ) -ForegroundColor Cyan
Write-Host ("  MeshPart {0}  Part {1}  SpawnLocation {2}  건너뜀 {3}" -f $stat.mesh, $stat.part, $stat.spawn, $stat.skip)
Write-Host ("  Position {0} / Size {1} / UnitExtent {2} 건 수정" -f $stat.pos, $stat.size, $stat.ue)

# ★ 기대값 검산 : MeshPart 189 + Part 992 + Spawn 2 = 1183
if ($stat.mesh -ne 189) { Write-Host ("  ⚠ MeshPart 가 189 가 아니다 : {0}" -f $stat.mesh) -ForegroundColor Yellow }
if ($stat.part -ne 992) { Write-Host ("  ⚠ Part 가 992 가 아니다 : {0}" -f $stat.part) -ForegroundColor Yellow }

$null = $text | ConvertFrom-Json

if (-not $Apply) { Write-Host "`n미리보기만 했다. 반영하려면 -Apply." -ForegroundColor Yellow; return }
$null = Backup-OvdrLevel -Path $LevelPath -Tag ("hws_scale_" + ($Factor -replace '\.', 'p'))
Write-OvdrText -Text $text -Path $LevelPath
$null = Invoke-OvdrRpc -Method 'game.stop' -TimeoutSec 30
Publish-OvdrLevel
