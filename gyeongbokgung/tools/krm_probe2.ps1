# P0 2차 프로브 — 알파 판정용 배경판, 조명을 방 밖으로, MaterialVariant
#
#   .\krm_probe2.ps1 -Apply
#   .\krm_probe2.ps1 -Lights off -Apply      # 조명만 끈다 (A/B 용)
#   .\krm_probe2.ps1 -Remove -Apply
param(
    [double] $OX = 110000,
    [string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm",
    [string] $Dir = "$PSScriptRoot\kremlin\KRM_work\probe",
    [ValidateSet('on','off')][string] $Lights = 'on',
    [switch] $Remove,
    [switch] $Apply
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"
. "$PSScriptRoot\ovdr_place.ps1"
. "$PSScriptRoot\ovdr_script.ps1"

$proj = (Get-OvdrProject).cwd
$before = @{}
Get-Content (Join-Path $Dir 'before_ids.txt') -Encoding UTF8 | ForEach-Object { $before[$_] = $true }
$tbl = Get-Content "$proj\UGCLocalAssetTable.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$tex = @{}
foreach ($p in $tbl.localAssetList.PSObject.Properties) {
    if ($before.ContainsKey($p.Name)) { continue }
    if ($p.Value.worldAssetType -eq 'TEXTURE') { $tex[$p.Value.name] = $p.Value.contentId }
}

$text = Read-OvdrText -Path $LevelPath
$text = Remove-OvdrInstancesByName -Text $text -NamePrefix 'KRMP2_'
$key  = Get-OvdrKeyIndex -Text $text
if ($Remove) {
    $null = $text | ConvertFrom-Json
    Write-OvdrText -Text $text -Path $LevelPath
    Write-Host 'KRMP2_* 제거됨' -ForegroundColor Yellow
    if ($Apply) { Publish-OvdrLevel }
    return
}

$en = if ($Lights -eq 'on') { 'true' } else { 'false' }
$k = $key
$items = New-Object System.Collections.Generic.List[string]

# ── 유리 뒤 흰 배경판 (알파 판정) ────────────────────────────────────────────
$k++
$items.Add((New-OvdrPartJson -Name 'KRMP2_backdrop' -ObjectKey $k `
    -PX ($OX+1520) -PY 150 -PZ -650 -SX 700 -SY 400 -SZ 20 `
    -R 250 -G 250 -B 250 -Material 'Unlit' -CanCollide $false))

# ── 조명을 방 밖, 판 앞으로 옮긴다 ─────────────────────────────────────────
$plNodes = @()
foreach ($cfg in @(@{n='near'; x=1800; br=20; rg=700}, @{n='far'; x=2100; br=60; rg=1500})) {
    $k++
    $plNodes += @"
{
	"InstanceType": "PointLight",
	"ActorGuid": "$(New-OvdrGuid)",
	"ObjectKey": $k,
	"Archivable": true,
	"Name": "KRMP2_pl_$($cfg.n)",
	"bDisableAdaptiveNetUpdateFrequency": false,
	"Mobility": "Movable",
	"Enabled": $en,
	"Brightness": $($cfg.br),
	"Range": $($cfg.rg),
	"Color": { "ObjectType": "Color3", "R": 255, "G": 190, "B": 120 }
}
"@
}
$k++
$anchorKey = $k; $anchorGuid = New-OvdrGuid
$items.Add(@"
{
	"InstanceType": "Part",
	"ActorGuid": "$anchorGuid",
	"ObjectKey": $anchorKey,
	"Archivable": true,
	"Name": "KRMP2_plmount",
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
	"CFrame": { "ObjectType": "CFrame", "Position": $(New-OvdrVector3 ($OX+1950) 200 -250), "Orientation": $(New-OvdrVector3 0 0 0) },
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
$($plNodes -join ",`r`n")
	]
}
"@)

# 조명이 비칠 흰 벽 (판 앞쪽, 정면)
$k++
$items.Add((New-OvdrPartJson -Name 'KRMP2_litwall' -ObjectKey $k `
    -PX ($OX+1950) -PY 200 -PZ -50 -SX 1200 -SY 400 -SZ 20 `
    -R 235 -G 235 -B 235 -Material 'Basic' -CanCollide $false))

# ── P0-8 MaterialVariant 시험용 파츠 (Variant 는 MaterialService 밑에 따로 넣는다) ──
$k++
$mvPart = (New-OvdrPartJson -Name 'KRMP2_mvtest' -ObjectKey $k `
    -PX ($OX+3400) -PY 200 -PZ -600 -SX 400 -SY 400 -SZ 20 `
    -R 255 -G 255 -B 255 -Material 'Basic' -CanCollide $false)
$mvPart = $mvPart -replace '"MaterialVariant": ""', '"MaterialVariant": "KRMP2_MV"'
$items.Add($mvPart)
$k++
$items.Add((New-OvdrPartJson -Name 'KRMP2_mvref' -ObjectKey $k `
    -PX ($OX+3900) -PY 200 -PZ -600 -SX 400 -SY 400 -SZ 20 `
    -R 255 -G 255 -B 255 -Material 'Basic' -CanCollide $false))

$k++
$modelKey = $k; $modelGuid = New-OvdrGuid
$model = @"
{
	"InstanceType": "Model",
	"ActorGuid": "$modelGuid",
	"ObjectKey": $modelKey,
	"Archivable": true,
	"Name": "KRMP2_Probe2",
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

# MaterialVariant 를 MaterialService 의 자식으로
$k++
$mv = @"
{
	"InstanceType": "MaterialVariant",
	"ActorGuid": "$(New-OvdrGuid)",
	"ObjectKey": $k,
	"Archivable": true,
	"Name": "KRMP2_MV",
	"bDisableAdaptiveNetUpdateFrequency": false,
	"Mobility": "Movable",
	"BaseMaterial": "Basic",
	"UseCustomPhysicsProperties": false,
	"MetersPerTile": 2,
	"Metalness": 0,
	"Roughness": 0.6,
	"ColorMap":     { "ObjectType": "Content", "Content": "ovdrassetid://$($tex['PRB_fresco_1024'])" },
	"MetalnessMap": { "ObjectType": "Content", "Content": "" },
	"NormalMap":    { "ObjectType": "Content", "Content": "" },
	"RoughnessMap": { "ObjectType": "Content", "Content": "" },
	"CustomPhysicalProperties": { "ObjectType": "PhysicalProperties", "Density": 1, "Friction": 1, "Elasticity": 1 },
	"Color": { "ObjectType": "Color3", "R": 255, "G": 255, "B": 255 }
}
"@
$text = Add-OvdrInstances -Text $text -InstanceJson @($mv) -ParentType 'MaterialService' -NewKeyIndex $k

$null = $text | ConvertFrom-Json
Write-OvdrText -Text $text -Path $LevelPath
Write-Host ("KRMP2 삽입: 노드 {0} + MaterialVariant, keys {1}..{2}, 조명 {3}" -f $items.Count, ($key+1), $k, $Lights) -ForegroundColor Green
if ($Apply) { Publish-OvdrLevel }
