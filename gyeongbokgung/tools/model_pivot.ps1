# Model 의 WorldPivot 을 자식 지오메트리 중심으로 맞춘다.
#
# ★ 왜 : Model 을 선택하면 기즈모(이동 화살표)가 자식 위치가 아니라 Model 의
#   WorldPivot 에 뜬다. PrimaryPart 가 None 이면 대체 기준도 없어서 원점 (0,0,0)
#   으로 떨어진다. 그래서 맵은 X=61400 에 있는데 화살표는 저 멀리 원점에 뜬다.
#
# ★ 렌더링·충돌·게임 로직엔 영향이 없다. 자식 Part 가 각자 월드 CFrame 을 들고 있어
#   위치는 그걸로 정해진다. WorldPivot 은 에디터 기즈모와 PivotTo() 의 기준일 뿐이다.
#
# ★ 이 레벨에서는 창덕궁만 맞춰져 있고 산곡·크렘린·화성은 전부 원점이다.
#   작업 대상 밖은 건드리지 않는다는 규칙에 따라 -Name 으로 하나씩만 고친다.
#
#   .\model_pivot.ps1 -Name 'Hwaseong Place'
#   .\model_pivot.ps1 -Name 'Hwaseong Place' -Apply
param(
    [Parameter(Mandatory)][string] $Name,
    [string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm",
    [switch] $Apply
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"
. "$PSScriptRoot\ovdr_script.ps1"

$text = Read-OvdrText -Path $LevelPath

# 노드 범위를 문자열 인식하며 찾는다
$m = [regex]::Match($text, '"Name":\s*"' + [regex]::Escape($Name) + '"')
if (-not $m.Success) { throw "노드를 못 찾았다: $Name" }
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

# 자식 CFrame.Position 들의 중심을 구한다 (PivotOffsetCFrame 은 제외해야 하므로
# "CFrame" 앞의 여는 따옴표까지 포함해 매치한다 -- PivotOffsetCFrame 에는 그게 없다)
$sum = @(0.0, 0.0, 0.0); $n = 0
foreach ($cm in [regex]::Matches($blk, '"CFrame"\s*:\s*\{\s*"ObjectType":\s*"CFrame",\s*"Position":\s*\{[^{}]*?"X":\s*(-?[\d.eE+]+),\s*"Y":\s*(-?[\d.eE+]+),\s*"Z":\s*(-?[\d.eE+]+)')) {
    $sum[0] += [double]$cm.Groups[1].Value
    $sum[1] += [double]$cm.Groups[2].Value
    $sum[2] += [double]$cm.Groups[3].Value
    $n++
}
if ($n -eq 0) { throw "자식 CFrame 을 하나도 못 찾았다" }
$ctr = $sum | ForEach-Object { [Math]::Round($_ / $n, 3) }
Write-Host ("{0} : 자식 {1} 개의 중심 ({2}, {3}, {4})" -f $Name, $n, $ctr[0], $ctr[1], $ctr[2]) -ForegroundColor Cyan

# WorldPivot.Position 을 그 값으로 바꾼다
$wp = [regex]::Match($blk, '"WorldPivot"\s*:\s*\{[\s\S]*?"Position":\s*\{[^{}]*\}')
if (-not $wp.Success) { throw "WorldPivot 을 못 찾았다" }
$old = [regex]::Match($wp.Value, '"X":\s*(-?[\d.eE+]+),\s*"Y":\s*(-?[\d.eE+]+),\s*"Z":\s*(-?[\d.eE+]+)')
Write-Host ("  WorldPivot  ({0}, {1}, {2})  ->  ({3}, {4}, {5})" -f
    $old.Groups[1].Value, $old.Groups[2].Value, $old.Groups[3].Value, $ctr[0], $ctr[1], $ctr[2]) -ForegroundColor Cyan

$inv = [Globalization.CultureInfo]::InvariantCulture
$newWp = $wp.Value
$newWp = [regex]::Replace($newWp, '("X"\s*:\s*)-?[\d.eE+]+', ('${1}' + $ctr[0].ToString($inv)))
$newWp = [regex]::Replace($newWp, '("Y"\s*:\s*)-?[\d.eE+]+', ('${1}' + $ctr[1].ToString($inv)))
$newWp = [regex]::Replace($newWp, '("Z"\s*:\s*)-?[\d.eE+]+', ('${1}' + $ctr[2].ToString($inv)))

$newBlk = $blk.Substring(0, $wp.Index) + $newWp + $blk.Substring($wp.Index + $wp.Length)
$new = $text.Substring(0, $i) + $newBlk + $text.Substring($j + 1)
$null = $new | ConvertFrom-Json

if (-not $Apply) { Write-Host "`n미리보기만 했다. 반영하려면 -Apply." -ForegroundColor Yellow; return }
$null = Backup-OvdrLevel -Path $LevelPath -Tag ('pivot_' + ($Name -replace '\W', '_'))
Write-OvdrText -Text $new -Path $LevelPath
$null = Invoke-OvdrRpc -Method 'game.stop' -TimeoutSec 30
Publish-OvdrLevel
