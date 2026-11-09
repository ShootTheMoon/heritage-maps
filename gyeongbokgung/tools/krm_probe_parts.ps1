# P0 프로브 — 메시가 필요 없는 것들 (Part 만으로)
#
#   전부 이름이 KRMPROBE_ 로 시작한다. -Remove 로 통째로 지운다.
#   자리는 X 110000 부근 — KRM 본체(95910..104345)에서 5.6 km 밖이다.
#
#   .\krm_probe_parts.ps1            # 파일만 고친다
#   .\krm_probe_parts.ps1 -Apply     # level.apply + save
#   .\krm_probe_parts.ps1 -Remove -Apply
param(
    [double] $OX = 110000,
    [string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm",
    [switch] $Remove,
    [switch] $Apply
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"
. "$PSScriptRoot\ovdr_script.ps1"

$text = Read-OvdrText -Path $LevelPath
$text = Remove-OvdrInstancesByName -Text $text -NamePrefix 'KRMPROBE_'
$key  = Get-OvdrKeyIndex -Text $text

if ($Remove) {
    $null = $text | ConvertFrom-Json
    Write-OvdrText -Text $text -Path $LevelPath
    Write-Host 'KRMPROBE_* 제거됨' -ForegroundColor Yellow
    if ($Apply) { Publish-OvdrLevel }
    return
}

$k = $key
$items = New-Object System.Collections.Generic.List[string]
function Add-Box {
    param([string]$Name, [double]$PX,[double]$PY,[double]$PZ, [double]$SX,[double]$SY,[double]$SZ,
          [int]$R=160,[int]$G=160,[int]$B=160, [string]$Mat='Basic', [double]$Tr=0)
    $script:k++
    $script:items.Add((New-OvdrPartJson -Name $Name -ObjectKey $script:k `
        -PX $PX -PY $PY -PZ $PZ -SX $SX -SY $SY -SZ $SZ `
        -R $R -G $G -B $B -Material $Mat -Transparency $Tr -CanCollide $true))
}

# ── 바닥 ────────────────────────────────────────────────────────────────────
Add-Box 'KRMPROBE_ground' ($OX+900) -10 0  3600 20 1600 -R 120 -G 120 -B 120

# ── P0-10a 눈금자 : 100 유닛 간격 말뚝 11개 = 1000 유닛 ─────────────────────
for ($i = 0; $i -le 10; $i++) {
    $h = if ($i % 5 -eq 0) { 300 } else { 150 }
    $c = if ($i % 5 -eq 0) { @(230, 60, 60) } else { @(240, 240, 240) }
    Add-Box ("KRMPROBE_ruler_{0:d2}" -f $i) ($OX + $i*100) ($h/2) -500  8 $h 8 -R $c[0] -G $c[1] -B $c[2] -Mat 'Unlit'
}

# ── P0-10b 키 기준 기둥 : 180 / 90 ──────────────────────────────────────────
Add-Box 'KRMPROBE_h180' ($OX+1200)  90 -500  40 180 40 -R  60 -G 200 -B  90 -Mat 'Unlit'
Add-Box 'KRMPROBE_h090' ($OX+1300)  45 -500  40  90 40 -R  60 -G 140 -B 220 -Mat 'Unlit'

# ── P0-10c 단차 시험 : 20 / 30 / 40 / 47 / 60 cm ────────────────────────────
$steps = @(
    @{ h = 20; c = @( 80, 220,  80) },
    @{ h = 30; c = @( 80, 220, 220) },
    @{ h = 40; c = @(240, 230,  80) },
    @{ h = 47; c = @(250, 150,  40) },   # 계단탑 실측 라이저 46.68
    @{ h = 60; c = @(230,  60,  60) }
)
for ($i = 0; $i -lt $steps.Count; $i++) {
    $s = $steps[$i]
    Add-Box ("KRMPROBE_step_{0}" -f $s.h) ($OX + 200 + $i*400) ($s.h/2) 200  300 $s.h 300 `
        -R $s.c[0] -G $s.c[1] -B $s.c[2]
}

# ── P0-9 암실 : 내부 800×400×800, -X 쪽 한 면만 열어 둔다 ───────────────────
$cx = $OX + 2600
Add-Box 'KRMPROBE_room_floor' $cx  -10   0   900 20 900 -R 90 -G 90 -B 95
Add-Box 'KRMPROBE_room_ceil'  $cx  410   0   900 20 900 -R 90 -G 90 -B 95
Add-Box 'KRMPROBE_room_w_zp'  $cx  200  450  900 400 20 -R 90 -G 90 -B 95
Add-Box 'KRMPROBE_room_w_zn'  $cx  200 -450  900 400 20 -R 90 -G 90 -B 95
Add-Box 'KRMPROBE_room_w_xp' ($cx+450) 200 0   20 400 900 -R 200 -G 200 -B 200   # 안쪽 벽 = 빛 받는 면
# -X 쪽은 비워 둔다 (에디터 카메라가 들여다볼 구멍)

$k++
$modelKey = $k
$modelGuid = New-OvdrGuid
$model = @"
{
	"InstanceType": "Model",
	"ActorGuid": "$modelGuid",
	"ObjectKey": $modelKey,
	"Archivable": true,
	"Name": "KRMPROBE_Parts",
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
Write-Host ("KRMPROBE_Parts 삽입: 파츠 {0}, keys {1}..{2}" -f $items.Count, ($key+1), $k) -ForegroundColor Green
if ($Apply) { Publish-OvdrLevel } else { Write-Host '적용 안 함. -Apply 를 붙여라.' -ForegroundColor Yellow }
