# KRM_Palace 의 셸 MeshPart 만 DoubleSided 를 켠다 (소품은 안 건드린다).
#
# 왜 :
#   셸(벽·바닥·볼트)은 속이 빈 실내 면이라 법선이 안쪽을 본다.
#   DoubleSided=false 면 밖에서 볼 때 뒷면만 보여 통째로 컬링된다.
#   소품은 닫힌 덩어리라 어느 쪽에서 봐도 보인다 -- 「소품만 보인다」와 정확히 맞는다.
#
# 되돌리기 : -Off 를 붙여 다시 끄면 된다. 레벨 데이터만 바뀌고 메시 재발행은 없다.
#
#   .\vote_krm_ds.ps1            # 미리보기
#   .\vote_krm_ds.ps1 -Apply
#   .\vote_krm_ds.ps1 -Off -Apply
param(
    [string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm",
    [switch] $Off,
    [switch] $Apply
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"
. "$PSScriptRoot\ovdr_script.ps1"

$want = if ($Off) { 'false' } else { 'true' }
$text = Read-OvdrText -Path $LevelPath

# KRM_Palace 블록 범위
$m = [regex]::Match($text, '"Name":\s*"KRM_Palace"')
if (-not $m.Success) { throw "KRM_Palace 를 못 찾았다" }
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

# 자식 블록을 훑으며 셸만 고른다. 뒤에서부터 고쳐야 인덱스가 안 밀린다.
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
                if ($nm.Success) {
                    $n = $nm.Groups[2].Value
                    # 셸만. 소품(KRMM_KRM_PROP*)은 닫힌 덩어리라 건드릴 이유가 없다.
                    if ($n -notlike 'KRMM_KRM_PROP*') {
                        $ds = [regex]::Match($ch, '"DoubleSided":\s*(true|false)')
                        if ($ds.Success -and $ds.Groups[1].Value -ne $want) {
                            $edits += [pscustomobject]@{
                                Name = $n
                                At = $start + $ds.Groups[1].Index
                                Len = $ds.Groups[1].Length
                                From = $ds.Groups[1].Value
                            }
                        }
                    }
                }
                $start = -1
            }
        }
        elseif ($c -eq ']' -and $d -eq 0) { break }
    }
    $k++
}

Write-Host ("셸 MeshPart 중 DoubleSided 를 {0} 로 바꿀 것 : {1} 개" -f $want, $edits.Count) -ForegroundColor Cyan
$edits | Sort-Object Name | ForEach-Object { "   {0,-34} {1} -> {2}" -f $_.Name, $_.From, $want }
if ($edits.Count -eq 0) { Write-Host "바꿀 게 없다." -ForegroundColor Yellow; return }

$newBlk = $blk
foreach ($e in ($edits | Sort-Object At -Descending)) {
    $newBlk = $newBlk.Substring(0, $e.At) + $want + $newBlk.Substring($e.At + $e.Len)
}
$new = $text.Substring(0, $blkStart) + $newBlk + $text.Substring($blkEnd + 1)
$null = $new | ConvertFrom-Json

# 검산 : 소품은 하나도 안 바뀌었나
$propTrue = ([regex]::Matches($newBlk, '"Name":\s*"KRMM_KRM_PROP[^"]*"[\s\S]{0,900}?"DoubleSided":\s*true')).Count
Write-Host ("검산 : 소품 중 DoubleSided=true 가 된 것 {0} 개 (0 이어야 한다)" -f $propTrue) -ForegroundColor $(if ($propTrue) { 'Red' } else { 'Green' })
if ($propTrue) { throw "소품을 건드렸다" }

if (-not $Apply) { Write-Host "미리보기만 했다. 반영하려면 -Apply." -ForegroundColor Yellow; return }

$null = Backup-OvdrLevel -Path $LevelPath -Tag ('krm_doublesided_' + $want)
Write-OvdrText -Text $new -Path $LevelPath
$null = Invoke-OvdrRpc -Method 'game.stop' -TimeoutSec 30
Publish-OvdrLevel
