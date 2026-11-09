# KRM_Palace MeshPart 의 DoubleSided / CastShadow / Material 을 본다.
#
# 가설 : 셸은 속이 빈 실내 면이라 법선이 안쪽을 본다.
#        DoubleSided 가 false 면 밖에서 볼 때 백페이스 컬링으로 통째로 사라진다.
#        소품은 닫힌 덩어리라 어느 쪽에서 봐도 보인다 -- 관측과 정확히 맞는다.
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
                $nm = [regex]::Match($ch, '"InstanceType":\s*"(MeshPart)"[\s\S]{0,400}?"Name":\s*"([^"]+)"')
                if ($nm.Success) {
                    $ds = [regex]::Match($ch, '"DoubleSided":\s*(true|false)')
                    $cs = [regex]::Match($ch, '"CastShadow":\s*(true|false)')
                    $mt = [regex]::Match($ch, '"Material":\s*"([^"]+)"')
                    $rows += [pscustomobject]@{
                        Name = $nm.Groups[2].Value
                        DS   = $(if ($ds.Success) { $ds.Groups[1].Value } else { '(속성없음)' })
                        CS   = $(if ($cs.Success) { $cs.Groups[1].Value } else { '(없음)' })
                        Mat  = $(if ($mt.Success) { $mt.Groups[1].Value } else { '(없음)' })
                        Kind = $(if ($nm.Groups[2].Value -like 'KRMM_KRM_PROP*') { '소품' } else { '셸' })
                    }
                }
                $start = -1
            }
        }
        elseif ($c -eq ']' -and $d -eq 0) { break }
    }
    $k++
}

Write-Host ("MeshPart {0} 개`n" -f $rows.Count) -ForegroundColor Cyan
$rows | Group-Object Kind, DS, Mat | Sort-Object Name |
    ForEach-Object { "  {0,-40} {1}개" -f $_.Name, $_.Count }

Write-Host "`n== 셸 하나하나 ==" -ForegroundColor Cyan
$rows | Where-Object { $_.Kind -eq '셸' } | Sort-Object Name |
    ForEach-Object { "  {0,-34} DoubleSided={1,-11} CastShadow={2,-6} Material={3}" -f $_.Name, $_.DS, $_.CS, $_.Mat }

Write-Host "`n== 소품 표본 4 ==" -ForegroundColor Cyan
$rows | Where-Object { $_.Kind -eq '소품' } | Select-Object -First 4 |
    ForEach-Object { "  {0,-34} DoubleSided={1,-11} CastShadow={2,-6} Material={3}" -f $_.Name, $_.DS, $_.CS, $_.Mat }
