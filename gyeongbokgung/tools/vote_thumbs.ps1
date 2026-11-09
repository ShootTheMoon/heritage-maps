# 발행된 에셋의 썸네일을 받아 온다.
#
# 「메시가 있는데 안 보인다」의 마지막 후보 : 에셋 빌드 자체가 비었을 수 있다.
# 썸네일은 발행 서버가 실제 메시로 구운 그림이라, 비어 있으면 빌드가 실패한 것이다.
param(
    [string] $Proj = "$env:USERPROFILE\Desktop\onlyoneshot",
    [string] $Out  = "$env:USERPROFILE\Desktop\onlyoneshot\Screenshots\Agent\thumbs"
)
$ErrorActionPreference = 'Stop'
$tbl = Get-Content "$Proj\UGCLocalAssetTable.json" -Raw -Encoding UTF8 | ConvertFrom-Json

$want = @(
    'KRM_SHELL_VLA_Room_overdare',
    'KRM_SHELL_GRA_Room_overdare',
    'KRM_SHELL_VLA_FloorPlate_overdare',
    'cor_n_overdare',
    'KRM_PROP_Bench_overdare'
)
New-Item -ItemType Directory -Force -Path $Out | Out-Null

foreach ($p in $tbl.localAssetList.PSObject.Properties) {
    $v = $p.Value
    if (($want -contains $v.name) -and $v.worldAssetType -eq 'STATIC_MESH') {
        $dst = Join-Path $Out ($v.name + '.png')
        try {
            Invoke-WebRequest -Uri $v.thumbnailUrl -OutFile $dst -TimeoutSec 30 -UseBasicParsing
            $len = (Get-Item $dst).Length
            Write-Host ("  {0,-38} {1,8} bytes   {2}" -f $v.name, $len, $dst) -ForegroundColor Green
        } catch {
            Write-Host ("  {0,-38} 받기 실패 : {1}" -f $v.name, $_.Exception.Message) -ForegroundColor Red
        }
    }
}
