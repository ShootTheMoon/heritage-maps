# 「셸이 안 보인다」 진단 시험대.
#
# 궁전 동쪽 바깥(X 107000~)에 조건을 하나씩 다르게 한 파츠를 일렬로 세운다.
# 편집기에서 보면 어느 조건에서 보이고 어느 조건에서 안 보이는지 한눈에 갈린다.
#
# 세우는 것 (Z 는 전부 0, 1500 간격) :
#   1. 순수 Part (메시 없음)          <- 이 자리에 렌더가 되긴 하는지 확인하는 대조군
#   2. 소품 메시 (벤치) Size 100      <- 보이는 것으로 알려진 것
#   3. 소품 메시 (벤치) Size 1000     <- 크게 키우면 어떻게 되는지
#   4. 셸 메시 (VLA_Room) Size 100    <- 문제의 것. 텍스처 있음
#   5. 셸 메시 (VLA_Room) Size 100    <- 텍스처 없음
#   6. 셸 메시 (VLA_Room) Size 10     <- 작게 줄이면 보이는지
#   7. 셸 메시 (GRA_Room) Size 100    <- 다른 셸도 같은지
#   8. 셸 메시 (VLA_FloorPlate) 100   <- 평평한 바닥판
#
#   .\vote_probe.ps1 -Apply
#   .\vote_probe.ps1 -Remove -Apply
param(
    [string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm",
    [string] $Proj      = "$env:USERPROFILE\Desktop\onlyoneshot",
    [switch] $Remove,
    [switch] $Apply
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"
. "$PSScriptRoot\ovdr_script.ps1"

$PREFIX = 'KRMDIAG_'
$text = Read-OvdrText -Path $LevelPath
$text = Remove-OvdrInstancesByName -Text $text -NamePrefix $PREFIX

if ($Remove) {
    $null = $text | ConvertFrom-Json
    Write-OvdrText -Text $text -Path $LevelPath
    Write-Host "$PREFIX* 제거됨" -ForegroundColor Yellow
    if ($Apply) { $null = Invoke-OvdrRpc -Method 'game.stop' -TimeoutSec 30; Publish-OvdrLevel }
    return
}

# 자산표에서 필요한 에셋 id 를 이름으로 찾는다 (STATIC_MESH / TEXTURE 만)
$tbl = Get-Content "$Proj\UGCLocalAssetTable.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$mesh = @{}; $tex = @{}
foreach ($p in $tbl.localAssetList.PSObject.Properties) {
    $v = $p.Value
    if ($v.worldAssetType -eq 'STATIC_MESH' -and -not $mesh.ContainsKey($v.name)) { $mesh[$v.name] = $v.contentId }
    if ($v.worldAssetType -eq 'TEXTURE'     -and -not $tex.ContainsKey($v.name))  { $tex[$v.name]  = $v.contentId }
}
function MId { param($n) if (-not $mesh.ContainsKey($n)) { throw "STATIC_MESH 를 못 찾음: $n" }; return $mesh[$n] }
function TId { param($n) if (-not $tex.ContainsKey($n))  { throw "TEXTURE 를 못 찾음: $n" };     return $tex[$n] }

$X0 = 107000; $Y = 300; $Z = 0; $STEP = 1500

$specs = @(
    @{ N = '1_plainpart'; Kind = 'part' }
    @{ N = '2_prop_100';   Kind = 'mesh'; M = 'KRM_PROP_Bench_overdare';       T = 'KRM_PROP_Bench_i_014'; S = 100  }
    @{ N = '3_prop_1000';  Kind = 'mesh'; M = 'KRM_PROP_Bench_overdare';       T = 'KRM_PROP_Bench_i_014'; S = 1000 }
    @{ N = '4_shell_tex';  Kind = 'mesh'; M = 'KRM_SHELL_VLA_Room_overdare';   T = 'KRM_SHELL_VLA_Room_001'; S = 100 }
    @{ N = '5_shell_notex';Kind = 'mesh'; M = 'KRM_SHELL_VLA_Room_overdare';   T = '';                       S = 100 }
    @{ N = '6_shell_10';   Kind = 'mesh'; M = 'KRM_SHELL_VLA_Room_overdare';   T = 'KRM_SHELL_VLA_Room_001'; S = 10  }
    @{ N = '7_shellGRA';   Kind = 'mesh'; M = 'KRM_SHELL_GRA_Room_overdare';   T = 'KRM_SHELL_GRA_Room_001'; S = 100 }
    @{ N = '8_floorplate'; Kind = 'mesh'; M = 'KRM_SHELL_VLA_FloorPlate_overdare'; T = 'KRM_SHELL_VLA_FloorPlate_001'; S = 100 }
)

$key = Get-OvdrKeyIndex -Text $text
$k = $key
$json = @()
$idx = 0
foreach ($sp in $specs) {
    $k++
    $px = $X0 + $idx * $STEP
    $idx++
    $name = $PREFIX + $sp.N
    if ($sp.Kind -eq 'part') {
        $json += New-OvdrPartJson -Name $name -ObjectKey $k `
            -PX $px -PY $Y -PZ $Z -SX 400 -SY 400 -SZ 400 `
            -R 255 -G 220 -B 60 -Material 'Basic' -CanCollide $false
        Write-Host ("  {0,-22} 순수 Part 400cm 노랑        X={1}" -f $name, $px)
    } else {
        $mid = MId $sp.M
        $tid = if ($sp.T) { 'ovdrassetid://' + (TId $sp.T) } else { '' }
        $json += New-OvdrMeshPartJson -Name $name -ObjectKey $k `
            -MeshId ('ovdrassetid://' + $mid) -TextureId $tid `
            -PX $px -PY $Y -PZ $Z -OX 0 -OY 0 -OZ 0 `
            -SX $sp.S -SY $sp.S -SZ $sp.S `
            -Material 'Basic' -CanCollide $false -CastShadow $true
        Write-Host ("  {0,-22} {1,-38} Size={2,-5} tex={3,-6} X={4}" -f `
            $name, $sp.M, $sp.S, $(if ($sp.T) { '있음' } else { '없음' }), $px)
    }
}

$new = Add-OvdrInstances -Text $text -InstanceJson $json -ParentType 'Workspace' -NewKeyIndex $k
$null = $new | ConvertFrom-Json
Write-Host ("`n{0} 개 세움. X {1} ~ {2}, Y {3}, Z {4} (궁전 동쪽 바깥)" -f `
    $json.Count, $X0, ($X0 + ($specs.Count - 1) * $STEP), $Y, $Z) -ForegroundColor Green

if (-not $Apply) { Write-Host "미리보기만 했다. 반영하려면 -Apply." -ForegroundColor Yellow; return }
$null = Backup-OvdrLevel -Path $LevelPath -Tag 'krm_diag'
Write-OvdrText -Text $new -Path $LevelPath
$null = Invoke-OvdrRpc -Method 'game.stop' -TimeoutSec 30
Publish-OvdrLevel
