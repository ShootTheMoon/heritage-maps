# KRM_Palace 의 MeshPart 124개를 배치한다 (FBX 38개를 Studio 에서 벌크 임포트한 뒤).
#
#   1) 임포트 직전:  .\krm_place_meshes.ps1 -Snapshot
#      → UGCLocalAssetTable 의 기존 에셋 id 를 before_ids.txt 로 남긴다.
#        (에셋 매핑은 이름이 아니라 contentId 집합 차이로 한다 — 같은 이름 에셋이
#         이미 여러 개 있는 프로젝트다.)
#   2) Studio GUI 에서 FBX 38개를 벌크 임포트한다. 이 PC 에는 메시 임포트 RPC 가 없다.
#   3) 이름 대조만 먼저:  .\krm_place_meshes.ps1 -Resolve
#   4) 실제 배치:        .\krm_place_meshes.ps1 -Apply
#
# 좌표는 krm_place.ps1 과 같은 ΔX 를 써야 콜리전과 겹친다.
param(
    [double] $Dx = 100000,
    [double] $Dy = 0,
    [double] $Dz = 0,
    [string] $Dir = "$PSScriptRoot\kremlin\KRM_work\export_v1",
    [string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm",
    [switch] $Snapshot,
    [switch] $Resolve,
    [switch] $Apply
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"
. "$PSScriptRoot\ovdr_place.ps1"
. "$PSScriptRoot\ovdr_script.ps1"

if ($Snapshot) { Save-OvdrBeforeIds -Dir $Dir; return }

$man = Get-Content (Join-Path $Dir 'manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json

# 배치에서 뺄 메시. 대홀 서쪽 문 정면을 막고 서 있어서 뺐다(2026-08-27).
# 되살리려면 이 배열을 비우고 다시 -Apply 하면 된다. 재발행 불필요.
$SkipMesh = @('KRM_SHELL_GRA_Responds')
if ($SkipMesh.Count) {
    $man.meshes = @($man.meshes | Where-Object { $SkipMesh -notcontains $_.mesh })
    Write-Host ("배치 제외: {0}" -f ($SkipMesh -join ', ')) -ForegroundColor DarkYellow
}

# --- 에셋 이름 대조 ---------------------------------------------------------
$proj = "$env:USERPROFILE\Desktop\onlyoneshot"
$tbl  = Get-Content "$proj\UGCLocalAssetTable.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$before = @{}
$bidFile = Join-Path $Dir 'before_ids.txt'
if (Test-Path $bidFile) { Get-Content $bidFile -Encoding UTF8 | ForEach-Object { $before[$_] = $true } }
else { Write-Warning "before_ids.txt 가 없다. 신규 에셋만 골라내지 못하고 전체에서 이름으로 찾는다." }

$mesh = @{}; $tex = @{}
foreach ($p in $tbl.localAssetList.PSObject.Properties) {
    if ($before.ContainsKey($p.Name)) { continue }
    $v = $p.Value
    if ($v.worldAssetType -eq 'STATIC_MESH') { if (-not $mesh.ContainsKey($v.name)) { $mesh[$v.name] = $v.contentId } }
    elseif ($v.worldAssetType -eq 'TEXTURE') {
        # ★ TEXTURE 만 담는다. MODEL 까지 담으면 이름이 안 맞을 때 MODEL id 가 TextureId 로 들어간다
        #   (2026-08-27 실제로 124개 전부 그렇게 들어갔다).
        # ★ 임포터가 이름의 점을 밑줄로 바꾼다 : KRM_PROP_Bench_i.014 -> KRM_PROP_Bench_i_014
        $n = $v.name
        if (-not $tex.ContainsKey($n)) { $tex[$n] = @{ id = $v.contentId; type = $v.worldAssetType } }
        $u = $n -replace '[.]', '_'
        if (-not $tex.ContainsKey($u)) { $tex[$u] = @{ id = $v.contentId; type = $v.worldAssetType } }
    }
}
Write-Host ("신규 STATIC_MESH {0} 개 / 그 외 {1} 개" -f $mesh.Count, $tex.Count)

$resolved = @{}; $resolvedTex = @{}; $missing = @(); $missingTex = @()
foreach ($m in $man.meshes) {
    $stem = ($m.file -replace '\.fbx$', '')
    $cand = @($stem, $m.mesh, "$($m.mesh)_overdare")
    $hit  = $cand | Where-Object { $mesh.ContainsKey($_) } | Select-Object -First 1
    if ($hit) { $resolved[$m.mesh] = $mesh[$hit] } else { $missing += $stem; continue }
    $tstem = ($m.texture -replace '\.png$', '')
    $cands = @($tstem, ($tstem -replace '[.]', '_'), $stem, ($stem -replace '[.]', '_'), $m.mesh)
    $th = $cands | Where-Object { $_ -and $tex.ContainsKey($_) } | Select-Object -First 1
    if (-not $th) {
        # 같은 텍스처를 두 메시가 공유하면 블렌더가 임포트 때 .001/.002 로 복제하는데
        # 엔진에는 하나만 올라간다(옥좌 p00/p01). 끝 숫자를 떼고 유일하게 걸리면 그걸 쓴다.
        $base = ($tstem -replace '[._]\d+$', '')
        $hits = @($tex.Keys | Where-Object { $_ -like ($base + '_*') } | Sort-Object -Unique)
        $ids  = @($hits | ForEach-Object { $tex[$_].id } | Sort-Object -Unique)
        if ($ids.Count -eq 1) {
            $th = $hits[0]
            Write-Host ("  텍스처 공유 추정: {0} -> {1}" -f $m.mesh, $th) -ForegroundColor DarkYellow
        }
    }
    if ($th) { $resolvedTex[$m.mesh] = $tex[$th].id } else { $missingTex += $m.mesh }
}
Write-Host ("메시 매칭 {0}/{1}  텍스처 매칭 {2}" -f $resolved.Count, $man.meshes.Count, $resolvedTex.Count) -ForegroundColor Green
if ($missingTex.Count) {
    Write-Host ("텍스처 매칭 실패 {0}: {1}" -f $missingTex.Count, ($missingTex -join ', ')) -ForegroundColor Red
    Write-Host "임포트된 TEXTURE 이름:" -ForegroundColor Yellow
    $tex.Keys | Sort-Object | Select-Object -First 40 | ForEach-Object { "   $_" }
}
if ($missing.Count) {
    Write-Host ("매칭 실패 {0}: {1}" -f $missing.Count, (($missing | Select-Object -First 12) -join ', ')) -ForegroundColor Yellow
    Write-Host "임포트된 에셋 이름 목록:" -ForegroundColor Yellow
    $mesh.Keys | Sort-Object | Select-Object -First 40 | ForEach-Object { "   $_" }
}
if ($Resolve -or -not $Apply) {
    Write-Host "대조만 했다. 배치하려면 -Apply 를 붙여라." -ForegroundColor Yellow
    return
}
if ($missing.Count -or $missingTex.Count) { throw "매칭 실패가 있다. 먼저 해결해라." }

# --- 배치 -------------------------------------------------------------------
$text = Read-OvdrText -Path $LevelPath
$text = Remove-OvdrInstancesByName -Text $text -NamePrefix 'KRMM_'
$key  = Get-OvdrKeyIndex -Text $text
$k = $key
$json = @()
foreach ($m in $man.meshes) {
    foreach ($inst in $m.instances) {
        $k++
        $t = if ($resolvedTex.ContainsKey($m.mesh)) { "ovdrassetid://$($resolvedTex[$m.mesh])" } else { '' }
        # ★ Size 는 배율(100=원본)이 아니라 실치수(cm)다. 2026-08-27 실측:
        #   Size 100 으로 넣으면 27 m 방이 1 m 로 렌더돼 화면에서 사라진다.
        #   manifest.size_cm = 엔진 축 순서 (X, Y=높이, Z) 의 실치수.
        $base = $m.size_cm
        if (-not $base) { throw ("manifest 에 size_cm 이 없다: " + $m.mesh) }
        $sx = [double]$base[0] * $inst.scale[0]
        $sy = [double]$base[1] * $inst.scale[1]
        $sz = [double]$base[2] * $inst.scale[2]
        $json += New-OvdrMeshPartJson -Name ("KRMM_" + $inst.name) -ObjectKey $k `
                   -MeshId "ovdrassetid://$($resolved[$m.mesh])" -TextureId $t `
                   -PX ([double]$inst.engine_pos[0] + $Dx) `
                   -PY ([double]$inst.engine_pos[1] + $Dy) `
                   -PZ ([double]$inst.engine_pos[2] + $Dz) `
                   -OX ([double]$inst.pitch_deg) -OY ([double]$inst.yaw_deg) -OZ ([double]$inst.roll_deg) `
                   -SX $sx -SY $sy -SZ $sz `
                   -Material 'Basic' -CanCollide $false -CastShadow $true
    }
}
Write-Host ("MeshPart {0} 개 생성" -f $json.Count)
$text = Add-OvdrInstances -Text $text -InstanceJson $json -ParentType 'Model' -ParentName 'KRM_Palace' -NewKeyIndex $k
$null = $text | ConvertFrom-Json
$null = Backup-OvdrLevel -Path $LevelPath -Tag 'BEFORE_KRM_MESH'
Write-OvdrText -Text $text -Path $LevelPath
Publish-OvdrLevel
