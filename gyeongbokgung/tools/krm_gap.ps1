# 크렘린 콜리전의 빈 곳을 찾는다.
#
# KRM_COL_* 슬래브를 전부 읽어 XZ 격자에 투영하고, 방 경계선을 따라
# "콜리전이 없는 구간" 을 뽑는다. 그게 플레이어가 빠져나가는 구멍이다.
#
# ★ 셸 메시에는 콜리전이 없다. KRM_COL_* 164장이 유일한 벽이다.
param(
    [string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm",
    [switch] $Detail
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"

$text = Read-OvdrText -Path $LevelPath
$m = [regex]::Match($text, '"Name":\s*"KRM_Palace"')
if (-not $m.Success) { throw "KRM_Palace 를 못 찾았다" }
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

# 자식 파츠를 훑는다
$lc = $blk.IndexOf('"LuaChildren"'); $arr = $blk.IndexOf('[', $lc)
$k = $arr + 1; $d = 0; $s = $false; $start = -1; $rows = @()
while ($k -lt $blk.Length) {
    $c = $blk[$k]
    if ($s) { if ($c -eq '\') { $k += 2; continue }; if ($c -eq '"') { $s = $false } }
    else {
        if ($c -eq '"') { $s = $true }
        elseif ($c -eq '{') { if ($d -eq 0) { $start = $k }; $d++ }
        elseif ($c -eq '}') {
            $d--
            if ($d -eq 0 -and $start -ge 0) {
                $ch = $blk.Substring($start, $k - $start + 1)
                $nm = [regex]::Match($ch, '"InstanceType":\s*"(Part)"[\s\S]{0,400}?"Name":\s*"([^"]+)"')
                if ($nm.Success) {
                    $cf = [regex]::Match($ch, '"CFrame":\s*\{[\s\S]{0,200}?"Position":\s*\{[^{}]*?"X":\s*(-?[\d.eE+]+)[^{}]*?"Y":\s*(-?[\d.eE+]+)[^{}]*?"Z":\s*(-?[\d.eE+]+)[^{}]*?\}[\s\S]{0,80}?"Orientation":\s*\{[^{}]*?"X":\s*(-?[\d.eE+]+)[^{}]*?"Y":\s*(-?[\d.eE+]+)[^{}]*?"Z":\s*(-?[\d.eE+]+)')
                    $sz = [regex]::Match($ch, '"Size":\s*\{[^{}]*?"X":\s*(-?[\d.eE+]+)[^{}]*?"Y":\s*(-?[\d.eE+]+)[^{}]*?"Z":\s*(-?[\d.eE+]+)')
                    $cc = [regex]::Match($ch, '"CanCollide":\s*(true|false)')
                    if ($cf.Success -and $sz.Success) {
                        $rows += [pscustomobject]@{
                            Name = $nm.Groups[2].Value
                            X = [double]$cf.Groups[1].Value; Y = [double]$cf.Groups[2].Value; Z = [double]$cf.Groups[3].Value
                            OY = [double]$cf.Groups[5].Value
                            SX = [double]$sz.Groups[1].Value; SY = [double]$sz.Groups[2].Value; SZ = [double]$sz.Groups[3].Value
                            CC = ($cc.Success -and $cc.Groups[1].Value -eq 'true')
                        }
                    }
                }
                $start = -1
            }
        }
        elseif ($c -eq ']' -and $d -eq 0) { break }
    }
    $k++
}

$col = @($rows | Where-Object { $_.Name -like 'KRM_COL*' -or $_.Name -like 'KRM_Corridor*' })
Write-Host ("콜리전 파츠 {0} 개 (충돌 켜진 것 {1})" -f $col.Count, @($col | Where-Object { $_.CC }).Count) -ForegroundColor Cyan

# 종류별
$col | Group-Object { ($_.Name -replace '_\d+$','') -replace '^KRM_COL_','' } | Sort-Object Name |
    ForEach-Object { "  {0,-24} {1,3}개" -f $_.Name, $_.Count }

# 기울어진 것 (경사 슬래브) 은 따로 센다
$tilt = @($col | Where-Object { [Math]::Abs($_.OY) -gt 0.5 })
Write-Host ("`nyaw 가 0 이 아닌 슬래브 : {0} 개" -f $tilt.Count)

# 수직 벽으로 볼 수 있는 것 : 얇은 축이 수평이고 높이가 200 이상
$walls = @($col | Where-Object { $_.SY -ge 200 -and ([Math]::Min($_.SX, $_.SZ) -le 120) })
$floors = @($col | Where-Object { $_.SY -lt 200 })
Write-Host ("벽 슬래브(높이>=200, 얇은축<=120) {0} 개 / 바닥·천장 {1} 개" -f $walls.Count, $floors.Count)

Write-Host "`n== 벽 슬래브의 윗면 높이 분포 ==" -ForegroundColor Cyan
$walls | Group-Object { [Math]::Round($_.Y + $_.SY / 2) } | Sort-Object { [int]$_.Name } |
    ForEach-Object { "  윗면 Y {0,6}  {1,3}개" -f $_.Name, $_.Count }

Write-Host "`n== 방별 XZ 범위 ==" -ForegroundColor Cyan
$col | Group-Object { if ($_.Name -match 'KRM_COL_([a-z]+)_') { $Matches[1] } else { 'other' } } | Sort-Object Name |
    ForEach-Object {
        $g = $_.Group
        "  {0,-10} {1,3}개  X {2,7:N0}~{3,-7:N0} Y {4,6:N0}~{5,-6:N0} Z {6,7:N0}~{7,-7:N0}" -f `
            $_.Name, $g.Count,
            ($g | ForEach-Object { $_.X - $_.SX/2 } | Measure-Object -Minimum).Minimum,
            ($g | ForEach-Object { $_.X + $_.SX/2 } | Measure-Object -Maximum).Maximum,
            ($g | ForEach-Object { $_.Y - $_.SY/2 } | Measure-Object -Minimum).Minimum,
            ($g | ForEach-Object { $_.Y + $_.SY/2 } | Measure-Object -Maximum).Maximum,
            ($g | ForEach-Object { $_.Z - $_.SZ/2 } | Measure-Object -Minimum).Minimum,
            ($g | ForEach-Object { $_.Z + $_.SZ/2 } | Measure-Object -Maximum).Maximum
    }

if ($Detail) {
    Write-Host "`n== 벽 슬래브 전체 ==" -ForegroundColor Cyan
    $walls | Sort-Object Name | ForEach-Object {
        "  {0,-26} P=({1,7:N0},{2,6:N0},{3,7:N0})  S=({4,6:N0},{5,5:N0},{6,6:N0})  yaw {7,5:N1}  윗면 {8,5:N0}" -f `
            $_.Name, $_.X, $_.Y, $_.Z, $_.SX, $_.SY, $_.SZ, $_.OY, ($_.Y + $_.SY/2)
    }
}
