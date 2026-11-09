# KRM_Palace 의 MeshPart 가 가리키는 에셋 id 를 자산표에서 이름으로 되짚는다.
#
# 「셸이 안 보인다」의 후보 원인 :
#   - MeshId 가 셸이 아닌 다른 에셋(소품·모델)을 가리킨다  <- 이전에 TextureId 에서 실제로 났던 사고
#   - 에셋이 비활성(bIsActive=false)이다
#   - 에셋 자체가 자산표에 없다
param(
    [string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm",
    [string] $Proj      = "$env:USERPROFILE\Desktop\onlyoneshot"
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"

$tbl = Get-Content "$Proj\UGCLocalAssetTable.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$byId = @{}
foreach ($p in $tbl.localAssetList.PSObject.Properties) {
    $v = $p.Value
    $byId[[string]$v.contentId] = [pscustomobject]@{
        Name = $v.name; Type = $v.worldAssetType
        Active = $(if ($null -ne $v.bIsActive) { $v.bIsActive } else { $true })
    }
}
Write-Host ("자산표 {0} 개" -f $byId.Count)

$text = Read-OvdrText -Path $LevelPath
$m = [regex]::Match($text, '"Name":\s*"KRM_Palace"')
$i = $m.Index; $d = 0
while ($i -ge 0) { $c = $text[$i]; if ($c -eq '}') { $d++ } elseif ($c -eq '{') { if ($d -eq 0) { break }; $d-- }; $i-- }
$j = $i; $d = 0; $s = $false
while ($j -lt $text.Length) {
    $c = $text[$j]
    if ($s) { if ($c -eq '\') { $j += 2; continue }; if ($c -eq '"') { $s = $false } }
    else { if ($c -eq '"') { $s = $true } elseif ($c -eq '{') { $d++ } elseif ($c -eq '}') { $d--; if ($d -eq 0) { break } } }
    $j++
}
$blk = $text.Substring($i, $j - $i + 1)

# 이름 + MeshId + TextureId 를 한 노드 안에서 짝지어 뽑는다
$pat = '"Name":\s*"(KRMM_[^"]+)"[\s\S]{0,3000}?"MeshId":\s*"ovdrassetid://(\d+)"[\s\S]{0,600}?"TextureId":\s*"ovdrassetid://(\d+)"'
$rows = @()
foreach ($mm in [regex]::Matches($blk, $pat)) {
    $rows += [pscustomobject]@{
        Part = $mm.Groups[1].Value
        MeshId = $mm.Groups[2].Value
        TexId = $mm.Groups[3].Value
    }
}
Write-Host ("짝지은 MeshPart {0} 개`n" -f $rows.Count)

function Show { param($r)
    $mesh = $byId[$r.MeshId]
    $tex  = $byId[$r.TexId]
    $mn = if ($mesh) { "{0} [{1}{2}]" -f $mesh.Name, $mesh.Type, $(if ($mesh.Active) { '' } else { ' /비활성' }) } else { '자산표에 없음' }
    $tn = if ($tex)  { "{0} [{1}{2}]" -f $tex.Name,  $tex.Type,  $(if ($tex.Active)  { '' } else { ' /비활성' }) } else { '자산표에 없음' }
    "  {0,-34} mesh {1,-8} -> {2,-46}  tex {3,-8} -> {4}" -f $r.Part, $r.MeshId, $mn, $r.TexId, $tn
}

Write-Host "== 셸 (KRMM_KRM_SHELL / cor / seni / stub / turret) ==" -ForegroundColor Cyan
$shell = @($rows | Where-Object { $_.Part -notlike 'KRMM_KRM_PROP*' })
$shell | ForEach-Object { Show $_ }

Write-Host "`n== 소품 표본 3개 (비교군 - 이건 화면에 보인다) ==" -ForegroundColor Cyan
@($rows | Where-Object { $_.Part -like 'KRMM_KRM_PROP*' } | Select-Object -First 3) | ForEach-Object { Show $_ }

# 요약
$bad = @($rows | Where-Object {
    $a = $byId[$_.MeshId]
    (-not $a) -or ($a.Type -ne 'STATIC_MESH') -or (-not $a.Active)
})
Write-Host ("`nMeshId 가 수상한 파츠 : {0} / {1}" -f $bad.Count, $rows.Count) -ForegroundColor $(if ($bad.Count) { 'Red' } else { 'Green' })
