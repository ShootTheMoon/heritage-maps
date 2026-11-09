# KRM_Palace 의 Part(콜리전) 들이 투명한지 본다.
#
# 가설 : 콜리전 슬래브가 불투명하면 셸을 통째로 가린다.
#        편집기 화면의 「커다란 평평한 판」이 사실 콜리전일 수 있다.
param([string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm")
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"

$text = Read-OvdrText -Path $LevelPath
$m = [regex]::Match($text, '"Name":\s*"KRM_Palace"')
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
                $nm = [regex]::Match($ch, '"InstanceType":\s*"([^"]+)"[\s\S]{0,400}?"Name":\s*"([^"]+)"')
                if ($nm.Success) {
                    $tr = [regex]::Match($ch, '"Transparency":\s*([\d.]+)')
                    $cc = [regex]::Match($ch, '"CanCollide":\s*(true|false)')
                    $sz = [regex]::Match($ch, '"Size":\s*\{[^{}]*?"X":\s*(-?[\d.]+)[^{}]*?"Y":\s*(-?[\d.]+)[^{}]*?"Z":\s*(-?[\d.]+)')
                    $rows += [pscustomobject]@{
                        Name = $nm.Groups[2].Value; Type = $nm.Groups[1].Value
                        Tsp = $(if ($tr.Success) { [double]$tr.Groups[1].Value } else { -1 })
                        CC  = $(if ($cc.Success) { $cc.Groups[1].Value } else { '?' })
                        SX  = $(if ($sz.Success) { [double]$sz.Groups[1].Value } else { 0 })
                        SY  = $(if ($sz.Success) { [double]$sz.Groups[2].Value } else { 0 })
                        SZ  = $(if ($sz.Success) { [double]$sz.Groups[3].Value } else { 0 })
                    }
                }
                $start = -1
            }
        }
        elseif ($c -eq ']' -and $d -eq 0) { break }
    }
    $k++
}

Write-Host ("자식 {0} 개`n" -f $rows.Count) -ForegroundColor Cyan
$rows | Group-Object Type, Tsp, CC | Sort-Object Name |
    ForEach-Object { "  {0,-34} {1,4}개" -f $_.Name, $_.Count }

Write-Host "`n== 가장 큰 Part 10개 ==" -ForegroundColor Cyan
$rows | Where-Object { $_.Type -eq 'Part' } |
    Sort-Object { $_.SX * $_.SZ } -Descending | Select-Object -First 10 |
    ForEach-Object { "  {0,-26} Size({1,7:N0} x {2,6:N0} x {3,7:N0})  투명={4}  충돌={5}" -f $_.Name, $_.SX, $_.SY, $_.SZ, $_.Tsp, $_.CC }
