# KRM_Palace 자식들의 위치·회전을 종류별로 본다.
#
# 「소품은 보이는데 셸이 안 보인다」면 셸이 엉뚱한 자리/크기일 수 있다.
# 소품(보임)과 셸(안 보임)을 나란히 놓고 비교한다.
#
# ★ 정규식으로 "Name" 을 잡으면 BrickColor 안의 "Name" 에 걸린다 (실제로 당했다).
#   자식 블록을 중괄호 균형으로 잘라 낸 뒤 그 안에서만 읽는다.
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
                # 노드 자신의 Name = InstanceType 바로 뒤에 오는 첫 Name (BrickColor 보다 앞이다)
                $nm = [regex]::Match($ch, '"InstanceType":\s*"([^"]+)"[\s\S]{0,400}?"Name":\s*"([^"]+)"')
                $cf = [regex]::Match($ch, '"CFrame":\s*\{[\s\S]{0,200}?"Position":\s*\{[^{}]*?"X":\s*(-?[\d.eE+]+)[^{}]*?"Y":\s*(-?[\d.eE+]+)[^{}]*?"Z":\s*(-?[\d.eE+]+)[^{}]*?\}[\s\S]{0,80}?"Orientation":\s*\{[^{}]*?"X":\s*(-?[\d.eE+]+)[^{}]*?"Y":\s*(-?[\d.eE+]+)[^{}]*?"Z":\s*(-?[\d.eE+]+)')
                if ($nm.Success -and $cf.Success) {
                    $n = $nm.Groups[2].Value
                    $kind =
                        if ($n -like 'KRMM_KRM_PROP*') { '소품(보임)' }
                        elseif ($n -like 'KRMM_*')     { '셸(안보임)' }
                        elseif ($n -like 'KRM_COL*')   { '콜리전' }
                        elseif ($n -like 'KRM_Bound*') { '경기구역벽' }
                        elseif ($n -like 'KRM_Spawn*') { '스폰' }
                        else { '기타' }
                    $rows += [pscustomobject]@{
                        Name = $n; Kind = $kind; Type = $nm.Groups[1].Value
                        X = [double]$cf.Groups[1].Value; Y = [double]$cf.Groups[2].Value; Z = [double]$cf.Groups[3].Value
                        OX = [double]$cf.Groups[4].Value; OY = [double]$cf.Groups[5].Value; OZ = [double]$cf.Groups[6].Value
                    }
                }
                $start = -1
            }
        }
        elseif ($c -eq ']' -and $d -eq 0) { break }
    }
    $k++
}
Write-Host ("위치를 읽은 자식 {0} 개`n" -f $rows.Count)

$rows | Group-Object Kind | Sort-Object Name | ForEach-Object {
    $g = $_.Group
    "  {0,-12} {1,4}개   X {2,9:N0}~{3,-9:N0} Y {4,7:N0}~{5,-7:N0} Z {6,8:N0}~{7,-8:N0}" -f `
        $_.Name, $g.Count,
        ($g | Measure-Object X -Minimum).Minimum, ($g | Measure-Object X -Maximum).Maximum,
        ($g | Measure-Object Y -Minimum).Minimum, ($g | Measure-Object Y -Maximum).Maximum,
        ($g | Measure-Object Z -Minimum).Minimum, ($g | Measure-Object Z -Maximum).Maximum
}

Write-Host "`n== 셸 하나하나 ==" -ForegroundColor Cyan
$rows | Where-Object { $_.Kind -eq '셸(안보임)' } | Sort-Object Name | ForEach-Object {
    "  {0,-34} P=({1,8:N0}, {2,6:N0}, {3,6:N0})  yaw {4,6:N1}  pitch {5,5:N1} roll {6,5:N1}" -f `
        $_.Name, $_.X, $_.Y, $_.Z, $_.OY, $_.OX, $_.OZ
}

Write-Host "`n== 소품 표본 6개 (비교군 - 화면에 보인다) ==" -ForegroundColor Cyan
$rows | Where-Object { $_.Kind -eq '소품(보임)' } | Select-Object -First 6 | ForEach-Object {
    "  {0,-34} P=({1,8:N0}, {2,6:N0}, {3,6:N0})  yaw {4,6:N1}" -f $_.Name, $_.X, $_.Y, $_.Z, $_.OY
}
