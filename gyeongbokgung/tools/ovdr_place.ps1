# 매니페스트 → MeshPart 배치
#
#   . .\ovdr_place.ps1
#   Save-OvdrBeforeIds  -Out <dir>        # 임포트 직전
#   Place-OvdrManifest  -Dir <dir>        # 임포트 직후
#   Test-OvdrPlacement  -Dir <dir>        # 검증
#
# 에셋 매핑은 반드시 contentId 집합 차이로 한다. 이 프로젝트에는 이미
# 같은 이름의 에셋이 4개씩 있는 사례가 있어(F3) 이름 매칭은 엉뚱한 메시를
# 조용히 물어온다.

. (Join-Path $PSScriptRoot 'ovdr_rpc.ps1')
. (Join-Path $PSScriptRoot 'ovdr_level.ps1')

function Save-OvdrBeforeIds {
    param([Parameter(Mandatory)][string] $Dir)
    $proj = (Get-OvdrProject).cwd
    $t = Get-Content "$proj\UGCLocalAssetTable.json" -Raw -Encoding UTF8 | ConvertFrom-Json
    $ids = $t.localAssetList.PSObject.Properties.Name
    $ids | Set-Content (Join-Path $Dir 'before_ids.txt') -Encoding UTF8
    Write-Host "기존 에셋 $($ids.Count) 개 기록 -> $Dir\before_ids.txt"
}

function Get-OvdrAssetMap {
    <# expected_asset_name → contentId. 신규 에셋만 대상으로 한다. #>
    param([Parameter(Mandatory)][string] $Dir)
    $proj = (Get-OvdrProject).cwd
    $before = @{}
    Get-Content (Join-Path $Dir 'before_ids.txt') -Encoding UTF8 | ForEach-Object { $before[$_] = $true }
    $t = Get-Content "$proj\UGCLocalAssetTable.json" -Raw -Encoding UTF8 | ConvertFrom-Json

    $map = @{}
    $dupes = @()
    foreach ($p in $t.localAssetList.PSObject.Properties) {
        if ($before.ContainsKey($p.Name)) { continue }
        $v = $p.Value
        if ($v.worldAssetType -ne 'STATIC_MESH') { continue }
        if ($map.ContainsKey($v.name)) { $dupes += $v.name; continue }
        $map[$v.name] = $v.contentId
    }
    if ($dupes.Count) { Write-Warning "신규 에셋 중 이름 중복: $($dupes -join ', ')" }
    return $map
}

function Place-OvdrManifest {
    <#
      Scale 은 플랫폼 상면(FloorY)을 기준으로 궁궐 전체를 줄이거나 키운다.
      메시는 그대로 두고 MeshPart.Size 로 스케일하므로 재임포트가 필요 없다.
        X' = X * S
        Z' = Z * S
        Y' = (Y - FloorY) * S + FloorY      ← 지면 높이는 고정
        Size' = Size * S

      중요: 새 MeshPart JSON 의 UnitExtent 자리표시자는 축마다 ±50 이다.
      MeshId 가 로드되면 Studio 가 현재 배율을 유지한 채 실제 UnitExtent 를
      반영하므로, 초기 MeshPart Size 에 bbox 크기를 넣으면 bbox 가 한 번 더
      곱해진다. 초기 Size 는 축마다 100 * S 를 넣어야 최종 크기가
      실제 bbox 전체 크기 * S 가 된다.
    #>
    param(
        [Parameter(Mandatory)][string] $Dir,
        [string] $ParentModel = 'Gyeongbokgung',
        [double] $Scale = 1.0,
        [double] $FloorY = 5000.0,
        [switch] $Replace,
        [switch] $Partial,
        [switch] $WhatIf
    )
    $man = Get-Content (Join-Path $Dir 'manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    $map = Get-OvdrAssetMap -Dir $Dir
    Write-Host "신규 STATIC_MESH 에셋: $($map.Count) 개"

    # 메시가 하나뿐인 FBX 는 에셋 이름에 메시명 접미사가 붙지 않는다
    # (SJJ_03_SJJ_GABLE_785203 이 아니라 그냥 SJJ_03). 양쪽을 다 받는다.
    $perFile = @{}
    foreach ($m in $man.meshes) { $perFile[$m.file] = 1 + [int]$perFile[$m.file] }
    $resolved = @{}
    $missing = @()
    foreach ($m in $man.meshes) {
        $cand = @($m.expected_asset_name)
        if ($perFile[$m.file] -eq 1) { $cand += ($m.file -replace '\.fbx$', '') }
        $hit = $cand | Where-Object { $map.ContainsKey($_) } | Select-Object -First 1
        if ($hit) { $resolved[$m.slug] = $map[$hit] } else { $missing += $m.expected_asset_name }
    }
    if ($missing.Count) {
        Write-Host "매칭 실패 $($missing.Count) 건 (누락 팩: $((($missing | ForEach-Object { ($_ -split '_')[0..1] -join '_' }) | Sort-Object -Unique) -join ', '))" -ForegroundColor Yellow
        if (-not $Partial) {
            $missing | Select-Object -First 10 | ForEach-Object { "   $_" }
            Write-Host "해당 FBX 를 임포트했는지, Name 이 팩 파일명과 같은지 확인하라." -ForegroundColor Yellow
            Write-Host "들어온 것만 먼저 배치하려면 -Partial 을 붙여라." -ForegroundColor Yellow
            return
        }
    }
    $todo = @($man.meshes | Where-Object { $resolved.ContainsKey($_.slug) })
    Write-Host "배치 대상: $($todo.Count) / $($man.meshes.Count) 메시" -ForegroundColor Green
    if ($WhatIf) { return }

    $path = Get-OvdrLevelPath
    $txt  = Read-OvdrText $path
    if ($Replace) {
        foreach ($m in $man.meshes) { $txt = Remove-OvdrInstancesByName -Text $txt -NamePrefix $m.slug }
        foreach ($p in $man.parts)  { $txt = Remove-OvdrInstancesByName -Text $txt -NamePrefix $p.name }
    }
    $ki = Get-OvdrKeyIndex $txt
    $S = $Scale

    $pal = $man.palette
    $json = @(); $k = $ki
    foreach ($m in $todo) {
        $c = $pal.($m.material_key)
        $rgb = if ($c) { $c.color3 } else { @(180, 180, 180) }
        $mat = if ($c) { $c.material } else { 'Basic' }
        $tr  = if ($c) { $c.transparency } else { 0 }
        # 스캔 모델(KCISA)은 색이 전부 텍스처 아틀라스에 있어서 팔레트 단색으로는
        # 회색 덩어리가 된다. 매니페스트에 texture_id 가 있으면 그걸 넘긴다.
        # 없으면 빈 문자열 — 경복궁처럼 material_key 단색으로 칠해진다.
        $tex = if ($m.PSObject.Properties['texture_id'] -and $m.texture_id) {
                   if ($m.texture_id -like 'ovdrassetid://*') { $m.texture_id }
                   else { "ovdrassetid://$($m.texture_id)" }
               } else { '' }
        # 회전은 항상 0 이다. 회전은 익스포트 때 matrix_world 로 메시에 구워
        # 넣으므로 여기서 돌릴 것이 없다. 계단만 180도 돌리던 패치가 있었으나
        # 그건 좌표계 Z 부호 문제의 증상을 가린 것이라 제거했다.
        $json += New-OvdrMeshPartJson -Name $m.slug -ObjectKey $k `
                   -MeshId "ovdrassetid://$($resolved[$m.slug])" `
                   -TextureId $tex `
                   -PX ($m.cframe_cm.X * $S) `
                   -PY (($m.cframe_cm.Y - $FloorY) * $S + $FloorY) `
                   -PZ ($m.cframe_cm.Z * $S) `
                   -SX ($m.size_cm.X * $S) -SY ($m.size_cm.Y * $S) -SZ ($m.size_cm.Z * $S) `
                   -R $rgb[0] -G $rgb[1] -B $rgb[2] -Material $mat `
                   -Transparency $tr -CanCollide $true -CastShadow $true
        $k++
    }
    foreach ($p in $man.parts) {
        $c = $pal.($p.material_key)
        $rgb = if ($c) { $c.color3 } else { @(180, 180, 180) }
        $mat = if ($c) { $c.material } else { 'Basic' }
        $json += New-OvdrPartJson -Name $p.name -ObjectKey $k `
                   -PX ($p.cframe_cm.X * $S) `
                   -PY (($p.cframe_cm.Y - $FloorY) * $S + $FloorY) `
                   -PZ ($p.cframe_cm.Z * $S) `
                   -SX ($p.size_cm.X * $S) -SY ($p.size_cm.Y * $S) -SZ ($p.size_cm.Z * $S) `
                   -R $rgb[0] -G $rgb[1] -B $rgb[2] -Material $mat -CanCollide $true
        $k++
    }

    $new = Add-OvdrInstances -Text $txt -InstanceJson $json `
             -ParentType 'Model' -ParentName $ParentModel -NewKeyIndex $k
    try { $null = $new | ConvertFrom-Json } catch { Write-Host "JSON 깨짐: $($_.Exception.Message)" -ForegroundColor Red; return }

    Write-OvdrText -Text $new -Path $path
    $null = Invoke-OvdrRpc -Method 'level.apply'     -TimeoutSec 120
    $null = Invoke-OvdrRpc -Method 'level.save.file' -TimeoutSec 180
    Write-Host "배치 완료: MeshPart $($todo.Count) + Part $($man.parts.Count)  (scale $S)" -ForegroundColor Green
}

function Test-OvdrPlacement {
    <# 레벨 파일을 다시 읽어 매니페스트와 대조한다 (V1~V15 축약). #>
    param(
        [Parameter(Mandatory)][string] $Dir,
        [double] $TolCm = 1.0,
        [double] $Scale = 1.0,
        [double] $FloorY = 5000.0
    )
    $man = Get-Content (Join-Path $Dir 'manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    $txt = Read-OvdrText
    $j = $txt | ConvertFrom-Json
    function Walk($n) { $n; if ($n.LuaChildren) { foreach ($c in $n.LuaChildren) { Walk $c } } }
    $placed = @{}
    foreach ($n in (Walk $j.Root)) {
        if ($n.InstanceType -in 'MeshPart', 'Part' -and $n.Name) { $placed[$n.Name] = $n }
    }

    $fail = 0
    $expect = @($man.meshes) + @($man.parts)
    foreach ($m in $expect) {
        $nm = if ($m.slug) { $m.slug } else { $m.name }
        $p = $placed[$nm]
        if (-not $p) { Write-Host "V1 누락: $nm" -ForegroundColor Red; $fail++; continue }
        $ex = $m.cframe_cm.X * $Scale
        $ey = ($m.cframe_cm.Y - $FloorY) * $Scale + $FloorY
        $ez = $m.cframe_cm.Z * $Scale
        $dp = [math]::Max([math]::Max([math]::Abs($p.CFrame.Position.X - $ex),
                                      [math]::Abs($p.CFrame.Position.Y - $ey)),
                          [math]::Abs($p.CFrame.Position.Z - $ez))
        if ($dp -gt $TolCm) { Write-Host ("V2 위치 오차 {0}: {1:N2} cm" -f $nm, $dp) -ForegroundColor Red; $fail++ }
        # V3 — 회전은 예외 없이 0 이어야 한다. 특정 부재만 돌려서 맞추면
        # 좌표계 오류가 검증을 통과해 버린다.
        $orientationError = [math]::Max(
            [math]::Max([math]::Abs($p.CFrame.Orientation.X),
                        [math]::Abs($p.CFrame.Orientation.Y)),
            [math]::Abs($p.CFrame.Orientation.Z)
        )
        if ($orientationError -gt 0.5) {
            Write-Host ("V3 회전이 0 이 아님 {0}: 최대 {1:N1}도" -f $nm, $orientationError) -ForegroundColor Red
            $fail++
        }
        # V4 — 세 축 크기. size_cm 이 없는 항목(초기 매니페스트)은 건너뛴다.
        if ($null -ne $m.size_cm) {
            # PowerShell 은 쉼표가 * 보다 우선순위가 높다.
            # @(a * $s, b * $s) 는 a * ($s, b) 로 파싱되므로 원소마다 괄호를 씌운다.
            $exp = @(([double]$m.size_cm.X * $Scale),
                     ([double]$m.size_cm.Y * $Scale),
                     ([double]$m.size_cm.Z * $Scale))
            $act = @(([double]$p.Size.X), ([double]$p.Size.Y), ([double]$p.Size.Z))
            $sizeError = 0.0
            for ($axis = 0; $axis -lt 3; $axis++) {
                if ($exp[$axis] -le 0) { continue }
                $e = [math]::Abs($act[$axis] - $exp[$axis]) / [math]::Max(1.0, $exp[$axis])
                $sizeError = [math]::Max($sizeError, $e)
            }
            if ($sizeError -gt 0.005) {
                Write-Host ("V4 XYZ 크기 오차 {0}: 최대 {1:P2}" -f $nm, $sizeError) -ForegroundColor Red
                $fail++
            }
        }
        if ($p.InstanceType -eq 'MeshPart') {
            # V5 — Size / (2|UnitExtent|) 가 의도한 배율과 같은가.
            # 이 비율이 곧 메시에 적용된 실제 스케일이다.
            # V5 — Size / (2|UnitExtent|) 가 곧 메시에 실제로 먹은 배율이다.
            # 단, UnitExtent 는 스튜디오가 메시를 읽어야 채워진다. 스튜디오가
            # 꺼진 상태로 파일만 쓰면 자리표시자(50,50,-50)가 남아 전건 오탐이
            # 나므로, 자리표시자로 보이면 판정을 보류한다.
            $ue = 2 * [math]::Abs($p.UnitExtent.X)
            $placeholder = ([math]::Abs([math]::Abs($p.UnitExtent.X) - 50) -lt 0.01 -and
                            [math]::Abs([math]::Abs($p.UnitExtent.Y) - 50) -lt 0.01 -and
                            [math]::Abs([math]::Abs($p.UnitExtent.Z) - 50) -lt 0.01)
            if ($ue -gt 1 -and -not $placeholder) {
                $applied = $p.Size.X / $ue
                if ([math]::Abs($applied - $Scale) / $Scale -gt 0.01) {
                    Write-Host ("V5 배율 불일치 {0}: 적용 {1:N3} vs 의도 {2:N3}" -f $nm, $applied, $Scale) -ForegroundColor Yellow
                }
            } elseif ($placeholder) { $script:v5skip = 1 + [int]$script:v5skip }
            if (-not $p.MeshId) { Write-Host "V6 MeshId 비어 있음: $nm" -ForegroundColor Red; $fail++ }
            if (-not $p.CanCollide -or $p.CollisionProfile -ne 'BlockAll') {
                Write-Host "V7 충돌 비활성: $nm" -ForegroundColor Red
                $fail++
            }
        }
    }

    # V6 — 서로 다른 슬러그가 같은 MeshId 를 쓰면 안 된다
    $byMesh = @{}
    foreach ($m in $man.meshes) {
        $p = $placed[$m.slug]
        if ($p -and $p.MeshId) {
            if ($byMesh.ContainsKey($p.MeshId)) { Write-Host "V6 MeshId 중복: $($m.slug) 와 $($byMesh[$p.MeshId])" -ForegroundColor Red; $fail++ }
            else { $byMesh[$p.MeshId] = $m.slug }
        }
    }

    # V8 — 좌우 대칭 (X 합 ≈ 0)
    $sx = ($expect | ForEach-Object { $_.cframe_cm.X } | Measure-Object -Sum).Sum
    Write-Host ("V8 X 합계 = {0:N1} cm (0 근처여야 함)" -f $sx)

    if ($script:v5skip) {
        Write-Host ("V5 보류 {0} 건 — 스튜디오가 레벨을 읽어야 UnitExtent 가 채워진다. 스튜디오를 켜고 저장한 뒤 다시 검증할 것." -f $script:v5skip) -ForegroundColor Yellow
        $script:v5skip = 0
    }
    if ($fail -eq 0) { Write-Host "검증 통과: $($expect.Count) 개 전부 일치" -ForegroundColor Green }
    else { Write-Host "검증 실패 $fail 건" -ForegroundColor Red }
    return $fail
}
