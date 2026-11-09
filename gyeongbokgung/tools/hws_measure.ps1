# 화성의 시각 모델과 콜리전 크기를 정확히 잰다.
#
# 문서(003-hwaseong-v23-import.md)는 둘 다 X 56750..66050 / Z -4800..4800 이라고 적혀 있다.
# 그런데 레벨 실측에서 Place 의 경계상자가 그보다 두 배로 나왔다. 어느 쪽이 맞는지 본다.
#
# ★ 경계상자만 보면 멀리 떨어진 파츠 하나에 속는다. 분포를 같이 본다.
param([string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm")
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"

$text = Read-OvdrText -Path $LevelPath

function Get-Block {
    param([string] $Name)
    $m = [regex]::Match($text, '"Name":\s*"' + [regex]::Escape($Name) + '"')
    if (-not $m.Success) { return $null }
    $i = $m.Index; $d = 0
    while ($i -ge 0) { $c = $text[$i]; if ($c -eq '}') { $d++ } elseif ($c -eq '{') { if ($d -eq 0) { break }; $d-- }; $i-- }
    $j = $i; $d = 0; $s = $false
    while ($j -lt $text.Length) {
        $c = $text[$j]
        if ($s) { if ($c -eq '\') { $j += 2; continue }; if ($c -eq '"') { $s = $false } }
        else { if ($c -eq '"') { $s = $true } elseif ($c -eq '{') { $d++ } elseif ($c -eq '}') { $d--; if ($d -eq 0) { break } } }
        $j++
    }
    return $text.Substring($i, $j - $i + 1)
}

function Measure-Parts {
    param([string] $Blk, [string] $Label)
    # 블록 안의 모든 파츠형 노드의 CFrame.Position 과 Size 를 뽑는다 (깊이 무관)
    # ★ 지수 표기(-3.9e-05)가 섞여 있다. 부호까지 받는 패턴이어야 한다.
    $NUM = '(-?[\d.]+(?:[eE][-+]?\d+)?)'
    $pat = '"InstanceType":\s*"(Part|MeshPart|SpawnLocation)"[\s\S]{0,2500}?"CFrame":\s*\{[\s\S]{0,200}?"Position":\s*\{[^{}]*?"X":\s*' + $NUM + '[^{}]*?"Y":\s*' + $NUM + '[^{}]*?"Z":\s*' + $NUM + '[^{}]*?\}[\s\S]{0,400}?"Size":\s*\{[^{}]*?"X":\s*' + $NUM + '[^{}]*?"Y":\s*' + $NUM + '[^{}]*?"Z":\s*' + $NUM
    $xs = @(); $ys = @(); $zs = @(); $sx = @()
    foreach ($m in [regex]::Matches($Blk, $pat)) {
        $xs += [double]$m.Groups[2].Value
        $ys += [double]$m.Groups[3].Value
        $zs += [double]$m.Groups[4].Value
        $sx += [double]$m.Groups[5].Value
    }
    if ($xs.Count -eq 0) { Write-Host ("{0} : 파츠 0" -f $Label) -ForegroundColor Red; return }

    $sorted = $xs | Sort-Object
    $q = { param($a, $p) $a[[int][Math]::Floor(($a.Count - 1) * $p)] }
    Write-Host ("`n== {0} ==  파츠 {1}" -f $Label, $xs.Count) -ForegroundColor Cyan
    Write-Host ("  경계상자   X {0,9:N0}~{1,-9:N0}  Y {2,8:N0}~{3,-8:N0}  Z {4,9:N0}~{5,-9:N0}" -f `
        ($xs | Measure-Object -Minimum).Minimum, ($xs | Measure-Object -Maximum).Maximum,
        ($ys | Measure-Object -Minimum).Minimum, ($ys | Measure-Object -Maximum).Maximum,
        ($zs | Measure-Object -Minimum).Minimum, ($zs | Measure-Object -Maximum).Maximum)
    $zsort = $zs | Sort-Object
    Write-Host ("  가운데 90%% X {0,9:N0}~{1,-9:N0}                        Z {2,9:N0}~{3,-9:N0}" -f `
        (& $q $sorted 0.05), (& $q $sorted 0.95), (& $q $zsort 0.05), (& $q $zsort 0.95))
    Write-Host ("  파츠 크기  X 중앙값 {0:N1}   최대 {1:N0}" -f `
        (& $q ($sx | Sort-Object) 0.5), ($sx | Measure-Object -Maximum).Maximum)

    # 경계상자 밖으로 튀는 파츠 (가운데 90% 에서 크게 벗어난 것)
    $lo = & $q $sorted 0.05; $hi = & $q $sorted 0.95
    $span = $hi - $lo
    $out = 0
    for ($i = 0; $i -lt $xs.Count; $i++) {
        if ($xs[$i] -lt $lo - $span -or $xs[$i] -gt $hi + $span) { $out++ }
    }
    Write-Host ("  무리에서 멀리 떨어진 파츠 : {0} 개" -f $out)
}

foreach ($n in 'Hwaseong Place', 'Hwaseong Collision') {
    $b = Get-Block -Name $n
    if ($b) { Measure-Parts -Blk $b -Label $n } else { Write-Host "$n 을 못 찾았다" -ForegroundColor Red }
}

Write-Host "`n문서 003 기준 : 시각·콜리전 둘 다 X 56750~66050 / Z -4800~4800 (0.25배 빌드)" -ForegroundColor Yellow
