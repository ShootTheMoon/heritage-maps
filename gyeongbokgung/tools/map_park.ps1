# 맵 컨테이너를 Workspace <-> ServerStorage 로 통째로 옮긴다.
#
# ★ 왜 : ServerStorage 는 클라이언트로 복제가 안 된다. Workspace 에 있는 것만
#   접속할 때 클라로 내려간다. 세 맵을 다 창고에 넣어두고 투표가 끝난 뒤에
#   당선된 하나만 꺼내면, 접속할 때 받는 양이 3,773 -> 70 인스턴스가 된다.
#
# ★ 되돌리기 : -Restore 로 Workspace 에 다시 넣는다. 백업도 뜬다.
#
# ⚠ 편집기가 텅 빈 월드로 보이게 된다. 맵을 눈으로 고쳐야 하면 -Restore 로
#   꺼냈다가 작업하고 다시 넣어라.
#
#   .\map_park.ps1                    # 미리보기
#   .\map_park.ps1 -Apply
#   .\map_park.ps1 -Restore -Apply
param(
    [string[]] $Maps = @('JSN_Sangok', 'KRM_Palace'),
    [string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm",
    [switch] $Restore,
    [switch] $Apply
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"
. "$PSScriptRoot\ovdr_script.ps1"   # Backup-OvdrLevel / Publish-OvdrLevel

$from = 'Workspace'
$to   = 'ServerStorage'
if ($Restore) { $from = 'ServerStorage'; $to = 'Workspace' }

# 이름으로 최상위 노드 블록의 범위를 찾는다. 문자열 안의 중괄호는 세지 않는다.
function Get-NodeSpan {
    param([string] $Text, [string] $Name)
    $m = [regex]::Match($Text, '"Name":\s*"' + [regex]::Escape($Name) + '"')
    if (-not $m.Success) { return $null }
    $i = $m.Index; $d = 0
    while ($i -ge 0) {
        $c = $Text[$i]
        if ($c -eq '}') { $d++ } elseif ($c -eq '{') { if ($d -eq 0) { break }; $d-- }
        $i--
    }
    if ($i -lt 0) { return $null }
    $j = $i; $d = 0; $s = $false
    while ($j -lt $Text.Length) {
        $c = $Text[$j]
        if ($s) {
            if ($c -eq '\') { $j += 2; continue }
            if ($c -eq '"') { $s = $false }
        } else {
            if ($c -eq '"') { $s = $true }
            elseif ($c -eq '{') { $d++ }
            elseif ($c -eq '}') { $d--; if ($d -eq 0) { return [pscustomobject]@{ Start = $i; End = $j } } }
        }
        $j++
    }
    return $null
}

$text = Read-OvdrText -Path $LevelPath
$origLen = $text.Length

# 옮기기 전에 목적지가 존재하는지부터 본다. 없으면 아무것도 안 건드린다.
if ($null -eq (Find-OvdrChildrenInsertPoint -Text $text -InstanceType $to)) {
    throw "$to 의 LuaChildren 을 못 찾았다"
}

Write-Host ("{0} -> {1}" -f $from, $to) -ForegroundColor Cyan

$blocks = @()
foreach ($name in $Maps) {
    $sp = Get-NodeSpan -Text $text -Name $name
    if ($null -eq $sp) { Write-Host ("  {0,-24} 없다 - 건너뛴다" -f $name) -ForegroundColor Yellow; continue }

    $blk = $text.Substring($sp.Start, $sp.End - $sp.Start + 1)

    # 이미 목적지에 있는지 확인한다. 목적지 블록 안에 이 노드가 들어있으면 할 일이 없다.
    $destSp = Get-NodeSpan -Text $text -Name $to
    $inDest = $false
    if ($null -ne $destSp) { $inDest = ($sp.Start -gt $destSp.Start -and $sp.End -lt $destSp.End) }
    if ($inDest) { Write-Host ("  {0,-24} 이미 {1} 에 있다" -f $name, $to) -ForegroundColor Yellow; continue }

    # 블록과 붙어 있는 쉼표를 같이 뗀다. 앞쪽 쉼표를 우선한다.
    $cutStart = $sp.Start
    $cutEnd   = $sp.End
    $k = $sp.Start - 1
    while ($k -ge 0 -and $text[$k] -match '[\s\r\n]') { $k-- }
    if ($k -ge 0 -and $text[$k] -eq ',') {
        $cutStart = $k
    } else {
        $k = $sp.End + 1
        while ($k -lt $text.Length -and $text[$k] -match '[\s\r\n]') { $k++ }
        if ($k -lt $text.Length -and $text[$k] -eq ',') { $cutEnd = $k }
    }

    $text = $text.Substring(0, $cutStart) + $text.Substring($cutEnd + 1)
    $blocks += $blk
    Write-Host ("  {0,-24} 떼어냄 ({1:N0} 자)" -f $name, $blk.Length) -ForegroundColor Green
}

if ($blocks.Count -eq 0) { Write-Host "옮길 게 없다." -ForegroundColor Yellow; return }

# 목적지 LuaChildren 맨 앞에 붙인다. 삽입점은 블록을 뗀 뒤에 다시 잡아야 한다.
$at = Find-OvdrChildrenInsertPoint -Text $text -InstanceType $to
if ($null -eq $at) { throw "블록을 뗀 뒤 $to 의 LuaChildren 을 못 찾았다" }
$k = $at
while ($k -lt $text.Length -and $text[$k] -match '[\s\r\n]') { $k++ }
$isEmpty = ($k -lt $text.Length -and $text[$k] -eq ']')
$ins = ($blocks -join ',')
if (-not $isEmpty) { $ins = $ins + ',' }
$text = $text.Substring(0, $at) + $ins + $text.Substring($at)

# ★ 값 대조는 검증이 아니지만, JSON 이 깨졌는지는 여기서만 잡을 수 있다.
$null = $text | ConvertFrom-Json
Write-Host ("JSON 파싱 통과. {0:N0} -> {1:N0} 자" -f $origLen, $text.Length) -ForegroundColor Green

if (-not $Apply) { Write-Host "`n미리보기만 했다. 반영하려면 -Apply." -ForegroundColor Yellow; return }

$tag = if ($Restore) { 'map_unpark' } else { 'map_park' }
$null = Backup-OvdrLevel -Path $LevelPath -Tag $tag
Write-OvdrText -Text $text -Path $LevelPath
$null = Invoke-OvdrRpc -Method 'game.stop' -TimeoutSec 30
Publish-OvdrLevel
