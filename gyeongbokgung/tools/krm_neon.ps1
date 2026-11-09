# 특정 MeshPart 의 Material/Color/Size 를 바꿔 렌더 여부를 가린다.
param(
    [string] $Name = 'KRMM_KRM_SHELL_GRA_Room',
    [string] $Material = 'Neon',
    [int] $R = 60, [int] $G = 255, [int] $B = 90,
    [double] $Size = -1,
    [switch] $Apply
)
$ErrorActionPreference='Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"; . "$PSScriptRoot\ovdr_level.ps1"; . "$PSScriptRoot\ovdr_script.ps1"
$t = Read-OvdrText
$pat = '"Name":\s*"' + [regex]::Escape($Name) + '"'
$m = [regex]::Match($t, $pat)
if (-not $m.Success) { throw "$Name 못 찾음" }
$start = $t.LastIndexOf('{', $m.Index)
$depth=0; $end=-1
for ($i=$start; $i -lt $t.Length; $i++) {
    if ($t[$i] -eq '{') { $depth++ } elseif ($t[$i] -eq '}') { $depth--; if ($depth -eq 0) { $end=$i; break } }
}
$blk = $t.Substring($start, $end-$start+1)
$new = $blk
$new = [regex]::Replace($new, '"Material":\s*"[^"]*"', '"Material": "' + $Material + '"')
$new = [regex]::Replace($new, '"Color":\s*\{[^}]*\}', '"Color": { "ObjectType": "Color3", "R": ' + $R + ', "G": ' + $G + ', "B": ' + $B + ' }')
if ($Size -gt 0) {
    $new = [regex]::Replace($new, '"Size":\s*\{[^}]*\}', '"Size": { "ObjectType": "Vector3", "X": ' + $Size + ', "Y": ' + $Size + ', "Z": ' + $Size + ' }')
}
$t = $t.Substring(0,$start) + $new + $t.Substring($end+1)
$null = $t | ConvertFrom-Json
Write-OvdrText -Text $t
Write-Host ("{0} -> Material {1}, Color ({2},{3},{4}){5}" -f $Name, $Material, $R,$G,$B, $(if($Size -gt 0){", Size $Size"}else{""})) -ForegroundColor Green
if ($Apply) { Publish-OvdrLevel }
