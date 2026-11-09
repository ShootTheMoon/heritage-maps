$root = "$env:USERPROFILE\Desktop\ovdr_backup"
$dirs = Get-ChildItem $root -Directory | Sort-Object Name
foreach ($d in $dirs) {
    $f = Join-Path $d.FullName 'onlyoneshot.ovdrjm'
    if (-not (Test-Path $f)) { continue }
    $txt = [IO.File]::ReadAllText($f, [Text.Encoding]::Unicode)
    $br = ([regex]::Matches($txt, '"Name":\s*"KRM_CorridorBridge')).Count
    $col = ([regex]::Matches($txt, '"Name":\s*"KRM_COL_')).Count
    $mm = ([regex]::Matches($txt, '"Name":\s*"KRMM_')).Count
    "{0,-46} bridge={1,2}  COL={2,4}  KRMM={3,4}" -f $d.Name, $br, $col, $mm
}
