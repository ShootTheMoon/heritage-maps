# 메시와 파츠를 서로 바꿔치기해서 어느 쪽이 문제인지 확정한다.
#
#   A. 보이는 소품 파츠(벤치)에 셸 메시를 물린다
#      -> 나타나면 셸 메시는 멀쩡하다. 안 나타나면 셸 메시가 Studio 에서 못 그려진다.
#
#   B. 안 보이는 셸 파츠(VLA_Room)에 소품 메시를 물리고 크게 키운다
#      -> 나타나면 그 파츠 자리는 멀쩡하다. 안 나타나면 그 파츠 자체가 안 그려진다.
#
# 둘을 같이 보면 「메시 탓」인지 「파츠 탓」인지 한 번에 갈린다.
#
#   .\vote_swapmesh.ps1 -Apply
#   되돌리기 : .\krm_build.ps1 -YawOfs 180 -KeepCenter -RoomsOnly -Apply
param(
    [string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm",
    [string] $Proj      = "$env:USERPROFILE\Desktop\onlyoneshot",
    [switch] $Apply
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"
. "$PSScriptRoot\ovdr_script.ps1"

$tbl = Get-Content "$Proj\UGCLocalAssetTable.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$mesh = @{}
foreach ($p in $tbl.localAssetList.PSObject.Properties) {
    $v = $p.Value
    if ($v.worldAssetType -eq 'STATIC_MESH' -and -not $mesh.ContainsKey($v.name)) { $mesh[$v.name] = $v.contentId }
}
$SHELL = 'ovdrassetid://' + $mesh['KRM_SHELL_VLA_Room_overdare']
$PROP  = 'ovdrassetid://' + $mesh['KRM_PROP_Bench_overdare']
Write-Host ("셸 메시 {0}   소품 메시 {1}" -f $SHELL, $PROP)

# 바꿀 대상 : 파츠 이름 -> (새 MeshId, 새 Size)
$plan = @{
    'KRMM_KRM_PROP_Bench_i'     = @{ Mesh = $SHELL; Size = 100;  Why = 'A : 보이는 소품 파츠에 셸 메시' }
    'KRMM_KRM_SHELL_VLA_Room'   = @{ Mesh = $PROP;  Size = 2000; Why = 'B : 안 보이는 셸 파츠에 소품 메시 20배' }
}

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
$blkStart = $i; $blkEnd = $j
$blk = $text.Substring($blkStart, $blkEnd - $blkStart + 1)

$lc = $blk.IndexOf('"LuaChildren"'); $arr = $blk.IndexOf('[', $lc)
$k = $arr + 1; $d = 0; $s = $false; $start = -1; $edits = @()
while ($k -lt $blk.Length) {
    $c = $blk[$k]
    if ($s) { if ($c -eq '\') { $k += 2; continue }; if ($c -eq '"') { $s = $false } }
    else {
        if ($c -eq '"') { $s = $true }
        elseif ($c -eq '{') { if ($d -eq 0) { $start = $k }; $d++ }
        elseif ($c -eq '}') {
            $d--
            if ($d -eq 0 -and $start -ge 0) {
                $ch = $blk.Substring($start, $k - $start + 1)
                $nm = [regex]::Match($ch, '"InstanceType":\s*"(MeshPart)"[\s\S]{0,400}?"Name":\s*"([^"]+)"')
                if ($nm.Success -and $plan.ContainsKey($nm.Groups[2].Value)) {
                    $spec = $plan[$nm.Groups[2].Value]
                    $new = $ch
                    $new = $new -replace '"MeshId":\s*"[^"]*"', ('"MeshId": "' + $spec.Mesh + '"')
                    # 텍스처는 뗀다. 텍스처가 원인일 가능성을 같이 지운다.
                    $new = $new -replace '"TextureId":\s*"[^"]*"', '"TextureId": ""'
                    $new = $new -replace '"Size":\s*\{[^{}]*\}', `
                        ('"Size": { "ObjectType": "Vector3", "X": ' + $spec.Size + ', "Y": ' + $spec.Size + ', "Z": ' + $spec.Size + ' }')
                    $edits += [pscustomobject]@{ Name = $nm.Groups[2].Value; At = $start; Len = ($k - $start + 1); New = $new; Why = $spec.Why }
                }
                $start = -1
            }
        }
        elseif ($c -eq ']' -and $d -eq 0) { break }
    }
    $k++
}

$edits | ForEach-Object { "  {0,-30} {1}" -f $_.Name, $_.Why }
if ($edits.Count -ne 2) { throw ("대상 2개를 다 못 찾았다 (찾은 것 {0})" -f $edits.Count) }

$newBlk = $blk
foreach ($e in ($edits | Sort-Object At -Descending)) {
    $newBlk = $newBlk.Substring(0, $e.At) + $e.New + $newBlk.Substring($e.At + $e.Len)
}
$new = $text.Substring(0, $blkStart) + $newBlk + $text.Substring($blkEnd + 1)
$null = $new | ConvertFrom-Json

if (-not $Apply) { Write-Host "미리보기만 했다. 반영하려면 -Apply." -ForegroundColor Yellow; return }
$null = Backup-OvdrLevel -Path $LevelPath -Tag 'krm_swapmesh'
Write-OvdrText -Text $new -Path $LevelPath
$null = Invoke-OvdrRpc -Method 'game.stop' -TimeoutSec 30
Publish-OvdrLevel
