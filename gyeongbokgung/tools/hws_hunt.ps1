# Hunt every backup for the original (pre-50%) Hwaseong building size.
#
# Discriminator: B_CastleWall's Size.X .
# Studio recomputes MeshPart Size from the published MODEL on every save, so this value
# reflects the true build scale and cannot be faked by a level edit.
# If an older backup shows a bigger value, the original build is recoverable without
# re-importing anything.
param()
$ErrorActionPreference = 'SilentlyContinue'
$NUM = '(-?[\d.]+(?:[eE][-+]?\d+)?)'

$files = @()
Get-ChildItem "$env:USERPROFILE\Desktop\ovdr_backup" -Directory | Sort-Object Name | ForEach-Object {
    $p = Join-Path $_.FullName 'onlyoneshot.ovdrjm'
    if (Test-Path $p) { $files += [pscustomobject]@{ Tag = $_.Name; Path = $p } }
}
Get-ChildItem "$env:USERPROFILE\Desktop\onlyoneshot" -Filter '*.ovdrjm*' | Sort-Object Name | ForEach-Object {
    $files += [pscustomobject]@{ Tag = $_.Name; Path = $_.FullName }
}

foreach ($f in $files) {
    $txt = [IO.File]::ReadAllText($f.Path, [Text.Encoding]::Unicode)
    if (-not $txt -or $txt.Length -lt 1000) { continue }
    $wall = [regex]::Match($txt, '"Name":\s*"B_CastleWall[^"]*"[\s\S]{0,2500}?"Size":\s*\{[^{}]*?"X":\s*' + $NUM)
    $sc   = [regex]::Match($txt, '"Name":\s*"Hwaseong Place"[\s\S]{0,900}?"Scale":\s*\{[^{}]*?"X":\s*' + $NUM)
    $has  = ([regex]::Matches($txt, '"Name":\s*"Hwaseong Place"')).Count
    "{0,-50} place={1} wallSizeX={2,-10} modelScaleX={3}" -f `
        $f.Tag, $has,
        $(if ($wall.Success) { [Math]::Round([double]$wall.Groups[1].Value, 1) } else { '-' }),
        $(if ($sc.Success) { $sc.Groups[1].Value } else { '-' })
}
