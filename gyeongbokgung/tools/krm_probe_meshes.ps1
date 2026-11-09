# P0 프로브 메시 배치 — 임포트된 PRB_* 에셋을 놓는다.
#
#   .\krm_probe_meshes.ps1 -Apply
#   .\krm_probe_meshes.ps1 -Remove -Apply
param(
    [double] $OX = 110000,
    [string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm",
    [string] $Dir = "$PSScriptRoot\kremlin\KRM_work\probe",
    [switch] $Remove,
    [switch] $Apply
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"
. "$PSScriptRoot\ovdr_place.ps1"
. "$PSScriptRoot\ovdr_script.ps1"

# ── 에셋 해석 : contentId 집합 차이 ──────────────────────────────────────────
$proj = (Get-OvdrProject).cwd
$before = @{}
Get-Content (Join-Path $Dir 'before_ids.txt') -Encoding UTF8 | ForEach-Object { $before[$_] = $true }
$tbl = Get-Content "$proj\UGCLocalAssetTable.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$mesh = @{}; $tex = @{}
foreach ($p in $tbl.localAssetList.PSObject.Properties) {
    if ($before.ContainsKey($p.Name)) { continue }
    $v = $p.Value
    if     ($v.worldAssetType -eq 'STATIC_MESH') { $mesh[$v.name] = $v.contentId }
    elseif ($v.worldAssetType -eq 'TEXTURE')     { $tex[$v.name]  = $v.contentId }
}
Write-Host ("신규 메시 {0} / 텍스처 {1}" -f $mesh.Count, $tex.Count)

$text = Read-OvdrText -Path $LevelPath
$text = Remove-OvdrInstancesByName -Text $text -NamePrefix 'KRMPRB_'
$key  = Get-OvdrKeyIndex -Text $text
if ($Remove) {
    $null = $text | ConvertFrom-Json
    Write-OvdrText -Text $text -Path $LevelPath
    Write-Host 'KRMPRB_* 제거됨' -ForegroundColor Yellow
    if ($Apply) { Publish-OvdrLevel }
    return
}

$k = $key
$items = New-Object System.Collections.Generic.List[string]
function Add-Mesh {
    param([string]$Name,[string]$MeshName,[string]$TexName,
          [double]$PX,[double]$PY,[double]$PZ,[double]$OY=0,
          [int]$R=255,[int]$G=255,[int]$B=255,[string]$Mat='Basic',[double]$Tr=0)
    if (-not $mesh.ContainsKey($MeshName)) { throw "메시 에셋 없음: $MeshName" }
    $t = if ($TexName -and $tex.ContainsKey($TexName)) { "ovdrassetid://$($tex[$TexName])" } else { '' }
    $script:k++
    $script:items.Add((New-OvdrMeshPartJson -Name $Name -ObjectKey $script:k `
        -MeshId "ovdrassetid://$($mesh[$MeshName])" -TextureId $t `
        -PX $PX -PY $PY -PZ $PZ -OY $OY -SX 100 -SY 100 -SZ 100 `
        -R $R -G $G -B $B -Material $Mat -Transparency $Tr `
        -CanCollide $false -CastShadow $true))
}

# ── 판 6종 (앞면이 엔진 +Z 를 본다) ─────────────────────────────────────────
Add-Mesh 'KRMPRB_uv4'     'PRB_uv4'   'PRB_grid1234_1024' ($OX+0)    200 -600
Add-Mesh 'KRMPRB_uvneg'   'PRB_uvneg' 'PRB_grid1234_1024' ($OX+500)  200 -600
Add-Mesh 'KRMPRB_uniq'    'PRB_uniq'  'PRB_uniq_2048'     ($OX+1000) 200 -600
Add-Mesh 'KRMPRB_vcol'    'PRB_vcol'  'PRB_fresco_1024'   ($OX+1800) 300 -600
Add-Mesh 'KRMPRB_dense'   'PRB_dense' 'PRB_fresco_1024'   ($OX+900)  300 -1500

# P0-7 알파 : 같은 판을 Basic / Glass 두 벌
Add-Mesh 'KRMPRB_glass_basic' 'PRB_glass' 'PRB_glass_512' ($OX+300) 200 650 -Mat 'Basic'
Add-Mesh 'KRMPRB_glass_glass' 'PRB_glass' 'PRB_glass_512' ($OX+800) 200 650 -Mat 'Glass'

# P0-6 파츠 color 틴트 : 같은 메시·같은 텍스처, Color 만 다르게
Add-Mesh 'KRMPRB_tint_white'  'PRB_uniq' 'PRB_uniq_2048' ($OX+2400) 200 -600 -R 255 -G 255 -B 255
Add-Mesh 'KRMPRB_tint_orange' 'PRB_uniq' 'PRB_uniq_2048' ($OX+2900) 200 -600 -R 255 -G 150 -B  60

# 내장 머티리얼이 MeshPart 에도 먹는가 (텍스처 없이 Material 만)
Add-Mesh 'KRMPRB_matmesh_marble' 'PRB_uniq' '' ($OX+2400) 200 650 -Mat 'Marble'
Add-Mesh 'KRMPRB_matmesh_brick'  'PRB_uniq' '' ($OX+2900) 200 650 -Mat 'HouseBricks'
Add-Mesh 'KRMPRB_matmesh_none'   'PRB_uniq' '' ($OX+3400) 200 650 -Mat 'Basic'

# 유리 뒤 흰 배경판 (알파 투과 판정)
$k++
$items.Add((New-OvdrPartJson -Name 'KRMPRB_glassback' -ObjectKey $k `
    -PX ($OX+550) -PY 250 -PZ 780 -SX 1000 -SY 600 -SZ 20 `
    -R 250 -G 250 -B 250 -Material 'Unlit' -CanCollide $false))

# ── P0-9 PointLight : 암실 안 앵커 Part 의 자식으로 넣는다 ──────────────────
$cx = $OX + 2600
$lights = @()
foreach ($cfg in @(@{n='a'; z=-200; br=5;  rg=800}, @{n='b'; z=0;   br=15; rg=800}, @{n='c'; z=200; br=30; rg=1200})) {
    $k++
    $lights += @"
{
	"InstanceType": "PointLight",
	"ActorGuid": "$(New-OvdrGuid)",
	"ObjectKey": $k,
	"Archivable": true,
	"Name": "KRMPRB_light_$($cfg.n)",
	"bDisableAdaptiveNetUpdateFrequency": false,
	"Mobility": "Movable",
	"Enabled": true,
	"Brightness": $($cfg.br),
	"Range": $($cfg.rg),
	"Color": { "ObjectType": "Color3", "R": 255, "G": 214, "B": 170 }
}
"@
}
$k++
$anchorKey = $k
$anchorGuid = New-OvdrGuid
$anchor = @"
{
	"InstanceType": "Part",
	"ActorGuid": "$anchorGuid",
	"ObjectKey": $anchorKey,
	"Archivable": true,
	"Name": "KRMPRB_lightanchor",
	"bDisableAdaptiveNetUpdateFrequency": false,
	"Mobility": "Movable",
	"PivotOffsetCFrame": { "ObjectType": "CFrame", "Position": $(New-OvdrVector3 0 0 0), "Orientation": $(New-OvdrVector3 0 0 0) },
	"Anchored": true,
	"CanCollide": false,
	"CanTouch": false,
	"Transparency": 1,
	"CastShadow": false,
	"Locked": false,
	"CanClimb": false,
	"IsTouchingBodyPart": false,
	"CollisionProfile": "NoCollision",
	"MaterialVariant": "",
	"TraceGroupNameString": "None",
	"UnitExtent": $(New-OvdrVector3 50 50 -50),
	"CFrame": { "ObjectType": "CFrame", "Position": $(New-OvdrVector3 $cx 250 0), "Orientation": $(New-OvdrVector3 0 0 0) },
	"Size": $(New-OvdrVector3 20 20 20),
	"AssemblyLinearVelocity": $(New-OvdrVector3 0 0 0),
	"BrickColor": { "ObjectType": "BrickColor", "Number": 194, "r": 200, "g": 200, "b": 200, "Name": "Medium stone grey" },
	"Color": { "ObjectType": "Color3", "R": 200, "G": 200, "B": 200 },
	"CurrentPhysicalProperties": { "ObjectType": "PhysicalProperties", "Density": 1, "Friction": 1, "Elasticity": 1 },
	"CustomPhysicalProperties": { "ObjectType": "PhysicalProperties", "Density": 1, "Friction": 1, "Elasticity": 1 },
	"Material": "Basic",
	"AssemblyRootPart": { "Value": -1, "Type": "None" },
	"Shape": "Block",
	"LuaChildren": [
$($lights -join ",`r`n")
	]
}
"@
$items.Add($anchor)

$k++
$modelKey = $k
$modelGuid = New-OvdrGuid
$model = @"
{
	"InstanceType": "Model",
	"ActorGuid": "$modelGuid",
	"ObjectKey": $modelKey,
	"Archivable": true,
	"Name": "KRMPRB_Meshes",
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
Write-OvdrText -Text $text -Path $LevelPath
Write-Host ("KRMPRB_Meshes 삽입: 노드 {0}, keys {1}..{2}" -f $items.Count, ($key+1), $k) -ForegroundColor Green
if ($Apply) { Publish-OvdrLevel } else { Write-Host '적용 안 함.' -ForegroundColor Yellow }
