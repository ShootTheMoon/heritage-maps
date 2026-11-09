# KRM_Palace(크렘린 실내) 를 onlyoneshot 레벨에 넣는다.
#
#   . 이 스크립트는 콜리전 파츠 116개 + 스폰 2개만 넣는다.
#     MeshPart 124개는 Studio GUI 에서 FBX 38개를 벌크 임포트한 뒤
#     krm_place_meshes.ps1 로 넣는다 (이 PC 에는 메시 임포트 RPC 가 없다).
#
#   원점 보정 ΔX +100000 — 레벨 점유 현황과 대조해 고른 값이다:
#     JSN_Sangok  X -73649..-46546 / 경복궁 X -4115..4115 / 창덕궁 X 27000..33000
#     화성 X 42800..80000 / 로비·GND_Base 원점 부근
#     KRM 원좌표 X -4090..4345 → 그대로 넣으면 GND_Base(Y -40..0) 와 겹친다.
#
#   사용:
#     cd C:\Users\HSP\Desktop\blender\gyeongbokgung
#     .\krm_place.ps1              # 파일만 고친다 (미리보기)
#     .\krm_place.ps1 -Apply       # level.apply + level.save.file 까지
param(
    [double] $Dx = 100000,
    [double] $Dy = 0,
    [double] $Dz = 0,
    [string] $Dir = "$PSScriptRoot\kremlin\KRM_work\export_v1",
    [string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm",
    [switch] $Apply
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"
. "$PSScriptRoot\ovdr_script.ps1"

# 스폰 자리 (KRM 로컬 엔진 좌표). 파세트궁 대홀 동쪽 / 테렘궁 서쪽 끝 방.
$SPAWNS = @(
    @{ Name = 'KRM_Spawn_Red';  P = @(3700.0, 10.0, 0.0);   Num = 21; RGB = @(196, 40, 28) },
    @{ Name = 'KRM_Spawn_Blue'; P = @(-3700.0, 10.0, 0.0);  Num = 23; RGB = @(13, 105, 172) }
)

function New-OvdrSpawnJson {
    param(
        [Parameter(Mandatory)][string] $Name,
        [Parameter(Mandatory)][int] $ObjectKey,
        [Parameter(Mandatory)][double] $PX, [Parameter(Mandatory)][double] $PY, [Parameter(Mandatory)][double] $PZ,
        [Parameter(Mandatory)][int] $ColorNumber,
        [Parameter(Mandatory)][int] $R, [Parameter(Mandatory)][int] $G, [Parameter(Mandatory)][int] $B,
        [string] $Guid = (New-OvdrGuid)
    )
@"
{
	"InstanceType": "SpawnLocation",
	"ActorGuid": "$Guid",
	"ObjectKey": $ObjectKey,
	"Archivable": true,
	"Name": "$Name",
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
	"CFrame": { "ObjectType": "CFrame", "Position": $(New-OvdrVector3 $PX $PY $PZ), "Orientation": $(New-OvdrVector3 0 0 0) },
	"Size": $(New-OvdrVector3 100 10 100),
	"AssemblyLinearVelocity": $(New-OvdrVector3 0 0 0),
	"BrickColor": { "ObjectType": "BrickColor", "Number": $ColorNumber, "r": $R, "g": $G, "b": $B, "Name": "KRM" },
	"Color": { "ObjectType": "Color3", "R": $R, "G": $G, "B": $B },
	"CurrentPhysicalProperties": { "ObjectType": "PhysicalProperties", "Density": 1, "Friction": 1, "Elasticity": 1 },
	"CustomPhysicalProperties": { "ObjectType": "PhysicalProperties", "Density": 1, "Friction": 1, "Elasticity": 1 },
	"Material": "Basic",
	"AssemblyRootPart": { "Value": -1, "Type": "None" },
	"Shape": "Block",
	"TeamColor": { "ObjectType": "BrickColor", "Number": $ColorNumber, "r": $R, "g": $G, "b": $B, "Name": "KRM" },
	"Enabled": true,
	"Neutral": false
}
"@
}

function New-KrmModelJson {
    # Hwaseong Collision 노드와 같은 전체 스키마. 자식 JSON 을 그대로 품는다.
    param(
        [Parameter(Mandatory)][string] $Name,
        [Parameter(Mandatory)][int] $ObjectKey,
        [Parameter(Mandatory)][string[]] $Children,
        [string] $Guid = (New-OvdrGuid)
    )
    $kids = ($Children -join ",`r`n")
@"
{
	"InstanceType": "Model",
	"ActorGuid": "$Guid",
	"ObjectKey": $ObjectKey,
	"Archivable": true,
	"Name": "$Name",
	"bDisableAdaptiveNetUpdateFrequency": false,
	"Mobility": "Movable",
	"WorldTransform": { "Translation": $(New-OvdrVector3 0 0 0), "Rotation": $(New-OvdrVector3 0 0 0), "Scale": $(New-OvdrVector3 1 1 1) },
	"PivotOffsetCFrame": { "ObjectType": "CFrame", "Position": $(New-OvdrVector3 0 0 0), "Orientation": $(New-OvdrVector3 0 0 0) },
	"bNPCMapObject": false,
	"WorldPivot": { "ObjectType": "CFrame", "Position": $(New-OvdrVector3 0 0 0), "Orientation": $(New-OvdrVector3 0 0 0) },
	"PrimaryPart": { "Value": -1, "Type": "None" },
	"LuaChildren": [
$kids
	]
}
"@
}

# --- 읽기 -------------------------------------------------------------------
$colName = if (Test-Path (Join-Path $Dir 'items_col_01.json')) { 'items_col_01.json' } else { 'items_col_00.json' }
$colFile = Join-Path $Dir $colName
Write-Host ("콜리전 파일: {0}" -f $colName)
if (-not (Test-Path $colFile)) { throw "콜리전 파일이 없다: $colFile" }
$col = Get-Content $colFile -Raw -Encoding UTF8 | ConvertFrom-Json
Write-Host ("collision parts: {0}" -f $col.Count)

$text = Read-OvdrText -Path $LevelPath
$key  = Get-OvdrKeyIndex -Text $text
Write-Host ("level: {0}  chars={1}  MapObjectKeyIndex={2}" -f $LevelPath, $text.Length, $key)

# 재실행 대비 — 이전 KRM 노드를 먼저 걷어낸다
$before = $text.Length
$text = Remove-OvdrInstancesByName -Text $text -NamePrefix 'KRM_'
if ($text.Length -ne $before) { Write-Host ("removed old KRM_* nodes: {0} chars" -f ($before - $text.Length)) -ForegroundColor Yellow }

# --- 만들기 -----------------------------------------------------------------
$kids = New-Object System.Collections.Generic.List[string]
$k = $key
foreach ($c in $col) {
    $k++
    $p = $c.props.position
    $s = $c.props.size
    $o = $c.props.orientation
    $kids.Add((New-OvdrPartJson -Name $c.name -ObjectKey $k `
        -PX ([double]$p[0] + $Dx) -PY ([double]$p[1] + $Dy) -PZ ([double]$p[2] + $Dz) `
        -OX ([double]$o[0]) -OY ([double]$o[1]) -OZ ([double]$o[2]) `
        -SX ([double]$s[0]) -SY ([double]$s[1]) -SZ ([double]$s[2]) `
        -Material 'Unlit' -Transparency 1 -CanCollide $true))
}
foreach ($sp in $SPAWNS) {
    $k++
    $kids.Add((New-OvdrSpawnJson -Name $sp.Name -ObjectKey $k `
        -PX ([double]$sp.P[0] + $Dx) -PY ([double]$sp.P[1] + $Dy) -PZ ([double]$sp.P[2] + $Dz) `
        -ColorNumber $sp.Num -R $sp.RGB[0] -G $sp.RGB[1] -B $sp.RGB[2]))
}
$k++
$model = New-KrmModelJson -Name 'KRM_Palace' -ObjectKey $k -Children $kids.ToArray()

$text = Add-OvdrInstances -Text $text -InstanceJson @($model) -ParentType 'Workspace' -NewKeyIndex $k

# 쓰기 전에 JSON 이 깨지지 않았는지 확인한다 (레벨 전체 파싱)
$null = $text | ConvertFrom-Json
Write-Host ("json ok. children={0} (col {1} + spawn {2}), keys {3}..{4}" -f $kids.Count, $col.Count, $SPAWNS.Count, ($key + 1), $k) -ForegroundColor Green

$null = Backup-OvdrLevel -Path $LevelPath -Tag 'BEFORE_KRM'
Write-OvdrText -Text $text -Path $LevelPath
Write-Host "level written." -ForegroundColor Green

if ($Apply) {
    Publish-OvdrLevel
} else {
    Write-Host "적용은 안 했다. Studio 에 반영하려면 -Apply 를 붙여 다시 실행하거나 Publish-OvdrLevel 을 호출해라." -ForegroundColor Yellow
}
