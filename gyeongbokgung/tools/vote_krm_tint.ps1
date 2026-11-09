# KRM_Palace 의 셸 MeshPart 만 Material / Color 를 바꾼다 (소품은 안 건드린다).
#
# 왜 : 발행된 에셋 썸네일이 거의 순백이다.
#      「렌더는 되는데 하얘서 안 보이는 것」인지 「아예 렌더가 안 되는 것」인지 가른다.
#      빨간 Neon 으로 바꿔서 그래도 안 보이면 렌더 자체가 안 되는 것이다.
#
#   .\vote_krm_tint.ps1 -Apply           # 빨간 Neon 으로
#   .\vote_krm_tint.ps1 -Off -Apply      # Basic / 원래 회색으로 되돌린다
param(
    [string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm",
    [switch] $Off,
    [switch] $Apply
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"
. "$PSScriptRoot\ovdr_script.ps1"

$mat = if ($Off) { 'Basic' } else { 'Neon' }
$col = if ($Off) { @(200, 200, 200) } else { @(255, 40, 40) }

$text = Read-OvdrText -Path $LevelPath
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

# 자식 블록을 훑어 셸만 통째로 새로 만든다 (부분 치환보다 안전하다)
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
                if ($nm.Success -and $nm.Groups[2].Value -notlike 'KRMM_KRM_PROP*') {
                    $new = $ch
                    $new = $new -replace '"Material":\s*"[^"]*"', ('"Material": "' + $mat + '"')
                    $new = $new -replace '"Color":\s*\{\s*"ObjectType":\s*"Color3",\s*"R":\s*\d+,\s*"G":\s*\d+,\s*"B":\s*\d+\s*\}', `
                        ('"Color": { "ObjectType": "Color3", "R": ' + $col[0] + ', "G": ' + $col[1] + ', "B": ' + $col[2] + ' }')
                    if ($new -cne $ch) {
                        $edits += [pscustomobject]@{ Name = $nm.Groups[2].Value; At = $start; Len = ($k - $start + 1); New = $new }
                    }
                }
                $start = -1
            }
        }
        elseif ($c -eq ']' -and $d -eq 0) { break }
    }
    $k++
}

Write-Host ("셸 {0} 개를 Material={1} Color=({2},{3},{4}) 로 바꾼다" -f $edits.Count, $mat, $col[0], $col[1], $col[2]) -ForegroundColor Cyan
if ($edits.Count -eq 0) { Write-Host "바꿀 게 없다." -ForegroundColor Yellow; return }

$newBlk = $blk
foreach ($e in ($edits | Sort-Object At -Descending)) {
    $newBlk = $newBlk.Substring(0, $e.At) + $e.New + $newBlk.Substring($e.At + $e.Len)
}
$new = $text.Substring(0, $blkStart) + $newBlk + $text.Substring($blkEnd + 1)
$null = $new | ConvertFrom-Json

$propNeon = ([regex]::Matches($newBlk, '"Name":\s*"KRMM_KRM_PROP[^"]*"[\s\S]{0,900}?"Material":\s*"Neon"')).Count
Write-Host ("검산 : 소품 중 Neon 이 된 것 {0} 개 (0 이어야 한다)" -f $propNeon) -ForegroundColor $(if ($propNeon) { 'Red' } else { 'Green' })
if ($propNeon) { throw "소품을 건드렸다" }

if (-not $Apply) { Write-Host "미리보기만 했다. 반영하려면 -Apply." -ForegroundColor Yellow; return }
$null = Backup-OvdrLevel -Path $LevelPath -Tag ('krm_tint_' + $mat)
Write-OvdrText -Text $new -Path $LevelPath
$null = Invoke-OvdrRpc -Method 'game.stop' -TimeoutSec 30
Publish-OvdrLevel
