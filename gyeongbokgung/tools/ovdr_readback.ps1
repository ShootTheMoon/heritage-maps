# 캘리브레이션 판독 — 임포트 결과를 레벨 파일에서 읽어 판정표에 대입한다.
#
#   . .\ovdr_readback.ps1
#   Show-OvdrInstances -NameLike 'CAL*'
#   Resolve-OvdrCalibration

. (Join-Path $PSScriptRoot 'ovdr_rpc.ps1')
. (Join-Path $PSScriptRoot 'ovdr_level.ps1')

function Get-OvdrTree {
    $txt = Read-OvdrText
    $j = $txt | ConvertFrom-Json
    function Walk($n) { $n; if ($n.LuaChildren) { foreach ($c in $n.LuaChildren) { Walk $c } } }
    return (Walk $j.Root)
}

function Show-OvdrInstances {
    param([string] $NameLike = '*', [string[]] $Types = @('MeshPart', 'Part', 'Model'))
    Get-OvdrTree |
        Where-Object { $_.InstanceType -in $Types -and $_.Name -like $NameLike } |
        ForEach-Object {
            [pscustomobject]@{
                Name = $_.Name
                Type = $_.InstanceType
                PX = $_.CFrame.Position.X; PY = $_.CFrame.Position.Y; PZ = $_.CFrame.Position.Z
                OX = $_.CFrame.Orientation.X; OY = $_.CFrame.Orientation.Y; OZ = $_.CFrame.Orientation.Z
                SX = $_.Size.X; SY = $_.Size.Y; SZ = $_.Size.Z
                UX = $_.UnitExtent.X; UY = $_.UnitExtent.Y; UZ = $_.UnitExtent.Z
                MeshId = $_.MeshId
                TextureId = $_.TextureId
            }
        }
}

function Resolve-OvdrTexturePath {
    <#
      텍스처 경로 판정 — 스캔 모델(KCISA)을 쓰려면 답이 필요한 질문:
      **FBX 에 텍스처를 구워 임포트하면 Studio 가 TextureId 를 채우는가?**

      경복궁은 material_key → 팔레트 단색으로만 칠했다(ovdr_place.ps1). 스캔은
      색이 전부 아틀라스에 있어서, TextureId 가 안 채워지면 회색 덩어리가 된다.

      쓰는 법: HPR_EMB1K.fbx(텍스처 구움)와 HPR_STRIP.fbx(대조군)를 스튜디오에
      임포트해 배치한 뒤

          . .\ovdr_readback.ps1
          Resolve-OvdrTexturePath
    #>
    param([string] $NameLike = 'HPR*')

    $rows = Show-OvdrInstances -NameLike $NameLike -Types @('MeshPart')
    if (-not $rows) {
        Write-Host "판독할 $NameLike MeshPart 가 없다. 임포트·배치가 됐는지 확인하라." -ForegroundColor Yellow
        return
    }
    $rows | Format-Table Name, MeshId, TextureId -AutoSize

    $withTex = @($rows | Where-Object { $_.TextureId })
    if ($withTex.Count -gt 0) {
        Write-Host ''
        Write-Host "=> 임포터가 TextureId 를 채운다. 스캔 모델을 그대로 쓸 수 있다." -ForegroundColor Green
        Write-Host "   익스포터를 path_mode='COPY' / embed_textures=True 로 바꾸고," -ForegroundColor Green
        Write-Host "   ovdr_place.ps1 이 매니페스트의 texture_id 를 -TextureId 로 넘기게 한다." -ForegroundColor Green
        $withTex | ForEach-Object { Write-Host "   $($_.Name) -> $($_.TextureId)" }
    } else {
        Write-Host ''
        Write-Host "=> TextureId 가 비어 있다. FBX 임베딩만으로는 색이 안 붙는다." -ForegroundColor Red
        Write-Host "   우회 1: textures\HPR_baseColor_1024.png 를 스튜디오에 에셋으로" -ForegroundColor Yellow
        Write-Host "           올리고 그 contentId 를 매니페스트 texture_id 에 적는다." -ForegroundColor Yellow
        Write-Host "           (Get-OvdrNewAssets 로 신규 에셋 id 를 뽑을 수 있다)" -ForegroundColor Yellow
        Write-Host "   우회 2: 재질별로 메시를 쪼개 경복궁처럼 material_key 단색으로 간다." -ForegroundColor Yellow
    }
}

function Get-OvdrNewAssets {
    <# 임포트 전 저장해 둔 id 목록과 비교해 신규 에셋만 돌려준다. (F3 대응: 이름 매칭 금지) #>
    param([Parameter(Mandatory)][string] $BeforeIdsFile)
    $proj = (Get-OvdrProject).cwd
    $before = @{}
    Get-Content $BeforeIdsFile -Encoding UTF8 | ForEach-Object { $before[$_] = $true }
    $t = Get-Content "$proj\UGCLocalAssetTable.json" -Raw -Encoding UTF8 | ConvertFrom-Json
    $t.localAssetList.PSObject.Properties | Where-Object { -not $before.ContainsKey($_.Name) } |
        ForEach-Object {
            [pscustomobject]@{
                contentId = $_.Value.contentId
                name      = $_.Value.name
                type      = $_.Value.worldAssetType
                created   = $_.Value.createdTime
            }
        }
}

function Resolve-OvdrCalibration {
    <#
      CAL_YBAR / CAL_XBAR 의 Position 부호로 축 매핑을,
      Size 로 단위 배수를 판정한다.
    #>
    $rows = Show-OvdrInstances -NameLike '*CAL_*'
    if (-not $rows) { Write-Host '판독할 CAL_* 인스턴스가 없다. 임포트가 됐는지 확인하라.'; return }

    $rows | Format-Table Name, PX, PY, PZ, SX, SY, SZ, OY -AutoSize

    $yb = $rows | Where-Object { $_.Name -like '*YBAR*' } | Select-Object -First 1
    $xb = $rows | Where-Object { $_.Name -like '*XBAR*' } | Select-Object -First 1
    $zb = $rows | Where-Object { $_.Name -like '*ZBAR*' } | Select-Object -First 1

    Write-Host ''
    if (-not $yb) { Write-Host 'YBAR 를 못 찾았다 — 이름이 뭉개졌을 수 있다. 위 표를 직접 보라.'; return }

    # 단위
    $lens = @($yb.SX, $yb.SY, $yb.SZ) | Sort-Object -Descending
    $long = $lens[0]
    $unit = switch ($true) {
        ({ $long -gt 550 -and $long -lt 650 }) { 'cm (기대값 600) OK'; break }
        ({ $long -gt 5.5 -and $long -lt 6.5 }) { '미터로 해석됨 → Scale Unit=Meter 로 바꾸거나 재익스포트'; break }
        ({ $long -gt 55000 }) { 'x100 이 두 번 먹었다'; break }
        default { "판정 불가 (최장변 $long)" }
    }
    Write-Host "단위: $unit"

    # 축
    $absP = @{ X = [math]::Abs($yb.PX); Y = [math]::Abs($yb.PY); Z = [math]::Abs($yb.PZ) }
    $domY = ($absP.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 1).Key
    Write-Host "Blender +Y(20m 북쪽) 가 간 축: $domY  (값 X=$($yb.PX) Y=$($yb.PY) Z=$($yb.PZ))"

    if ($domY -eq 'Z') {
        if ($yb.PZ -lt 0) {
            Write-Host '=> H1: (x, z, -y). 설계대로 진행.' -ForegroundColor Green
        } elseif ($xb -and $xb.PX -lt 0) {
            Write-Host '=> H2b: 180도 yaw. Orientation.Y 에 180 가산, 기하는 정상.' -ForegroundColor Yellow
        } else {
            Write-Host '=> H2: 미러. 매니페스트 Z 부호 반전 + 면 감김 수정 필요.' -ForegroundColor Red
        }
    } elseif ($domY -eq 'Y') {
        Write-Host '=> H3: UE 식 Z-up. 임포트 다이얼로그의 World Up 을 바꿔 재측정.' -ForegroundColor Red
    } else {
        Write-Host '=> 예상 밖. 위 표로 수동 판정.' -ForegroundColor Red
    }

    if ($zb) { Write-Host "Blender +Z(30m 위) 가 간 축: X=$($zb.PX) Y=$($zb.PY) Z=$($zb.PZ)" }

    # 오프셋 보존
    $spread = ($rows | ForEach-Object { [math]::Abs($_.PX) + [math]::Abs($_.PY) + [math]::Abs($_.PZ) } |
               Measure-Object -Maximum).Maximum
    if ($spread -lt 100) {
        Write-Host '주의: 모든 조각이 원점 근처다 → 임포터가 bbox 로 재중심화했다. cframe_if_recentred 열을 쓸 것.' -ForegroundColor Yellow
    } else {
        Write-Host '오프셋 보존됨 (조각들이 원래 간격을 유지).' -ForegroundColor Green
    }
}
