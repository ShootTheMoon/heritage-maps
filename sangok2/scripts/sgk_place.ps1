# SGK(산곡 II) 를 onlyoneshot 레벨에 넣는다 — 이 PC(HSP) 용. 명세서 6절(Studio 절차)의 이식판.
#
#   이 PC 에는 overdare_mesh_bulk_import / overdare_create_instances RPC 가 없다.
#   FBX 44개는 Studio GUI 에서 사람이 벌크 임포트하고, 그 전후만 여기서 자동화한다.
#   MeshPart.Size 는 실치수 cm (2026-08-27 KRM 에서 실측: 100 을 넣으면 27 m 방이 1 m 가 된다).
#
#   순서:
#     1) Studio 에서 onlyoneshot 열기 (플레이테스트 정지)
#     2) .\sgk_place.ps1 -Snapshot                  <- 임포트 직전. 기존 에셋 id 를 before_ids.txt 로
#     3) Studio GUI: 06_OVERDARE\IMPORT_BATCHES.md 순서대로 벌크 임포트 (세션당 <=12 파일, 사이에 Studio 재시작)
#     4) .\sgk_place.ps1 -Resolve                   <- 이름 대조 + asset_ids.json + _place\*.json / items_static.json
#     5) .\sgk_place.ps1 -Probe -Apply              <- 타일 1 + 소나무 1 + 콜리전 슬랩 3 만 넣고 플레이테스트로 방향 확인
#     6) .\sgk_place.ps1 -Apply                     <- 전체 (Model + 경계 4 + 스폰 2 + 정적 + 552 + 콜리전 1,770)
#     7) .\sgk_place.ps1 -Lua -Apply                <- MapService_1 에 sgk 항목 추가
#   -Apply 없이 실행하면 레벨 파일만 고치고 Studio 반영(level.apply/save)은 하지 않는다.
param(
    [switch] $Check,
    [switch] $Snapshot,
    [switch] $Resolve,
    [switch] $Probe,
    [switch] $Lua,
    [switch] $Apply,
    [string] $LevelPath = "$env:USERPROFILE\Desktop\onlyonetap\onlyoneshot.ovdrjm",   # 프로젝트 폴더 onlyoneshot -> onlyonetap (2026-09-06). 실제 경로는 ~\.overdare\mcp\studios\*.json 의 cwd
    [string] $Bridge = "$env:USERPROFILE\Desktop\blender\gyeongbokgung"
)
$ErrorActionPreference = 'Stop'
. "$Bridge\ovdr_rpc.ps1"
. "$Bridge\ovdr_level.ps1"
. "$Bridge\ovdr_script.ps1"

$ROOT = Split-Path $PSScriptRoot -Parent
$OVD  = Join-Path $ROOT '06_OVERDARE'
$PROJ = Split-Path $LevelPath -Parent
$PY   = "C:\Program Files (x86)\Steam\steamapps\common\Blender\5.2\python\bin\python.exe"   # 시스템 파이썬이 없어 Blender 내장 파이썬
$REUSE = @{ MST_EULALIA = @('MST_EULALIA_overdare', 'ATL_EULALIA'); MST_ARTEMISIA = @('MST_ARTEMISIA_overdare', 'ATL_ARTEMISIA')
            MST_ROCK_A = @('MST_ROCK_A_overdare', 'ROCK_A'); MST_ROCK_D = @('MST_ROCK_D_overdare', 'ROCK_D'); MST_ROCK_E = @('MST_ROCK_E_overdare', 'ROCK_E') }

function Read-AssetTable {
    $raw = [IO.File]::ReadAllBytes("$PROJ\UGCLocalAssetTable.json")
    $txt = if ($raw[0] -eq 0xFF -and $raw[1] -eq 0xFE) { [Text.Encoding]::Unicode.GetString($raw, 2, $raw.Length - 2) } else { [Text.Encoding]::UTF8.GetString($raw) }
    return ($txt | ConvertFrom-Json).localAssetList
}

if ($Check) {
    # 임포트 전: 파일 stem 이 이미 테이블에 있으면 재임포트(중복 발행) 위험 → 경고
    $t = Read-AssetTable; $have = @{}
    foreach ($p in $t.PSObject.Properties) { $have[$p.Value.name] = $true }
    $man = Get-Content (Join-Path $OVD 'manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    $n = 0; $dup = @()
    foreach ($p in $man.PSObject.Properties) {
        if (-not $p.Value.file) { continue }
        $n++; $stem = [IO.Path]::GetFileNameWithoutExtension($p.Value.file)
        if ($have.ContainsKey($stem) -or $have.ContainsKey("${stem}_overdare")) { $dup += $stem }
    }
    Write-Host ("files {0}, already in table: {1}" -f $n, $dup.Count) -ForegroundColor $(if ($dup.Count) { 'Red' } else { 'Green' })
    $dup | ForEach-Object { "  SKIP (already imported): $_" }
    return
}
if ($Snapshot) {
    $t = Read-AssetTable
    $ids = @($t.PSObject.Properties.Name)
    $ids | Set-Content (Join-Path $OVD 'before_ids.txt') -Encoding UTF8
    Write-Host ("before_ids.txt: {0} assets" -f $ids.Count) -ForegroundColor Green
    return
}

# ---------------------------------------------------------------- Resolve
if ($Resolve) {
    $man = Get-Content (Join-Path $OVD 'manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    $t = Read-AssetTable
    $before = @{}
    $bf = Join-Path $OVD 'before_ids.txt'
    if (Test-Path $bf) { Get-Content $bf -Encoding UTF8 | ForEach-Object { $before[$_] = $true } } else { Write-Warning 'before_ids.txt missing: matching by name over the whole table' }
    $meshNew = @{}; $texNew = @{}; $meshAll = @{}; $texAll = @{}
    foreach ($p in $t.PSObject.Properties) {
        $v = $p.Value; $n = $v.name
        if ($v.worldAssetType -eq 'STATIC_MESH') {
            if (-not $meshAll.ContainsKey($n)) { $meshAll[$n] = $v.contentId }
            if (-not $before.ContainsKey($p.Name) -and -not $meshNew.ContainsKey($n)) { $meshNew[$n] = $v.contentId }
        } elseif ($v.worldAssetType -eq 'TEXTURE') {
            if (-not $texAll.ContainsKey($n)) { $texAll[$n] = $v.contentId }
            if (-not $before.ContainsKey($p.Name) -and -not $texNew.ContainsKey($n)) { $texNew[$n] = $v.contentId }
        }
    }
    Write-Host ("new STATIC_MESH {0} / new TEXTURE {1}" -f $meshNew.Count, $texNew.Count)
    $out = [ordered]@{}; $miss = @()
    foreach ($p in $man.PSObject.Properties) {
        $name = $p.Name; $rec = $p.Value
        if ($REUSE.ContainsKey($name)) {
            $mn = $REUSE[$name][0]; $tn = $REUSE[$name][1]
            if ($meshAll.ContainsKey($mn) -and $texAll.ContainsKey($tn)) { $out[$name] = @{ meshId = $meshAll[$mn]; textureId = $texAll[$tn] } }
            else { $miss += "$name(reuse $mn/$tn)" }
            continue
        }
        $stem = [IO.Path]::GetFileNameWithoutExtension($rec.file)
        $mh = @($stem, "${stem}_overdare") | Where-Object { $meshNew.ContainsKey($_) } | Select-Object -First 1
        $tn = if ($rec.mats.Count) { $rec.mats[0] } else { $null }
        $th = @($tn, "${tn}_overdare", $stem, "${stem}_overdare") | Where-Object { $_ -and $texNew.ContainsKey($_) } | Select-Object -First 1
        $mid = if ($mh) { $meshNew[$mh] } else { $null }; $tid = if ($th) { $texNew[$th] } else { $null }
        if (-not $mid) {   # 이전 라운드에 이미 올라간 파일: 전체 테이블에서 (SGK_/MST_ 이름은 유일함을 -Check 로 확인했다)
            $mh = @($stem, "${stem}_overdare") | Where-Object { $meshAll.ContainsKey($_) } | Select-Object -First 1
            if ($mh) { $mid = $meshAll[$mh] }
        }
        if (-not $tid) {
            $th = @($tn, "${tn}_overdare", $stem, "${stem}_overdare") | Where-Object { $_ -and $texAll.ContainsKey($_) } | Select-Object -First 1
            if ($th) { $tid = $texAll[$th] }
        }
        if ($mid -and $tid) { $out[$name] = @{ meshId = $mid; textureId = $tid } } else { $miss += "$name(mesh=$mh tex=$th)" }
    }
    # 로컬 테이블에서 사라진 에셋의 수동 매핑 (2026-09-06 3차 세션1: Studio 재시작 때 프로젝트 재동기화로 테이블·로컬 uasset 유실, 서버엔 남아 있어 build.zip 에서 이름을 읽어 복구)
    $ovf = Join-Path $OVD 'asset_ids_override.json'
    if (Test-Path $ovf) {
        $ov = Get-Content $ovf -Raw -Encoding UTF8 | ConvertFrom-Json; $fixed = @()
        foreach ($p in $ov.PSObject.Properties) {
            if (-not $out.Contains($p.Name)) { $out[$p.Name] = @{ meshId = $p.Value.meshId; textureId = $p.Value.textureId }; $fixed += $p.Name }
        }
        $miss = @($miss | Where-Object { $fixed -notcontains (($_ -split '\(')[0]) })
        if ($fixed.Count) { Write-Host ('override (server-recovered ids): ' + ($fixed -join ', ')) -ForegroundColor Yellow }
    }
    [IO.File]::WriteAllText((Join-Path $OVD 'asset_ids.json'), ($out | ConvertTo-Json -Depth 4), [Text.UTF8Encoding]::new($false))   # BOM 없이 (파이썬이 읽는다)
    Write-Host ("asset_ids.json: {0}/{1} resolved" -f $out.Count, @($man.PSObject.Properties).Count) -ForegroundColor Green
    if ($miss.Count) {
        Write-Host ("MISSING: " + ($miss -join ', ')) -ForegroundColor Red
        Write-Host 'new mesh names:'; $meshNew.Keys | Sort-Object | ForEach-Object { "  $_" }
        Write-Host 'new texture names:'; $texNew.Keys | Sort-Object | ForEach-Object { "  $_" }
        return
    }
    Push-Location $PSScriptRoot
    & $PY sgk_placements.py csv
    & $PY sgk_placements.py items
    Pop-Location
    return
}

# ---------------------------------------------------------------- Lua
if ($Lua) {
    $src = Get-OvdrScriptSource -Name 'MapService' -Path $LevelPath   # 레벨 노드 이름은 MapService (Lua 폴더 사본은 MapService_1.lua)
    $entry = [IO.File]::ReadAllText((Join-Path $OVD 'MapService_sgk.lua'), [Text.UTF8Encoding]::new($false)).TrimEnd()
    if ($src -match '(?m)^\s*sgk = \{') {
        # 기존 sgk 항목을 통째로 교체 (맵 이동·조명값 변경 반영, 2026-09-06). 블록 = 들여쓰기 1탭의 'sgk = {' 부터 같은 들여쓰기의 '},' 까지
        $m = [regex]::Match($src, '(?ms)^\tsgk = \{.*?(?=^\t\w+ = \{|^\}\s*$)')   # 다음 최상위 항목(jsn = { 등) 직전까지. 예전 패턴(탭·개행 리터럴)은 jsn 항목까지 삼켰다 (2026-09-07)
        if (-not $m.Success) { throw 'sgk block not found for replacement' }
        $src = $src.Substring(0, $m.Index) + $entry + "`n" + $src.Substring($m.Index + $m.Length)
        $tmp = Join-Path $env:TEMP 'MapService_1_sgk.lua'
        [IO.File]::WriteAllText($tmp, $src, [Text.UTF8Encoding]::new($false))
        $null = Backup-OvdrLevel -Path $LevelPath -Tag 'BEFORE_SGK_LUA'
        Set-OvdrScriptSource -Name 'MapService' -File $tmp -Path $LevelPath
        if (Test-Path "$PROJ\Lua") { Copy-Item $tmp "$PROJ\Lua\MapService_1.lua" -Force }
        Write-Host 'MapService_1: sgk entry replaced' -ForegroundColor Green
    }
    else {
        # M.MAPS = { 바로 뒤에 항목 삽입, M.ORDER 에 "sgk" 추가
        $src = [regex]::new('(?m)^(M\.MAPS\s*=\s*\{)').Replace($src, ('$1' + "`n" + $entry.Replace('$', '$$')), 1)
        $src = [regex]::new('(?m)^(M\.ORDER\s*=\s*\{[^}]*?)(\s*\})').Replace($src, '$1, "sgk"$2', 1)
        if ($src -notmatch '"sgk"') { throw 'M.ORDER patch failed' }
        $tmp = Join-Path $env:TEMP 'MapService_1_sgk.lua'
        [IO.File]::WriteAllText($tmp, $src, [Text.UTF8Encoding]::new($false))
        $null = Backup-OvdrLevel -Path $LevelPath -Tag 'BEFORE_SGK_LUA'
        Set-OvdrScriptSource -Name 'MapService' -File $tmp -Path $LevelPath
        if (Test-Path "$PROJ\Lua") { Copy-Item $tmp "$PROJ\Lua\MapService_1.lua" -Force }
        Write-Host 'MapService_1: sgk entry + ORDER added' -ForegroundColor Green
    }
    if ($Apply) { Publish-OvdrLevel }
    return
}

# ---------------------------------------------------------------- Place (Probe / full)
function Load-Items([string] $file) { return @(Get-Content $file -Raw -Encoding UTF8 | ConvertFrom-Json) }

function Get-SpawnTemplate([string] $text, [string] $name) {
    # JSN_Spawn_Red/Blue 의 TeamColor/BrickColor 를 그대로 복사한다 (TeamServer 가 색으로 팀을 판단)
    $m = [regex]::Match($text, '"InstanceType":\s*"SpawnLocation"[\s\S]{0,6000}?"Name":\s*"' + [regex]::Escape($name) + '"')
    if (-not $m.Success) { throw "spawn template not found: $name" }
    $start = $text.LastIndexOf('{', $m.Index); $depth = 0; $end = -1
    for ($i = $start; $i -lt $text.Length; $i++) {
        if ($text[$i] -eq '{') { $depth++ }
        elseif ($text[$i] -eq '}') { $depth--; if ($depth -eq 0) { $end = $i; break } }
    }
    return $text.Substring($start, $end - $start + 1)
}

function New-SgkSpawnJson([string] $tpl, [string] $name, [int] $key, [double[]] $pos) {
    $j = $tpl
    # 주의: [regex]::Replace($s,$p,$r,1) 의 4번째 인자는 개수가 아니라 RegexOptions 다 -> 인스턴스 메서드로 첫 1개만 바꾼다
    $j = [regex]::new('"ActorGuid":\s*"[^"]*"').Replace($j, ('"ActorGuid": "' + (New-OvdrGuid) + '"'), 1)
    $j = [regex]::new('"ObjectKey":\s*\d+').Replace($j, "`"ObjectKey`": $key", 1)
    $j = [regex]::new('"Name":\s*"[^"]*"').Replace($j, "`"Name`": `"$name`"", 1)   # 첫 Name = 인스턴스 이름 (BrickColor/TeamColor 의 Name 은 뒤에 온다)
    $j = [regex]::new('"CFrame":\s*\{\s*"ObjectType":\s*"CFrame",\s*"Position":\s*\{[^}]*\}').Replace($j, ('"CFrame": { "ObjectType": "CFrame", "Position": ' + (New-OvdrVector3 $pos[0] $pos[1] $pos[2])), 1)
    if ($j -match '"LuaChildren"') { $j = [regex]::new(',?\s*"LuaChildren":\s*\[[\s\S]*\]\s*(?=\}$)').Replace($j, '', 1) }
    if (([regex]::Matches($j, '"Name":\s*"' + [regex]::Escape($name) + '"')).Count -ne 1) { throw "spawn name replace went wrong: $name" }
    return $j
}

function New-SgkMeshPart($it, [int] $key) {
    $p = $it.props
    $o = if ($p.orientation) { $p.orientation } else { @(0, 0, 0) }
    $cs = if ($null -ne $p.castShadow) { [bool]$p.castShadow } else { $true }
    $tr = if ($p.raw -and $null -ne $p.raw.Transparency) { [double]$p.raw.Transparency } else { 0 }
    $ds = if ($p.raw -and $null -ne $p.raw.DoubleSided) { [bool]$p.raw.DoubleSided } else { $false }
    $j = (New-OvdrMeshPartJson -Transparency $tr -Name $it.name -ObjectKey $key -MeshId ("ovdrassetid://" + $p.meshId) -TextureId ("ovdrassetid://" + $p.raw.TextureId) `
        -PX ([double]$p.position[0]) -PY ([double]$p.position[1]) -PZ ([double]$p.position[2]) `
        -OX ([double]$o[0]) -OY ([double]$o[1]) -OZ ([double]$o[2]) `
        -SX ([double]$p.size[0]) -SY ([double]$p.size[1]) -SZ ([double]$p.size[2]) `
        -Material 'Basic' -CanCollide $false -CastShadow $cs -DoubleSided $ds)
    if ($p.unit) {
        # 실제 UnitExtent 로 교체 (자리표시자 ±50 이면 Size/100 배율이 메시 로드 후에도 남아 40 m 타일이 1.6 km 로 렌더됐다, 2026-09-06)
        $j = [regex]::new('"UnitExtent":\s*\{[^}]*\}').Replace($j, ('"UnitExtent": ' + (New-OvdrVector3 ([double]$p.unit[0]) ([double]$p.unit[1]) ([double]$p.unit[2]))), 1)
    }
    return $j
}

function New-SgkPart($it, [int] $key) {
    $p = $it.props
    $o = if ($p.orientation) { $p.orientation } else { @(0, 0, 0) }
    $raw = $p.raw
    $tr = if ($raw -and $null -ne $raw.Transparency) { [double]$raw.Transparency } elseif ($null -ne $p.transparency) { [double]$p.transparency } else { 0 }
    $cc = if ($raw -and $null -ne $raw.CanCollide) { [bool]$raw.CanCollide } elseif ($null -ne $p.canCollide) { [bool]$p.canCollide } else { $true }
    $mat = if ($raw -and $raw.Material) { $raw.Material } else { 'Basic' }
    $rgb = if ($p.color) { $p.color } else { @(160, 160, 160) }
    return (New-OvdrPartJson -Name $it.name -ObjectKey $key `
        -PX ([double]$p.position[0]) -PY ([double]$p.position[1]) -PZ ([double]$p.position[2]) `
        -OX ([double]$o[0]) -OY ([double]$o[1]) -OZ ([double]$o[2]) `
        -SX ([double]$p.size[0]) -SY ([double]$p.size[1]) -SZ ([double]$p.size[2]) `
        -R ([int]$rgb[0]) -G ([int]$rgb[1]) -B ([int]$rgb[2]) -Material $mat -CanCollide $cc -Transparency $tr)
}

$setup   = Get-Content (Join-Path $OVD 'studio_setup.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$bounds  = Load-Items (Join-Path $OVD 'items_bounds.json')
$statics = Load-Items (Join-Path $OVD 'items_static.json')
$inst = @(); Get-ChildItem (Join-Path $OVD '_place\place_*.json') | Sort-Object Name | ForEach-Object { $inst += Load-Items $_.FullName }
$col  = @(); Get-ChildItem (Join-Path $OVD '_collision\items_col_*.json') | Sort-Object Name | ForEach-Object { $col += Load-Items $_.FullName }
Write-Host ("loaded: bounds {0}, statics {1}, instances {2}, collision {3}" -f $bounds.Count, $statics.Count, $inst.Count, $col.Count)

if ($Probe) {
    # 명세서 5번 프로브. Size 의미론은 이 PC 에서 이미 확정(실치수) -> 남은 건 (a) 타일 위치·크기 (c) 슬랩 기울기 부호
    $statics = @($statics | Where-Object { $_.name -eq 'STA_TER_11' })
    $inst    = @(($inst | Where-Object { $_.name -like 'SGK_Pine_*' } | Select-Object -First 1), ($inst | Where-Object { $_.name -like 'SGK_Und_Fern_*' } | Select-Object -First 1), ($inst | Where-Object { $_.name -eq 'SGK_Pavilion' }))
    $flat  = $col | Where-Object { $_.name -like 'COL_TER_*' -and [math]::Abs([double]$_.props.orientation[0]) -lt 1 -and [math]::Abs([double]$_.props.orientation[2]) -lt 1 } | Select-Object -First 1
    $slope = $col | Where-Object { $_.name -like 'COL_TER_*' -and ([math]::Abs([double]$_.props.orientation[0]) -gt 20 -or [math]::Abs([double]$_.props.orientation[2]) -gt 20) } | Select-Object -First 1
    $steep = $col | Where-Object { $_.name -like 'COL_TER_*' -and ([math]::Abs([double]$_.props.orientation[0]) -gt 45 -or [math]::Abs([double]$_.props.orientation[2]) -gt 45) } | Select-Object -First 1
    $col = @(@($flat, $slope, $steep) | Where-Object { $_ })
    $desc = ($col | ForEach-Object { $_.name + ' ' + ($_.props.orientation -join '/') }) -join '; '
    Write-Host ("PROBE: tile {0}, pine {1}, slabs {2}" -f $statics.Count, $inst.Count, $desc) -ForegroundColor Cyan
}

$text = Read-OvdrText -Path $LevelPath
$redTpl  = Get-SpawnTemplate $text 'SGK_Spawn_Red'
$blueTpl = Get-SpawnTemplate $text 'SGK_Spawn_Blue'
$before = $text.Length
$text = Remove-OvdrInstancesByName -Text $text -NamePrefix 'SGK_'     # 재실행 대비 (Model SGK_Sangok 이 자식째 빠진다)
$text = Remove-OvdrInstancesByName -Text $text -NamePrefix 'COL_TER_'
$text = Remove-OvdrInstancesByName -Text $text -NamePrefix 'COL_'
if ($text.Length -ne $before) { Write-Host ("removed old SGK nodes: {0} chars" -f ($before - $text.Length)) -ForegroundColor Yellow }
$key = Get-OvdrKeyIndex -Text $text; $k = $key

$kids = New-Object System.Collections.Generic.List[string]
foreach ($b in $bounds)  { $k++; $kids.Add((New-SgkPart $b $k)) }
$k++; $kids.Add((New-SgkSpawnJson $redTpl  'SGK_Spawn_Red'  $k ([double[]]$setup.spawns_engine_cm.Red)))
$k++; $kids.Add((New-SgkSpawnJson $blueTpl 'SGK_Spawn_Blue' $k ([double[]]$setup.spawns_engine_cm.Blue)))
foreach ($s in $statics) { $k++; $kids.Add((New-SgkMeshPart $s $k)) }
foreach ($i in $inst)    { $k++; $kids.Add((New-SgkMeshPart $i $k)) }
foreach ($c in $col)     { $k++; $kids.Add((New-SgkPart $c $k)) }
$k++
$model = New-OvdrModelJson -Name 'SGK_Sangok' -ObjectKey $k
$model = $model -replace '"LuaChildren":\s*\[\s*\]', ('"LuaChildren": [' + "`r`n" + ($kids -join ",`r`n") + "`r`n" + ']')
$text = Add-OvdrInstances -Text $text -InstanceJson @($model) -ParentType 'Workspace' -NewKeyIndex $k
$null = $text | ConvertFrom-Json
Write-Host ("json ok. SGK_Sangok children={0}  keys {1}..{2}" -f $kids.Count, ($key + 1), $k) -ForegroundColor Green
$tag = if ($Probe) { 'BEFORE_SGK_PROBE' } else { 'BEFORE_SGK' }
$null = Backup-OvdrLevel -Path $LevelPath -Tag $tag
Write-OvdrText -Text $text -Path $LevelPath
Write-Host 'level written.' -ForegroundColor Green
if ($Apply) { Publish-OvdrLevel } else { Write-Host 'not applied (add -Apply, Studio must be open with onlyoneshot).' -ForegroundColor Yellow }
