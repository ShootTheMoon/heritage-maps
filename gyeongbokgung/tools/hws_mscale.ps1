# Set WorldTransform.Scale on Hwaseong Place and all its child Models.
#
# Why: MeshPart "Size" does not survive a Studio save for MODEL-imported parts --
# Studio recomputes it from the published mesh. Measured 2026-08-27:
#   after scaling Size x2 and publishing, B_CastleWall Size went back to 2059.5.
# CFrame.Position DOES survive (bbox stayed doubled), and plain Part Size survives.
# So the only remaining lever for visual size is the Model transform.
#
#   .\hws_mscale.ps1 -Scale 2            preview
#   .\hws_mscale.ps1 -Scale 2 -Apply
#   .\hws_mscale.ps1 -Scale 1 -Apply     revert
param(
    [Parameter(Mandatory)][double] $Scale,
    [string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm",
    [switch] $Apply
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"
. "$PSScriptRoot\ovdr_script.ps1"

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
$a = $i; $b = $j
$blk = $text.Substring($a, $b - $a + 1)

$NUM = '(-?[\d.]+(?:[eE][-+]?\d+)?)'
$pat = '("WorldTransform":\s*\{[\s\S]{0,900}?"Scale":\s*\{[^{}]*?"X":\s*)' + $NUM + '([^{}]*?"Y":\s*)' + $NUM + '([^{}]*?"Z":\s*)' + $NUM
$n = 0
$new = [regex]::Replace($blk, $pat, {
    param($mm)
    $script:n++
    $mm.Groups[1].Value + ('{0:0.####}' -f $Scale) + $mm.Groups[3].Value + ('{0:0.####}' -f $Scale) + $mm.Groups[5].Value + ('{0:0.####}' -f $Scale)
})

Write-Host ("WorldTransform.Scale set to {0} on {1} Model nodes" -f $Scale, $n) -ForegroundColor Cyan
if ($n -eq 0) { Write-Host "nothing changed"; return }

$out = $text.Substring(0, $a) + $new + $text.Substring($b + 1)
$null = $out | ConvertFrom-Json

if (-not $Apply) { Write-Host "preview only. add -Apply" -ForegroundColor Yellow; return }
$null = Backup-OvdrLevel -Path $LevelPath -Tag ("hws_mscale_" + ($Scale -replace '\.', 'p'))
Write-OvdrText -Text $out -Path $LevelPath
$null = Invoke-OvdrRpc -Method 'game.stop' -TimeoutSec 30
Publish-OvdrLevel
