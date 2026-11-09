# P0-8 후속 — MaterialVariant 가 전역 슬롯 등록을 요구하는지 본다.
# 이 레벨이 한 번도 안 쓰는 베이스 머티리얼(Marble)을 채널로 쓴다 → 다른 맵 영향 없음.
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
$text = Remove-OvdrInstancesByName -Text $text -NamePrefix 'KRMP3_'
# Marble 슬롯 원복
$text = [regex]::Replace($text, '"Marble":\s*"KRMP3_MV3"', '"Marble": ""', 1)
$key = Get-OvdrKeyIndex -Text $text
if ($Remove) {
    $null = $text | ConvertFrom-Json
    Write-OvdrText -Text $text -Path $LevelPath
    Write-Host 'KRMP3_* 제거 + Marble 슬롯 원복' -ForegroundColor Yellow
    if ($Apply) { Publish-OvdrLevel }
    return
}

$k = $key
$items = New-Object System.Collections.Generic.List[string]

# 변형을 적용한 판 / 대조군 판 (둘 다 Material = Marble)
$k++
$p1 = (New-OvdrPartJson -Name 'KRMP3_mvslot' -ObjectKey $k `
    -PX ($OX+1400) -PY 200 -PZ 650 -SX 400 -SY 400 -SZ 20 -Material 'Marble' -CanCollide $false)
$p1 = $p1 -replace '"MaterialVariant": ""', '"MaterialVariant": "KRMP3_MV3"'
$items.Add($p1)
$k++
$items.Add((New-OvdrPartJson -Name 'KRMP3_marbleref' -ObjectKey $k `
    -PX ($OX+1900) -PY 200 -PZ 650 -SX 400 -SY 400 -SZ 20 -Material 'Marble' -CanCollide $false))

$k++
$modelKey = $k; $modelGuid = New-OvdrGuid
$model = @"
{
	"InstanceType": "Model",
	"ActorGuid": "$modelGuid",
	"ObjectKey": $modelKey,
	"Archivable": true,
	"Name": "KRMP3_Probe3",
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

$k++
$mv = @"
{
	"InstanceType": "MaterialVariant",
	"ActorGuid": "$(New-OvdrGuid)",
	"ObjectKey": $k,
	"Archivable": true,
	"Name": "KRMP3_MV3",
	"bDisableAdaptiveNetUpdateFrequency": false,
	"Mobility": "Movable",
	"BaseMaterial": "Marble",
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

# ★ 전역 슬롯 등록 : 이 레벨이 안 쓰는 Marble 만 건드린다
$text = [regex]::Replace($text, '"Marble":\s*""', '"Marble": "KRMP3_MV3"', 1)

$null = $text | ConvertFrom-Json
Write-OvdrText -Text $text -Path $LevelPath
Write-Host ("KRMP3 삽입 + MaterialService.Marble = KRMP3_MV3, keys {0}..{1}" -f ($key+1), $k) -ForegroundColor Green
if ($Apply) { Publish-OvdrLevel }
