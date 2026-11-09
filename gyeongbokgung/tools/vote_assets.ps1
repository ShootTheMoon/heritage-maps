# 자산표에서 셸·소품 에셋의 원본 항목을 그대로 찍는다.
# 「내가 뭘 비활성화한 거 아니냐」를 확인하려는 것이다.
param([string] $Proj = "$env:USERPROFILE\Desktop\onlyoneshot")
$ErrorActionPreference = 'Stop'

$tbl = Get-Content "$Proj\UGCLocalAssetTable.json" -Raw -Encoding UTF8 | ConvertFrom-Json

$want = @(
    'KRM_SHELL_VLA_Room_overdare',
    'KRM_SHELL_GRA_Room_overdare',
    'cor_n_overdare',
    'KRM_PROP_Bench_overdare'
)
foreach ($p in $tbl.localAssetList.PSObject.Properties) {
    if ($want -contains $p.Value.name) {
        Write-Host ("=== {0} ===" -f $p.Value.name) -ForegroundColor Cyan
        ($p.Value | ConvertTo-Json -Depth 4 -Compress)
    }
}

$off = @()
foreach ($p in $tbl.localAssetList.PSObject.Properties) {
    $v = $p.Value
    if (($v.PSObject.Properties.Name -contains 'bIsActive') -and (-not $v.bIsActive)) {
        $off += ('{0} [{1}]' -f $v.name, $v.worldAssetType)
    }
}
Write-Host ("`nbIsActive = false 인 에셋 {0} 개" -f $off.Count) -ForegroundColor Yellow
$off | Sort-Object | ForEach-Object { '   ' + $_ }
