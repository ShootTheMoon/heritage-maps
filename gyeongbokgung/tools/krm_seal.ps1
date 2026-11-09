# 크렘린 궁전을 콜리전으로 밀폐한다. 어디로도 못 빠져나가게.
#
# 왜 필요한가 (krm_leak.js 실측) :
#   플레이어 높이 Y 60 / 150 / 400 / 700 / 1100 **전부**에서 밖으로 샜다.
#   주 구멍은 남북 회랑 끝(Z ±1900 부근)이고, Y 700 위로는 콜리전이 31장,
#   Y 1100 엔 0장이라 위쪽은 통째로 열려 있었다.
#   KRM_COL_* 166장은 방 안쪽 벽만 덮고 있고 **바깥 껍데기가 없다.**
#
# 무엇을 하나 :
#   벽 4장 + 천장 + 바닥, 여섯 장으로 궁전 전체를 감싼다.
#   투명하고(Transparency 1) 충돌만 있다. 안쪽 벽·문은 하나도 안 건드린다.
#
# ★ 범위는 콜리전 실측에서 뽑았다 : X 95840~105458, Z -2170~2170.
#   회랑이 경기구역(Z ±1900) 밖으로 삐져나와 있어서 경기구역도 같이 넓혀야 한다.
#   안 그러면 회랑 끝에 선 사람이 물리적으로는 안에 있는데 이탈 판정으로 죽는다.
#
#   .\krm_seal.ps1                # 미리보기
#   .\krm_seal.ps1 -Apply
#   .\krm_seal.ps1 -Remove -Apply
param(
    [string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm",
    [switch] $Remove,
    [switch] $Apply
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"
. "$PSScriptRoot\ovdr_script.ps1"

# ★ 이름을 KRM_COL_SEAL_ 로 둔다. krm_build.ps1 이 KRM_COL_ 접두어를 지우므로
#   재건축하면 같이 사라진다 -- 재건축 뒤엔 이 스크립트를 다시 돌려야 한다.
$PREFIX = 'KRM_COL_SEAL_'
$CONTAINER = 'KRM_Palace'

# 밀폐 상자. 콜리전 실측 범위에 여유를 조금 준다.
$MINX = 95800; $MAXX = 105500
$MINZ = -2200; $MAXZ = 2200
$FLOOR_TOP = -30          # 바닥판 윗면
$CEIL_BOT  = 1900         # 천장판 아랫면 (오큘러스 꼭대기 1815 위)

$cx = ($MINX + $MAXX) / 2
$cz = ($MINZ + $MAXZ) / 2
$spanX = $MAXX - $MINX
$spanZ = $MAXZ - $MINZ
$wallH = $CEIL_BOT - $FLOOR_TOP + 200      # 바닥·천장과 넉넉히 겹치게
$wallY = ($FLOOR_TOP + $CEIL_BOT) / 2
$TH = 100                                   # 판 두께

$text = Read-OvdrText -Path $LevelPath
$text = Remove-OvdrInstancesByName -Text $text -NamePrefix $PREFIX

if ($Remove) {
    $null = $text | ConvertFrom-Json
    $null = Backup-OvdrLevel -Path $LevelPath -Tag 'krm_seal_remove'
    Write-OvdrText -Text $text -Path $LevelPath
    Write-Host "$PREFIX* 제거됨" -ForegroundColor Yellow
    if ($Apply) { $null = Invoke-OvdrRpc -Method 'game.stop' -TimeoutSec 30; Publish-OvdrLevel }
    return
}

# 벽은 안쪽 면이 경계에 오게 바깥으로 반 두께만큼 민다.
$panels = @(
    @{ N = 'North';   PX = $cx;            PY = $wallY;                 PZ = $MAXZ + $TH/2;  SX = $spanX + $TH*2; SY = $wallH; SZ = $TH }
    @{ N = 'South';   PX = $cx;            PY = $wallY;                 PZ = $MINZ - $TH/2;  SX = $spanX + $TH*2; SY = $wallH; SZ = $TH }
    @{ N = 'East';    PX = $MAXX + $TH/2;  PY = $wallY;                 PZ = $cz;            SX = $TH; SY = $wallH; SZ = $spanZ + $TH*2 }
    @{ N = 'West';    PX = $MINX - $TH/2;  PY = $wallY;                 PZ = $cz;            SX = $TH; SY = $wallH; SZ = $spanZ + $TH*2 }
    @{ N = 'Ceiling'; PX = $cx;            PY = $CEIL_BOT + $TH/2;      PZ = $cz;            SX = $spanX + $TH*2; SY = $TH; SZ = $spanZ + $TH*2 }
    @{ N = 'Floor';   PX = $cx;            PY = $FLOOR_TOP - $TH/2;     PZ = $cz;            SX = $spanX + $TH*2; SY = $TH; SZ = $spanZ + $TH*2 }
)

$key = Get-OvdrKeyIndex -Text $text
$k = $key
$json = @()
foreach ($p in $panels) {
    $k++
    $name = $PREFIX + $p.N
    # 보이면 안 된다. 충돌만 있는 판이다.
    $json += New-OvdrPartJson -Name $name -ObjectKey $k `
        -PX $p.PX -PY $p.PY -PZ $p.PZ -SX $p.SX -SY $p.SY -SZ $p.SZ `
        -R 120 -G 120 -B 120 -Material 'Basic' -CanCollide $true -Transparency 1
    Write-Host ("  {0,-22} P=({1,8:N0},{2,7:N0},{3,7:N0})  S=({4,6:N0},{5,6:N0},{6,6:N0})" -f `
        $name, $p.PX, $p.PY, $p.PZ, $p.SX, $p.SY, $p.SZ)
}
Write-Host ("`n밀폐 상자 : X {0}~{1}  Z {2}~{3}  Y {4}~{5}" -f $MINX, $MAXX, $MINZ, $MAXZ, $FLOOR_TOP, $CEIL_BOT)

$new = Add-OvdrInstances -Text $text -InstanceJson $json `
        -ParentType 'Model' -ParentName $CONTAINER -NewKeyIndex $k
$null = $new | ConvertFrom-Json

$hits = ([regex]::Matches($new, '"Name":\s*"' + $PREFIX)).Count
if ($hits -ne 6) { throw ("검산 실패 : {0}* 가 {1}개다 (6개여야 한다)" -f $PREFIX, $hits) }
Write-Host ("검산 통과 : {0}* 6장, 컨테이너 {1}" -f $PREFIX, $CONTAINER) -ForegroundColor Green

if (-not $Apply) { Write-Host "미리보기만 했다. 반영하려면 -Apply." -ForegroundColor Yellow; return }
$null = Backup-OvdrLevel -Path $LevelPath -Tag 'krm_seal'
Write-OvdrText -Text $new -Path $LevelPath
$null = Invoke-OvdrRpc -Method 'game.stop' -TimeoutSec 30
Publish-OvdrLevel
