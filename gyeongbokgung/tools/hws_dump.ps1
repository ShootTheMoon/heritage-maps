# Dump the level's Hwaseong Place MeshParts to JSON for comparison against the
# original import placement (ovdr_export/hwaseong_v23/placement_*.json).
param(
    [string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm",
    [string] $Out = "$PSScriptRoot\kremlin\KRM_work\hws_level.json"
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"

$NUM = '(-?[\d.]+(?:[eE][-+]?\d+)?)'
$text = Read-OvdrText -Path $LevelPath

$m = [regex]::Match($text, '"Name":\s*"Hwaseong Place"')
if (-not $m.Success) { throw "Hwaseong Place not found" }
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

$rows = @()
foreach ($mm in [regex]::Matches($blk, '"InstanceType":\s*"MeshPart"')) {
    $ns = Node-Span -Txt $blk -At $mm.Index
    if ($null -eq $ns) { continue }
    $ch = $blk.Substring($ns.Start, $ns.End - $ns.Start + 1)
    $nm = [regex]::Match($ch, '"Name":\s*"([^"]+)"')
    $cf = [regex]::Match($ch, '"CFrame":\s*\{[\s\S]{0,200}?"Position":\s*\{[^{}]*?"X":\s*' + $NUM + '[^{}]*?"Y":\s*' + $NUM + '[^{}]*?"Z":\s*' + $NUM)
    $sz = [regex]::Match($ch, '"Size":\s*\{[^{}]*?"X":\s*' + $NUM + '[^{}]*?"Y":\s*' + $NUM + '[^{}]*?"Z":\s*' + $NUM)
    $mi = [regex]::Match($ch, '"MeshId":\s*"([^"]*)"')
    if (-not ($nm.Success -and $cf.Success -and $sz.Success)) { continue }
    $rows += [ordered]@{
        name = $nm.Groups[1].Value
        x = [double]$cf.Groups[1].Value; y = [double]$cf.Groups[2].Value; z = [double]$cf.Groups[3].Value
        sx = [double]$sz.Groups[1].Value; sy = [double]$sz.Groups[2].Value; sz = [double]$sz.Groups[3].Value
        meshId = $(if ($mi.Success) { $mi.Groups[1].Value } else { '' })
    }
}
New-Item -ItemType Directory -Force -Path (Split-Path $Out) | Out-Null
($rows | ConvertTo-Json -Depth 4) | Set-Content -Path $Out -Encoding UTF8
Write-Host ("{0} MeshParts -> {1}" -f $rows.Count, $Out) -ForegroundColor Green
