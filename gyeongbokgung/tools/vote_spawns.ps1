# 화성에 팀 스폰 2개를 만든다.
#
# ★ 반드시 "Hwaseong Place" 안에 넣는다.
#   "Hwaseong Collision" 은 992장짜리 생성물이라 재생성 레시피가 덮어쓸 수 있다.
#
# ★ BrickColor 이름·번호가 JSN / KRM 과 같아야 TeamServer 의 팀 매칭이 돈다.
#   Bright red = 21, Bright blue = 23. Neutral = false.
#
# ★ Y 는 대충 줘도 된다. TeamServer.snapToGround 가 스폰보다 30m 위에서 60m 아래로
#   레이캐스트해서 실제 바닥에 얹는다. 화성 지면은 Y ≈ -99 라 창 안에 들어온다.
#   로그의 "[Team] HWS_Spawn_Red 바닥에 붙임 : Y 200 -> ..." 가 -99 근처면 성공,
#   200 그대로면 레이캐스트가 실패한 것이다.
#
#   .\vote_spawns.ps1            # 미리보기
#   .\vote_spawns.ps1 -Apply
#   .\vote_spawns.ps1 -Remove -Apply
param(
    [string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm",
    [switch] $Remove,
    [switch] $Apply
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"
. "$PSScriptRoot\ovdr_script.ps1"

$CONTAINER = 'Hwaseong Place'
$PREFIX    = 'HWS_Spawn_'

# 걸을 수 있는 범위는 Hwaseong Collision 이 정한다 (X 56742..66060, Z -4808..4810).
# 경기구역 벽(X 57600..65200) 안쪽에서 동/서로 마주보게 둔다. 간격 62 m.
$spawns = @(
    @{ N = 'Red';  X = 64500; Z = 0; Num = 21; R = 196; G = 40;  B = 28;  Name = 'Bright red'  }
    @{ N = 'Blue'; X = 58300; Z = 0; Num = 23; R = 13;  G = 105; B = 172; Name = 'Bright blue' }
)
$Y = 200

$text = Read-OvdrText -Path $LevelPath
$text = Remove-OvdrInstancesByName -Text $text -NamePrefix $PREFIX

if ($Remove) {
    $null = $text | ConvertFrom-Json
    $null = Backup-OvdrLevel -Path $LevelPath -Tag 'hws_spawn_remove'
    Write-OvdrText -Text $text -Path $LevelPath
    Write-Host "$PREFIX* 제거됨" -ForegroundColor Yellow
    if ($Apply) { $null = Invoke-OvdrRpc -Method 'game.stop' -TimeoutSec 30; Publish-OvdrLevel }
    return
}

$key = Get-OvdrKeyIndex -Text $text
$k = $key
$json = @()
foreach ($s in $spawns) {
    $k++
    $name = $PREFIX + $s.N
    # SpawnLocation 은 New-OvdrPartJson 이 못 만든다. 레벨의 KRM 스폰과 같은 모양으로 직접 쓴다.
    # ★ CanTouch 는 반드시 true. 끄면 스폰 감지가 안 된다 (TeamServer:410 경고).
    $json += @"
{
	"InstanceType": "SpawnLocation",
	"ActorGuid": "$(New-OvdrGuid)",
	"ObjectKey": $k,
	"Archivable": true,
	"Name": "$name",
	"bDisableAdaptiveNetUpdateFrequency": false,
	"Mobility": "Movable",
	"PivotOffsetCFrame": { "ObjectType": "CFrame", "Position": $(New-OvdrVector3 0 0 0), "Orientation": $(New-OvdrVector3 0 0 0) },
	"Anchored": true,
	"CanCollide": true,
	"CanTouch": true,
	"Transparency": 0,
	"CastShadow": true,
	"Locked": false,
	"CanClimb": false,
	"IsTouchingBodyPart": false,
	"CollisionProfile": "BlockAll",
	"MaterialVariant": "",
	"TraceGroupNameString": "None",
	"UnitExtent": $(New-OvdrVector3 50 50 -50),
	"CFrame": { "ObjectType": "CFrame", "Position": $(New-OvdrVector3 $s.X $Y $s.Z), "Orientation": $(New-OvdrVector3 0 0 0) },
	"Size": $(New-OvdrVector3 100 10 100),
	"AssemblyLinearVelocity": $(New-OvdrVector3 0 0 0),
	"BrickColor": { "ObjectType": "BrickColor", "Number": $($s.Num), "r": $($s.R), "g": $($s.G), "b": $($s.B), "Name": "$($s.Name)" },
	"Color": { "ObjectType": "Color3", "R": $($s.R), "G": $($s.G), "B": $($s.B) },
	"CurrentPhysicalProperties": { "ObjectType": "PhysicalProperties", "Density": 1, "Friction": 1, "Elasticity": 1 },
	"CustomPhysicalProperties": { "ObjectType": "PhysicalProperties", "Density": 1, "Friction": 1, "Elasticity": 1 },
	"Material": "Basic",
	"AssemblyRootPart": { "Value": -1, "Type": "None" },
	"Shape": "Block",
	"Enabled": true,
	"Neutral": false,
	"TeamColor": { "ObjectType": "BrickColor", "Number": $($s.Num), "r": $($s.R), "g": $($s.G), "b": $($s.B), "Name": "$($s.Name)" }
}
"@
    Write-Host ("  {0,-16} P=({1}, {2}, {3})  TeamColor #{4} {5}" -f $name, $s.X, $Y, $s.Z, $s.Num, $s.Name)
}
$gap = [Math]::Abs($spawns[0].X - $spawns[1].X)
Write-Host ("  스폰 간격 {0} cm = {1} m   (MapService.hws.minSpawnDist = 2200 = 22m)" -f $gap, ($gap / 100))

$new = Add-OvdrInstances -Text $text -InstanceJson $json `
        -ParentType 'Model' -ParentName $CONTAINER -NewKeyIndex $k
$null = $new | ConvertFrom-Json

$hits = ([regex]::Matches($new, '"Name":\s*"' + $PREFIX)).Count
if ($hits -ne 2) { throw ("검산 실패 : {0}* 가 {1}개다 (2개여야 한다)" -f $PREFIX, $hits) }
Write-Host ("검산 통과 : {0}* 2개, 컨테이너 {1}" -f $PREFIX, $CONTAINER) -ForegroundColor Green

if (-not $Apply) { Write-Host "미리보기만 했다. 반영하려면 -Apply." -ForegroundColor Yellow; return }

$null = Backup-OvdrLevel -Path $LevelPath -Tag 'hws_spawns'
Write-OvdrText -Text $new -Path $LevelPath
$null = Invoke-OvdrRpc -Method 'game.stop' -TimeoutSec 30
Publish-OvdrLevel
