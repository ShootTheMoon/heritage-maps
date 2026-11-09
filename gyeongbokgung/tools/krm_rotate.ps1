# KRM 셸 MeshPart 를 제자리에서 회전시킨다 (소품 제외).
#   .\krm_rotate.ps1 -Deg 180 -Apply      # 180도 얹기
#   .\krm_rotate.ps1 -Deg -180 -Apply     # 되돌리기
#   .\krm_rotate.ps1 -Deg 180 -IncludeProps -Apply
param(
    [double] $Deg = 180,
    [switch] $IncludeProps,
    [switch] $Apply,
    [string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm"
)
$ErrorActionPreference='Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"; . "$PSScriptRoot\ovdr_level.ps1"; . "$PSScriptRoot\ovdr_script.ps1"
$t = Read-OvdrText -Path $LevelPath
$rx = [regex]'"Name":\s*"(KRMM_[^"]*)"'
$ms = @($rx.Matches($t)) 
[array]::Reverse($ms)
$n = 0
foreach ($m in $ms) {
    $nm = $m.Groups[1].Value
    if (-not $IncludeProps -and $nm -like '*KRM_PROP*') { continue }
    $start = $t.LastIndexOf('{', $m.Index)
    $d = 0; $end = -1
    for ($i = $start; $i -lt $t.Length; $i++) {
        if ($t[$i] -eq '{') { $d++ } elseif ($t[$i] -eq '}') { $d--; if ($d -eq 0) { $end = $i; break } }
    }
    $blk = $t.Substring($start, $end - $start + 1)
    $om = [regex]::Match($blk, '"Orientation":\s*\{[^}]*?"X":\s*(-?[\d.eE+]+),\s*"Y":\s*(-?[\d.eE+]+),\s*"Z":\s*(-?[\d.eE+]+)[^}]*\}')
    if (-not $om.Success) { continue }
    $ox = [double]$om.Groups[1].Value
    $oy = [double]$om.Groups[2].Value
    $oz = [double]$om.Groups[3].Value
    $ny = [math]::Round((($oy + $Deg) % 360 + 360) % 360, 3)
    if ($ny -gt 180) { $ny = $ny - 360 }
    $newOri = '"Orientation": { "ObjectType": "Vector3", "X": ' + $ox + ', "Y": ' + $ny + ', "Z": ' + $oz + ' }'
    $blk2 = $blk.Substring(0, $om.Index) + $newOri + $blk.Substring($om.Index + $om.Length)
    $t = $t.Substring(0, $start) + $blk2 + $t.Substring($end + 1)
    $n++
}
$null = $t | ConvertFrom-Json
$null = Backup-OvdrLevel -Path $LevelPath -Tag 'BEFORE_ROTATE'
Write-OvdrText -Text $t -Path $LevelPath
Write-Host ("MeshPart {0}개에 yaw {1}도 적용 (소품 {2})" -f $n, $Deg, $(if($IncludeProps){'포함'}else{'제외'})) -ForegroundColor Green
if ($Apply) { Publish-OvdrLevel }
