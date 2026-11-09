# KRM_Palace 를 처음부터 다시 짓는다.
#
#   placement.json 은 전부 블렌더 좌표(cm)다. 엔진 변환 규약을 스위치로 바꿔 끼운다.
#   메시와 콜리전이 같은 규약을 쓰므로 둘이 어긋날 수 없다.
#
#   기본 규약 : engine = (bx, bz, -by),  engine yaw = byaw
#     -FlipZ    : engine z 부호 반전 (남북 거울)
#     -FlipYaw  : yaw 부호 반전
#     -YawOfs   : yaw 에 상수 더하기 (예: 180)
#
#   .\krm_build.ps1 -Remove -Apply          # 통째로 지우기
#   .\krm_build.ps1 -Apply                  # 기본 규약으로 짓기
#   .\krm_build.ps1 -FlipZ -FlipYaw -Apply  # 남북 거울 + yaw 반전
param(
    [double] $Dx = 100000, [double] $Dy = 0, [double] $Dz = 0,
    [switch] $FlipZ, [switch] $FlipYaw, [double] $YawOfs = 0,
    [bool] $SkipResponds = $true,
    [ValidateSet('pct','cm')][string] $SizeMode = 'pct',
    [switch] $KeepCenter,
    [switch] $RoomsOnly,
    [string] $Dir = "$PSScriptRoot\kremlin\KRM_work\export_v1",
    [string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm",
    [switch] $Remove, [switch] $Apply
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"
. "$PSScriptRoot\ovdr_place.ps1"
. "$PSScriptRoot\ovdr_script.ps1"

$text = Read-OvdrText -Path $LevelPath
foreach ($p in @('KRM_Palace', 'KRMM_', 'KRM_COL_', 'KRM_Spawn')) {
    $text = Remove-OvdrInstancesByName -Text $text -NamePrefix $p
}
$key = Get-OvdrKeyIndex -Text $text
if ($Remove) {
    $null = $text | ConvertFrom-Json
    $null = Backup-OvdrLevel -Path $LevelPath -Tag 'BEFORE_WIPE'
    Write-OvdrText -Text $text -Path $LevelPath
    Write-Host 'KRM_Palace 전체 제거' -ForegroundColor Yellow
    if ($Apply) { Publish-OvdrLevel }
    return
}

$pl = Get-Content (Join-Path $Dir 'placement.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$zs = if ($FlipZ) { -1.0 } else { 1.0 }
$ys = if ($FlipYaw) { -1.0 } else { 1.0 }

# --- 에셋 매핑 (contentId 집합 차이) ---
$proj = "$env:USERPROFILE\Desktop\onlyoneshot"
$tbl = Get-Content "$proj\UGCLocalAssetTable.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$before = @{}
Get-Content (Join-Path $Dir 'before_ids.txt') -Encoding UTF8 | ForEach-Object { $before[$_] = $true }
$meshMap = @{}; $texMap = @{}
foreach ($p in $tbl.localAssetList.PSObject.Properties) {
    if ($before.ContainsKey($p.Name)) { continue }
    $v = $p.Value
    if ($v.worldAssetType -eq 'STATIC_MESH') {
        if (-not $meshMap.ContainsKey($v.name)) { $meshMap[$v.name] = $v.contentId }
    }
    elseif ($v.worldAssetType -eq 'TEXTURE') {
        if (-not $texMap.ContainsKey($v.name)) { $texMap[$v.name] = $v.contentId }
        $u = $v.name -replace '[.]', '_'
        if (-not $texMap.ContainsKey($u)) { $texMap[$u] = $v.contentId }
    }
}

$k = $key
$items = New-Object System.Collections.Generic.List[string]
$missMesh = @(); $missTex = @()

foreach ($m in $pl.meshes) {
    if ($SkipResponds -and $m.mesh -eq 'KRM_SHELL_GRA_Responds') { continue }
    $an = $m.mesh + '_overdare'
    if (-not $meshMap.ContainsKey($an)) { $missMesh += $m.mesh; continue }

    # 텍스처는 placement.json 의 tex 이름으로 찾는다 (임포터가 점을 밑줄로 바꾼 이름).
    $tid = $null
    if ($m.tex -and $texMap.ContainsKey($m.tex)) { $tid = $texMap[$m.tex] }
    if (-not $tid) {
        # 두 메시가 텍스처를 공유하면 엔진엔 한 장만 올라간다 (옥좌 p00/p01)
        $base = [string]$m.tex -replace '_\d+$', ''
        $hits = @($texMap.Keys | Where-Object { $_ -like ($base + '_*') })
        $ids = @($hits | ForEach-Object { $texMap[$_] } | Sort-Object -Unique)
        if ($ids.Count -eq 1) { $tid = $ids[0] }
    }
    if (-not $tid) { $missTex += $m.mesh }

    $px = [double]$m.bpos[0] + $Dx
    $py = [double]$m.bpos[2] + $Dy
    $pz = $zs * (-[double]$m.bpos[1]) + $Dz
    # Size 는 배율이다 : 100 = 원본 메시 크기. (실치수 cm 를 넣으면 수십 배로 커진다)
    if ($SizeMode -eq 'cm') {
        $sx = [double]$m.bsize[0] * [double]$m.scale[0]
        $sy = [double]$m.bsize[2] * [double]$m.scale[2]
        $sz = [double]$m.bsize[1] * [double]$m.scale[1]
    } else {
        $sx = 100 * [double]$m.scale[0]
        $sy = 100 * [double]$m.scale[2]
        $sz = 100 * [double]$m.scale[1]
    }
    # YawOfs 적용 대상 : -KeepCenter 면 VLA(가운데 팔각홀)는 제외, -RoomsOnly 면 소품 제외
    $ofs = $YawOfs
    if ($KeepCenter -and $m.mesh -like 'KRM_SHELL_VLA*') { $ofs = 0 }
    if ($RoomsOnly -and $m.mesh -like 'KRM_PROP*') { $ofs = 0 }
    $yaw = ($ys * [double]$m.byaw) + $ofs
    $yaw = (($yaw % 360) + 360) % 360
    if ($yaw -gt 180) { $yaw = $yaw - 360 }

    $k++
    $items.Add((New-OvdrMeshPartJson -Name ('KRMM_' + $m.name) -ObjectKey $k `
        -MeshId ("ovdrassetid://" + $meshMap[$an]) `
        -TextureId $(if ($tid) { "ovdrassetid://$tid" } else { '' }) `
        -PX $px -PY $py -PZ $pz `
        -OX ([double]$m.bpitch) -OY $yaw -OZ ([double]$m.broll) `
        -SX $sx -SY $sy -SZ $sz `
        -Material 'Basic' -CanCollide $false -CastShadow $true))
}

foreach ($c in $pl.collision) {
    $px = [double]$c.bpos[0] + $Dx
    $py = [double]$c.bpos[2] + $Dy
    $pz = $zs * (-[double]$c.bpos[1]) + $Dz
    $sx = [double]$c.bsize[0]
    $sy = [double]$c.bsize[2]
    $sz = [double]$c.bsize[1]
    $yaw = ($ys * [double]$c.byaw) + $YawOfs
    $yaw = (($yaw % 360) + 360) % 360
    if ($yaw -gt 180) { $yaw = $yaw - 360 }
    $k++
    $items.Add((New-OvdrPartJson -Name $c.name -ObjectKey $k `
        -PX $px -PY $py -PZ $pz -OX 0 -OY $yaw -OZ 0 `
        -SX $sx -SY $sy -SZ $sz `
        -Material 'Unlit' -Transparency 1 -CanCollide $true))
}

foreach ($s in $pl.spawns) {
    $px = [double]$s.bpos[0] + $Dx
    $py = [double]$s.bpos[2] + $Dy
    $pz = $zs * (-[double]$s.bpos[1]) + $Dz
    if ($s.team -eq 'red') { $cn = 21; $cr = 196; $cg = 40; $cb = 28 }
    else { $cn = 23; $cr = 13; $cg = 105; $cb = 172 }
    $k++
    $g = New-OvdrGuid
    $items.Add(@"
{
	"InstanceType": "SpawnLocation",
	"ActorGuid": "$g",
	"ObjectKey": $k,
	"Archivable": true,
	"Name": "$($s.name)",
	"bDisableAdaptiveNetUpdateFrequency": false,
	"Mobility": "Movable",
	"PivotOffsetCFrame": { "ObjectType": "CFrame", "Position": $(New-OvdrVector3 0 0 0), "Orientation": $(New-OvdrVector3 0 0 0) },
	"Anchored": true,
	"CanCollide": true,
	"CanTouch": true,
	"Transparency": 0,
	"CastShadow": false,
	"Locked": false,
	"CanClimb": false,
	"IsTouchingBodyPart": false,
	"CollisionProfile": "BlockAll",
	"MaterialVariant": "",
	"TraceGroupNameString": "None",
	"UnitExtent": $(New-OvdrVector3 50 50 -50),
	"CFrame": { "ObjectType": "CFrame", "Position": $(New-OvdrVector3 $px $py $pz), "Orientation": $(New-OvdrVector3 0 0 0) },
	"Size": $(New-OvdrVector3 100 10 100),
	"AssemblyLinearVelocity": $(New-OvdrVector3 0 0 0),
	"BrickColor": { "ObjectType": "BrickColor", "Number": $cn, "r": $cr, "g": $cg, "b": $cb, "Name": "KRM" },
	"Color": { "ObjectType": "Color3", "R": $cr, "G": $cg, "B": $cb },
	"CurrentPhysicalProperties": { "ObjectType": "PhysicalProperties", "Density": 1, "Friction": 1, "Elasticity": 1 },
	"CustomPhysicalProperties": { "ObjectType": "PhysicalProperties", "Density": 1, "Friction": 1, "Elasticity": 1 },
	"Material": "Basic",
	"AssemblyRootPart": { "Value": -1, "Type": "None" },
	"Shape": "Block",
	"TeamColor": { "ObjectType": "BrickColor", "Number": $cn, "r": $cr, "g": $cg, "b": $cb, "Name": "KRM" },
	"Enabled": true,
	"Neutral": false
}
"@)
}

if ($missMesh.Count) { throw ("메시 에셋 없음: " + ($missMesh -join ', ')) }
if ($missTex.Count) { Write-Host ("텍스처 못 찾음: " + ($missTex -join ', ')) -ForegroundColor Red }

$k++
$modelKey = $k
$modelGuid = New-OvdrGuid
$model = @"
{
	"InstanceType": "Model",
	"ActorGuid": "$modelGuid",
	"ObjectKey": $modelKey,
	"Archivable": true,
	"Name": "KRM_Palace",
	"bDisableAdaptiveNetUpdateFrequency": false,
	"Mobility": "Movable",
	"WorldTransform": { "Translation": $(New-OvdrVector3 0 0 0), "Rotation": $(New-OvdrVector3 0 0 0), "Scale": $(New-OvdrVector3 1 1 1) },
	"PivotOffsetCFrame": { "ObjectType": "CFrame", "Position": $(New-OvdrVector3 0 0 0), "Orientation": $(New-OvdrVector3 0 0 0) },
	"bNPCMapObject": false,
	"WorldPivot": { "ObjectType": "CFrame", "Position": $(New-OvdrVector3 0 0 0), "Orientation": $(New-OvdrVector3 0 0 0) },
	"PrimaryPart": { "Value": -1, "Type": "None" },
	"LuaChildren": [
$($items -join ",`r`n")
	]
}
"@

$text = Add-OvdrInstances -Text $text -InstanceJson @($model) -ParentType 'Workspace' -NewKeyIndex $k
$null = $text | ConvertFrom-Json
$null = Backup-OvdrLevel -Path $LevelPath -Tag 'BEFORE_BUILD'
Write-OvdrText -Text $text -Path $LevelPath
Write-Host ("KRM_Palace 재건축: 자식 {0}  (FlipZ={1} FlipYaw={2} YawOfs={3})" -f $items.Count, [bool]$FlipZ, [bool]$FlipYaw, $YawOfs) -ForegroundColor Green
if ($Apply) { Publish-OvdrLevel }
