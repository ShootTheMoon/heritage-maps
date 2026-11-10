# JSN_Sangok — 에셋 발행 추적과 ID 매핑
#
#   . .\jsn_assets.ps1
#   Save-JsnBefore                 # ← Bulk Import 시작 전에 한 번
#   ... Studio 에서 FBX 30개를 하나씩 임포트 ...
#   Build-JsnAssetIds              # ← 끝난 뒤. asset_ids_local.json 을 만든다
#
# 왜 이름 매핑이 안전한가:
#   기존 프로젝트 에셋 3,019개 중 아래 57개 이름과 겹치는 것이 0건임을 확인했다.
#   그래도 before 스냅샷으로 신규만 걸러 이중으로 막는다.
#   (경복궁 프로젝트에는 동명 에셋이 4개씩 있는 사례가 있었다 — ovdr_place.ps1 주석 참조)

$script:JsnRoot    = Split-Path $PSScriptRoot -Parent
$script:JsnOvdrDir = $PSScriptRoot
$script:JsnProject = "$env:USERPROFILE\Desktop\onlyoneshot"

# FBX → (메시 이름, 텍스처 이름). FBX 바이너리에서 임베드 텍스처명을 직접 뽑아 만든 표다.
# 검증: 고유 텍스처가 정확히 27장 나오고, 공유 관계(ROCK_A 3개 / WATER_FLAT 2개)가
# 원본 PC 의 asset_ids.json 과 일치한다.
$script:JsnTexOf = [ordered]@{
    'MST_ARTEMISIA'   = 'ATL_ARTEMISIA'
    'MST_EULALIA'     = 'ATL_EULALIA'
    'MST_PEBBLE'      = 'ROCK_A'
    'MST_PINE'        = 'ATL_PINE'
    'MST_ROCK_A'      = 'ROCK_A'
    'MST_ROCK_B'      = 'ROCK_B'
    'MST_ROCK_C'      = 'ROCK_C'
    'MST_ROCK_D'      = 'ROCK_D'
    'MST_ROCK_E'      = 'ROCK_E'
    'MST_ROCK_F'      = 'ROCK_F'
    'MST_ROCK_MASS'   = 'ROCK_MASS'
    'STA_STEPS'       = 'ROCK_A'
    'STA_StreamWater' = 'WATER_FLAT'
    'STA_TribWater'   = 'WATER_FLAT'
}
foreach ($r in 0..3) { foreach ($c in 0..3) { $script:JsnTexOf["STA_TER_$r$c"] = "TER_$r$c" } }

function Get-JsnProjectDir {
    param([string] $ProjectDir)
    if ($ProjectDir) { return $ProjectDir }
    # 스튜디오 매니페스트가 있으면 그걸 믿는다(열려 있는 프로젝트를 가리킨다)
    $mf = Get-ChildItem "$env:USERPROFILE\.overdare\mcp\studios\*.json" -ErrorAction SilentlyContinue |
          Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($mf) {
        $txt = Get-Content $mf.FullName -Raw -Encoding UTF8
        if ($txt -match '"cwd"\s*:\s*"([^"]+)"') {
            $cwd = $Matches[1] -replace '/', '\'
            if (Test-Path "$cwd\UGCLocalAssetTable.json") { return $cwd }
        }
    }
    return $script:JsnProject
}

function Get-JsnAssetTable {
    param([string] $ProjectDir)
    $p = Get-JsnProjectDir $ProjectDir
    $f = "$p\UGCLocalAssetTable.json"
    if (-not (Test-Path $f)) { throw "에셋 테이블을 찾지 못했다: $f" }
    return (Get-Content $f -Raw -Encoding UTF8 | ConvertFrom-Json)
}

function Save-JsnBefore {
    <# Bulk Import 시작 전 현재 에셋 id 전체를 기록한다. #>
    param([string] $ProjectDir)
    $t = Get-JsnAssetTable $ProjectDir
    $ids = @($t.localAssetList.PSObject.Properties.Name)
    $out = Join-Path $script:JsnOvdrDir 'before_ids.txt'
    $ids | Set-Content $out -Encoding UTF8
    Write-Host "임포트 전 에셋 $($ids.Count) 개 기록 -> $out" -ForegroundColor Cyan
}

function Get-JsnNewAssets {
    <# before 스냅샷 이후 새로 생긴 에셋만 돌려준다. #>
    param([string] $ProjectDir)
    $bf = Join-Path $script:JsnOvdrDir 'before_ids.txt'
    if (-not (Test-Path $bf)) { throw "before_ids.txt 가 없다. Save-JsnBefore 를 먼저 돌려라." }
    $before = @{}
    Get-Content $bf -Encoding UTF8 | ForEach-Object { if ($_) { $before[$_] = $true } }
    $t = Get-JsnAssetTable $ProjectDir
    $t.localAssetList.PSObject.Properties |
        Where-Object { -not $before.ContainsKey($_.Name) } |
        ForEach-Object {
            [pscustomobject]@{
                contentId = $_.Value.contentId
                name      = $_.Value.name
                type      = $_.Value.worldAssetType
                created   = $_.Value.createdTime
            }
        }
}

function Show-JsnImportState {
    <# 30개 중 무엇이 들어왔고 무엇이 남았는지. #>
    param([string] $ProjectDir)
    $new = @(Get-JsnNewAssets -ProjectDir $ProjectDir)
    $mesh = @{}; $tex = @{}
    foreach ($a in $new) {
        if ($a.type -eq 'STATIC_MESH') { $mesh[$a.name] = 1 + [int]$mesh[$a.name] }
        elseif ($a.type -eq 'TEXTURE')  { $tex[$a.name]  = 1 + [int]$tex[$a.name] }
    }
    $done = @(); $todo = @()
    foreach ($k in $script:JsnTexOf.Keys) { if ($mesh.ContainsKey($k)) { $done += $k } else { $todo += $k } }
    Write-Host "발행 완료 $($done.Count) / 30   남음 $($todo.Count)" -ForegroundColor Cyan
    if ($todo.Count) { Write-Host "  남은 것: $($todo -join ', ')" -ForegroundColor Yellow }
    $dupM = @($mesh.GetEnumerator() | Where-Object { $_.Value -gt 1 })
    if ($dupM) { Write-Host "  !! 메시 중복 발행: $(($dupM | ForEach-Object { "$($_.Key)x$($_.Value)" }) -join ', ')" -ForegroundColor Red }
    Write-Host "  신규 텍스처 $($tex.Count) 종 (기대 27)" -ForegroundColor Cyan
    return [pscustomobject]@{ done = $done; todo = $todo; meshes = $mesh; textures = $tex }
}

function Build-JsnAssetIds {
    <#
      신규 에셋에서 30개 메시 + 그 텍스처를 찾아 asset_ids_local.json 을 만든다.
      원본 PC 의 asset_ids.json 과 같은 형식 { "<키>": { meshId, textureId } }.
    #>
    param([string] $ProjectDir, [switch] $Partial)
    $new = @(Get-JsnNewAssets -ProjectDir $ProjectDir)
    if (-not $new) { throw "신규 에셋이 없다. 임포트가 됐는지, before 스냅샷 시점이 맞는지 확인하라." }

    $mesh = @{}; $tex = @{}; $dupes = @()
    foreach ($a in $new) {
        switch ($a.type) {
            'STATIC_MESH' { if ($mesh.ContainsKey($a.name)) { $dupes += "MESH:$($a.name)" } else { $mesh[$a.name] = $a.contentId } }
            'TEXTURE'     { if ($tex.ContainsKey($a.name))  { $dupes += "TEX:$($a.name)"  } else { $tex[$a.name]  = $a.contentId } }
        }
    }
    if ($dupes) {
        Write-Host "!! 중복 발행 감지 (같은 파일을 두 번 올렸을 수 있다):" -ForegroundColor Red
        ($dupes | Sort-Object -Unique) | ForEach-Object { Write-Host "   $_" -ForegroundColor Red }
        Write-Host "   먼저 발행된 쪽을 쓴다. Studio 에서 중복 에셋을 확인할 것." -ForegroundColor Yellow
    }

    $out = [ordered]@{}; $missM = @(); $missT = @()
    foreach ($k in $script:JsnTexOf.Keys) {
        $tn = $script:JsnTexOf[$k]
        if (-not $mesh.ContainsKey($k)) { $missM += $k; continue }
        if (-not $tex.ContainsKey($tn))  { $missT += "$k(tex $tn)" }
        $out[$k] = [ordered]@{
            meshId    = $mesh[$k]
            textureId = if ($tex.ContainsKey($tn)) { $tex[$tn] } else { '' }
        }
    }

    if ($missM) {
        Write-Host "메시 누락 $($missM.Count) 개: $($missM -join ', ')" -ForegroundColor Yellow
        if (-not $Partial) { Write-Host "전부 발행한 뒤 다시 돌리거나, 부분 진행하려면 -Partial 을 붙여라." -ForegroundColor Yellow; return }
    }
    if ($missT) { Write-Host "텍스처 누락: $($missT -join ', ')" -ForegroundColor Yellow }

    $f = Join-Path $script:JsnOvdrDir 'asset_ids_local.json'
    ($out | ConvertTo-Json -Depth 4) | Set-Content $f -Encoding UTF8
    Write-Host "asset_ids_local.json 작성: $($out.Count) / 30 -> $f" -ForegroundColor Green
    return $out
}
