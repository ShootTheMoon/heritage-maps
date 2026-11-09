# 3단계 : 경기구역 벽 4장을 맵별 이름으로 바꾸고 맵 컨테이너 안으로 옮긴다.
#
#   Workspace/Arena_Bound_North  ->  Workspace/JSN_Sangok/JSN_Bound_North
#   (South / East / West 도 같다)
#
# 왜 이렇게 하나 :
#   BoundaryServer 와 CaptureServer 가 둘 다 FindFirstChild(name, true) 로 벽을 찾는다.
#   맵이 셋인데 이름이 같으면 어느 맵의 벽이 잡히는지 통제할 수 없다.
#   게다가 BoundaryServer 는 찾은 벽을 ServerStorage 로 옮겨버려서,
#   그 다음 CaptureServer 가 Workspace 를 뒤지면 다른 맵의 벽을 잡는 상태가 실제로 만들어진다.
#   -> 점령지는 맵 B 에 열리고 즉사 판정은 맵 A 기준이 된다.
#
#   이름을 맵별로 나누면 이 일이 물리적으로 불가능해진다. 존재하지 않는 이름은 잡힐 수 없다.
#
# ★ 위치·크기·속성은 한 글자도 안 바꾼다. 이름과 부모만 바꾼다.
# ★ 되돌릴 수 없는 단계다. 실행 전에 전용 백업을 뜬다.
#
#   .\vote_step3.ps1            # 미리보기
#   .\vote_step3.ps1 -Apply
param(
    [string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm",
    [switch] $Apply
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"
. "$PSScriptRoot\ovdr_script.ps1"

$MAP = 'JSN_Sangok'
$pairs = [ordered]@{
    'Arena_Bound_North' = 'JSN_Bound_North'
    'Arena_Bound_South' = 'JSN_Bound_South'
    'Arena_Bound_East'  = 'JSN_Bound_East'
    'Arena_Bound_West'  = 'JSN_Bound_West'
}

$text = Read-OvdrText -Path $LevelPath

# 이름으로 노드 블록의 시작/끝 인덱스를 잡는다 (문자열 안의 중괄호는 건너뛴다)
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

# 1) 벽 4장의 블록을 통째로 떼어 낸다 (뒤에서부터 지워야 인덱스가 안 밀린다)
$blocks = [ordered]@{}
$spans = @()
foreach ($old in $pairs.Keys) {
    $sp = Get-NodeSpan -Text $text -Name $old
    if ($null -eq $sp) { throw "벽을 못 찾았다: $old" }
    $blk = $text.Substring($sp.Start, $sp.End - $sp.Start + 1)
    # 이름만 바꾼다. 다른 속성은 손대지 않는다.
    $blk = $blk -replace ('"Name":\s*"' + [regex]::Escape($old) + '"'), ('"Name": "' + $pairs[$old] + '"')
    $blocks[$old] = $blk
    $spans += [pscustomobject]@{ Name = $old; Start = $sp.Start; End = $sp.End }
    Write-Host ("  {0,-20} -> {1,-18} ({2} chars)" -f $old, $pairs[$old], $blk.Length)
}

# 옮기기 전에 목적지가 있는지 먼저 확인한다. 없으면 아무것도 지우지 않는다.
if ($null -eq (Find-OvdrChildrenInsertPoint -Text $text -InstanceType 'Model' -Name $MAP)) {
    throw "$MAP 의 LuaChildren 을 못 찾았다"
}

# 2) 원래 자리에서 지운다 (뒤에서부터)
$cut = $text
foreach ($sp in ($spans | Sort-Object Start -Descending)) {
    $a = $sp.Start; $b = $sp.End
    # 뒤따르는 쉼표까지 같이 지운다
    $k = $b + 1
    while ($k -lt $cut.Length -and [char]::IsWhiteSpace($cut[$k])) { $k++ }
    if ($k -lt $cut.Length -and $cut[$k] -eq ',') { $b = $k }
    else {
        # 마지막 원소였으면 앞의 쉼표를 지운다
        $k = $a - 1
        while ($k -ge 0 -and [char]::IsWhiteSpace($cut[$k])) { $k-- }
        if ($k -ge 0 -and $cut[$k] -eq ',') { $a = $k }
    }
    $cut = $cut.Substring(0, $a) + $cut.Substring($b + 1)
}

# 3) 맵 안에 넣는다. ObjectKey 는 그대로 쓴다 (같은 파츠를 옮기는 것뿐이다).
$key = Get-OvdrKeyIndex -Text $cut
$new = Add-OvdrInstances -Text $cut -InstanceJson @($blocks.Values) `
        -ParentType 'Model' -ParentName $MAP -NewKeyIndex $key

$null = $new | ConvertFrom-Json

# 4) 검산 : 새 이름 4개가 있고 옛 이름이 하나도 없어야 한다
foreach ($old in $pairs.Keys) {
    $nOld = ([regex]::Matches($new, '"Name":\s*"' + [regex]::Escape($old) + '"')).Count
    $nNew = ([regex]::Matches($new, '"Name":\s*"' + [regex]::Escape($pairs[$old]) + '"')).Count
    if ($nOld -ne 0 -or $nNew -ne 1) { throw ("검산 실패 {0}: 옛이름 {1}개, 새이름 {2}개" -f $old, $nOld, $nNew) }
}
# 새 이름 4개가 전부 JSN_Sangok 블록 안에 있는가
$mapSpan = Get-NodeSpan -Text $new -Name $MAP
if ($null -eq $mapSpan) { throw "$MAP 블록을 못 찾았다" }
$mapBlk = $new.Substring($mapSpan.Start, $mapSpan.End - $mapSpan.Start + 1)
foreach ($nn in $pairs.Values) {
    if (([regex]::Matches($mapBlk, '"Name":\s*"' + $nn + '"')).Count -ne 1) { throw "$nn 이 $MAP 안에 없다" }
}
Write-Host "검산 통과 : 새 이름 4개가 전부 $MAP 안에 있고 옛 이름은 0개" -ForegroundColor Green

if (-not $Apply) { Write-Host "미리보기만 했다. 반영하려면 -Apply." -ForegroundColor Yellow; return }

$null = Backup-OvdrLevel -Path $LevelPath -Tag 'before_bound_rename'
Write-OvdrText -Text $new -Path $LevelPath
$null = Invoke-OvdrRpc -Method 'game.stop' -TimeoutSec 30
Publish-OvdrLevel
