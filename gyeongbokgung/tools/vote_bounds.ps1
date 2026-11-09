# 맵별 경기구역 벽 4장을 만든다 (또는 지운다).
#
# 벽은 반드시 그 맵의 컨테이너 안에 있어야 한다. 그래야 스왑할 때 맵과 함께 오간다.
#
# ★ 얇은 축 규칙을 지켜야 한다.
#   BoundaryServer.readRect() 가 size.X < size.Z 로 동/서를 가른다.
#   남/북 벽은 X 가 길어야 하고, 동/서 벽은 Z 가 길어야 한다. 어기면 사각형이 안 나온다.
#
# ★ 벽은 4장이 전부 있어야 한다.
#   하나라도 없으면 readRect 가 nil 을 주고 BoundaryServer 가 "조용히 쉰다".
#   그러면 _G.BoundaryRect 가 안 서고 스왑 검증이 통과하지 못한다.
#
#   .\vote_bounds.ps1 -Map krm             # 미리보기
#   .\vote_bounds.ps1 -Map krm -Apply
#   .\vote_bounds.ps1 -Map krm -Remove -Apply
param(
    [Parameter(Mandatory)][ValidateSet('krm','hws')][string] $Map,
    [string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm",
    [switch] $Remove,
    [switch] $Apply
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"
. "$PSScriptRoot\ovdr_script.ps1"

# MapService.lua 의 rect 와 반드시 같아야 한다.
# (rect 는 벽을 못 찾았을 때의 폴백이므로, 둘이 어긋나면 폴백만 이상해진다)
$specs = @{
    # ★ 높이를 낮게 눕힌다. 벽을 높이 세우면 편집기에서 맵을 통째로 가린다.
    #   실측 : 크렘린 궁전이 벽 4장 때문에 안 보였다. 벽을 넣자마자 사라지고
    #          벽 없이 다시 지으면 보였다. 반투명 Neon 판이 궁전을 덮은 것이다.
    #
    #   ★ 높이는 판정에 아무 영향이 없다.
    #     BoundaryServer.readRect() 는 Position 과 "size.X < size.Z" 만 본다.
    #     size.Y 는 어디서도 안 쓴다. CaptureServer 도 사각형(minX..maxZ)만 읽는다.
    #     인게임 빨간 울타리는 BoundaryFX 가 사각형으로 따로 그리므로 그것도 무관하다.
    # ★ 밀폐 상자(krm_seal.ps1)와 같은 범위여야 한다.
    #   콜리전 실측이 X 95840~105458 / Z -2170~2170 이라 예전 값(Z ±1900)은
    #   회랑 끝을 잘라먹었다 -- 거기 선 사람이 물리적으론 안에 있는데 이탈로 죽는다.
    krm = @{
        Container = 'KRM_Palace'
        Prefix    = 'KRM_Bound_'
        MinX = 95800; MaxX = 105500; MinZ = -2200; MaxZ = 2200
        Height = 120; CenterY = 60
    }
    # ★ 2026-08-27 : 화성을 2배로 키웠다 (0.25배 -> 0.5배 빌드).
    #   콜리전 실측 X 52084~70719 / Z -9617~9619 = 186.4 x 192.4 m.
    #   경기구역은 거기서 조금 안쪽으로 잡는다.
    hws = @{
        Container = 'Hwaseong Place'
        Prefix    = 'HWS_Bound_'
        MinX = 43000; MaxX = 79800; MinZ = -19000; MaxZ = 19000
        Height = 120; CenterY = 60
    }
}
$s = $specs[$Map]
$cx = ($s.MinX + $s.MaxX) / 2
$cz = ($s.MinZ + $s.MaxZ) / 2
$spanX = ($s.MaxX - $s.MinX) + 1000      # 모서리가 벌어지지 않게 조금 넉넉히
$spanZ = ($s.MaxZ - $s.MinZ) + 1000

$text = Read-OvdrText -Path $LevelPath
$text = Remove-OvdrInstancesByName -Text $text -NamePrefix $s.Prefix

if ($Remove) {
    $null = $text | ConvertFrom-Json
    $null = Backup-OvdrLevel -Path $LevelPath -Tag ("bounds_remove_" + $Map)
    Write-OvdrText -Text $text -Path $LevelPath
    Write-Host ("{0}* 제거됨" -f $s.Prefix) -ForegroundColor Yellow
    if ($Apply) { $null = Invoke-OvdrRpc -Method 'game.stop' -TimeoutSec 30; Publish-OvdrLevel }
    return
}

# 얇은 축 규칙 : 남/북은 X 로 길게, 동/서는 Z 로 길게
$walls = @(
    @{ N = 'North'; PX = $cx;       PZ = $s.MaxZ; SX = $spanX; SZ = 100    }
    @{ N = 'South'; PX = $cx;       PZ = $s.MinZ; SX = $spanX; SZ = 100    }
    @{ N = 'East';  PX = $s.MaxX;   PZ = $cz;     SX = 100;    SZ = $spanZ }
    @{ N = 'West';  PX = $s.MinX;   PZ = $cz;     SX = 100;    SZ = $spanZ }
)

$key = Get-OvdrKeyIndex -Text $text
$k = $key
$json = @()
foreach ($w in $walls) {
    $k++
    $name = $s.Prefix + $w.N
    # 규격은 JSN 벽과 같게 : 통과 가능한 표시용 판이다. 충돌이 있으면 안 된다.
    $json += New-OvdrPartJson -Name $name -ObjectKey $k `
        -PX $w.PX -PY $s.CenterY -PZ $w.PZ `
        -SX $w.SX -SY $s.Height -SZ $w.SZ `
        -R 255 -G 70 -B 70 -Material 'Neon' -CanCollide $false -Transparency 0.62
    $thin = if ($w.SX -lt $w.SZ) { '동/서 (X 로 얇다)' } else { '남/북 (Z 로 얇다)' }
    Write-Host ("  {0,-18} P=({1}, {2}, {3})  Size={4} x {5} x {6}   {7}" -f `
        $name, $w.PX, $s.CenterY, $w.PZ, $w.SX, $s.Height, $w.SZ, $thin)
}

$new = Add-OvdrInstances -Text $text -InstanceJson $json `
        -ParentType 'Model' -ParentName $s.Container -NewKeyIndex $k
$null = $new | ConvertFrom-Json

# 검산 : 4장이 전부 그 컨테이너 안에 있는가
$m = [regex]::Match($new, '"Name":\s*"' + [regex]::Escape($s.Container) + '"')
if (-not $m.Success) { throw ("컨테이너를 못 찾았다: " + $s.Container) }
$hits = ([regex]::Matches($new, '"Name":\s*"' + $s.Prefix)).Count
if ($hits -ne 4) { throw ("검산 실패 : {0}* 가 {1}개다 (4개여야 한다)" -f $s.Prefix, $hits) }
Write-Host ("검산 통과 : {0}* 4장, 컨테이너 {1}" -f $s.Prefix, $s.Container) -ForegroundColor Green

if (-not $Apply) { Write-Host "미리보기만 했다. 반영하려면 -Apply." -ForegroundColor Yellow; return }

$null = Backup-OvdrLevel -Path $LevelPath -Tag ("bounds_" + $Map)
Write-OvdrText -Text $new -Path $LevelPath
$null = Invoke-OvdrRpc -Method 'game.stop' -TimeoutSec 30
Publish-OvdrLevel
