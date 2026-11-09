# Lighting / Atmosphere 현재값을 레벨에서 읽는다. 맵별 프리셋의 기준선이 된다.
param([string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm")
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"
$text = Read-OvdrText -Path $LevelPath
foreach ($t in 'Lighting','Atmosphere') {
    $m = [regex]::Match($text, '"InstanceType":\s*"' + $t + '"')
    if (-not $m.Success) { Write-Host "$t NOT FOUND" -ForegroundColor Red; continue }
    $i = $m.Index; $d = 0
    while ($i -ge 0) { $c=$text[$i]; if ($c -eq '}'){$d++} elseif ($c -eq '{'){ if($d -eq 0){break}; $d-- }; $i-- }
    $j=$i; $d=0; $s=$false
    while ($j -lt $text.Length) {
        $c=$text[$j]
        if ($s) { if ($c -eq '\'){$j+=2;continue}; if ($c -eq '"'){$s=$false} }
        else { if ($c -eq '"'){$s=$true} elseif ($c -eq '{'){$d++} elseif ($c -eq '}'){$d--; if($d -eq 0){break}} }
        $j++
    }
    $b = $text.Substring($i, $j-$i+1)
    Write-Host "`n== $t ==" -ForegroundColor Cyan
    foreach ($mm in [regex]::Matches($b, '"([A-Za-z][A-Za-z0-9_]*)":\s*(-?[\d.]+|true|false|"[^"]*")')) {
        "  {0,-28} {1}" -f $mm.Groups[1].Value, $mm.Groups[2].Value
    }
    foreach ($mm in [regex]::Matches($b, '"([A-Za-z][A-Za-z0-9_]*)":\s*\{\s*"ObjectType":\s*"Color3",\s*"R":\s*(\d+),\s*"G":\s*(\d+),\s*"B":\s*(\d+)')) {
        "  {0,-28} ({1}, {2}, {3})" -f $mm.Groups[1].Value, $mm.Groups[2].Value, $mm.Groups[3].Value, $mm.Groups[4].Value
    }
}
