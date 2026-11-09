# KRM_Palace 안의 인스턴스를 종류별로 훑는다.
#
# 「셸이 또 안 보인다」를 진단할 때 쓴다. 눈으로 안 보이는 이유는 셋 중 하나다 :
#   1) 노드가 아예 없다
#   2) MeshId 가 비었다 (임포트 에셋 참조가 깨졌다)
#   3) Size / Transparency 가 이상하다
# 어느 쪽인지 숫자로 먼저 가른다.
param([string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm")
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"

$text = Read-OvdrText -Path $LevelPath

# KRM_Palace 블록만 잘라 낸다
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
Write-Host ("KRM_Palace 블록 {0} chars" -f $blk.Length) -ForegroundColor Cyan

# 자식 노드를 하나씩 뜯어 본다 (깊이 1)
$lc = $blk.IndexOf('"LuaChildren"')
$arr = $blk.IndexOf('[', $lc)
$k = $arr + 1; $d = 0; $s = $false; $start = -1
$rows = @()
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
                $nm = [regex]::Match($ch, '"Name":\s*"([^"]+)"')
                $ty = [regex]::Match($ch, '"InstanceType":\s*"([^"]+)"')
                $mi = [regex]::Match($ch, '"MeshId":\s*"([^"]*)"')
                $ti = [regex]::Match($ch, '"TextureId":\s*"([^"]*)"')
                $tr = [regex]::Match($ch, '"Transparency":\s*([\d.]+)')
                $sz = [regex]::Match($ch, '"Size":\s*\{[^{}]*?"X":\s*(-?[\d.]+)[^{}]*?"Y":\s*(-?[\d.]+)[^{}]*?"Z":\s*(-?[\d.]+)')
                $rows += [pscustomobject]@{
                    Name = $(if ($nm.Success) { $nm.Groups[1].Value } else { '?' })
                    Type = $(if ($ty.Success) { $ty.Groups[1].Value } else { '?' })
                    Mesh = $(if ($mi.Success) { $mi.Groups[1].Value } else { '' })
                    Tex  = $(if ($ti.Success) { $ti.Groups[1].Value } else { '' })
                    Tsp  = $(if ($tr.Success) { [double]$tr.Groups[1].Value } else { -1 })
                    SX   = $(if ($sz.Success) { [double]$sz.Groups[1].Value } else { 0 })
                    SY   = $(if ($sz.Success) { [double]$sz.Groups[2].Value } else { 0 })
                    SZ   = $(if ($sz.Success) { [double]$sz.Groups[3].Value } else { 0 })
                }
                $start = -1
            }
        }
        elseif ($c -eq ']' -and $d -eq 0) { break }
    }
    $k++
}

Write-Host ("`n자식 {0} 개" -f $rows.Count) -ForegroundColor Cyan
$rows | Group-Object Type | Sort-Object Count -Descending |
    ForEach-Object { "  {0,-16} {1}" -f $_.Name, $_.Count }

$meshes = @($rows | Where-Object { $_.Type -eq 'MeshPart' })
$noMesh = @($meshes | Where-Object { -not $_.Mesh })
$noTex  = @($meshes | Where-Object { -not $_.Tex })
Write-Host ("`nMeshPart {0}   MeshId 빈 것 {1}   TextureId 빈 것 {2}" -f $meshes.Count, $noMesh.Count, $noTex.Count)
if ($noMesh.Count) { $noMesh | Select-Object -First 10 | ForEach-Object { "   MeshId 없음: " + $_.Name } }

# 이름 접두어별로 Size 범위를 본다. 셸(SHELL)과 소품(PROP)을 갈라 본다.
Write-Host "`n접두어별 Size 범위 (Size 는 배율이다. 100 = 원본 메시 크기)" -ForegroundColor Cyan
$rows | Where-Object { $_.Type -eq 'MeshPart' } |
    Group-Object { ($_.Name -split '_')[0..2] -join '_' } |
    Sort-Object Name |
    ForEach-Object {
        $g = $_.Group
        "  {0,-30} {1,4}개   SX {2,8:N1}~{3,-8:N1} SY {4,8:N1}~{5,-8:N1} 투명 {6}" -f `
            $_.Name, $g.Count,
            ($g | Measure-Object SX -Minimum).Minimum, ($g | Measure-Object SX -Maximum).Maximum,
            ($g | Measure-Object SY -Minimum).Minimum, ($g | Measure-Object SY -Maximum).Maximum,
            (($g | Select-Object -ExpandProperty Tsp -Unique) -join ',')
    }

Write-Host "`n표본 5개" -ForegroundColor Cyan
$rows | Where-Object { $_.Type -eq 'MeshPart' } | Select-Object -First 5 |
    ForEach-Object { "  {0,-34} Size({1},{2},{3})  Mesh={4}" -f $_.Name, $_.SX, $_.SY, $_.SZ, $_.Mesh }
