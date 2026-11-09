# KRM_Palace 의 콜리전 파츠를 JSON 으로 뽑는다. 새는 곳 검사(krm_leak.js)의 입력이다.
param(
    [string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm",
    [string] $Out = "$PSScriptRoot\kremlin\KRM_work\krm_collision.json"
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
                $nm = [regex]::Match($ch, '"InstanceType":\s*"(Part|SpawnLocation)"[\s\S]{0,400}?"Name":\s*"([^"]+)"')
                if ($nm.Success) {
                    $cf = [regex]::Match($ch, '"CFrame":\s*\{[\s\S]{0,200}?"Position":\s*\{[^{}]*?"X":\s*(-?[\d.eE+]+)[^{}]*?"Y":\s*(-?[\d.eE+]+)[^{}]*?"Z":\s*(-?[\d.eE+]+)[^{}]*?\}[\s\S]{0,80}?"Orientation":\s*\{[^{}]*?"X":\s*(-?[\d.eE+]+)[^{}]*?"Y":\s*(-?[\d.eE+]+)[^{}]*?"Z":\s*(-?[\d.eE+]+)')
                    $sz = [regex]::Match($ch, '"Size":\s*\{[^{}]*?"X":\s*(-?[\d.eE+]+)[^{}]*?"Y":\s*(-?[\d.eE+]+)[^{}]*?"Z":\s*(-?[\d.eE+]+)')
                    $cc = [regex]::Match($ch, '"CanCollide":\s*(true|false)')
                    if ($cf.Success -and $sz.Success) {
                        $rows += [ordered]@{
                            name = $nm.Groups[2].Value
                            x = [double]$cf.Groups[1].Value; y = [double]$cf.Groups[2].Value; z = [double]$cf.Groups[3].Value
                            pitch = [double]$cf.Groups[4].Value; yaw = [double]$cf.Groups[5].Value; roll = [double]$cf.Groups[6].Value
                            sx = [double]$sz.Groups[1].Value; sy = [double]$sz.Groups[2].Value; sz = [double]$sz.Groups[3].Value
                            collide = ($cc.Success -and $cc.Groups[1].Value -eq 'true')
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

New-Item -ItemType Directory -Force -Path (Split-Path $Out) | Out-Null
($rows | ConvertTo-Json -Depth 4) | Set-Content -Path $Out -Encoding UTF8
Write-Host ("{0} 개 -> {1}" -f $rows.Count, $Out) -ForegroundColor Green
$rows | Group-Object { if ($_.name -like 'KRM_COL*' -or $_.name -like 'KRM_Corridor*') { '콜리전' } else { '기타' } } |
    ForEach-Object { "  {0} : {1}" -f $_.Name, $_.Count }
