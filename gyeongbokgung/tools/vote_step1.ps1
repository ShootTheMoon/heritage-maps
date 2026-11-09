# 1단계 : ReplicatedStorage 에 MapService ModuleScript 노드를 만든다.
#
# 이 단계에서 게임 동작은 하나도 안 바뀐다. 아무 스크립트도 아직 require 하지 않는다.
# 노드가 정상적으로 만들어지고 level.apply 가 조용히 통과하는지만 본다.
#
#   .\vote_step1.ps1            # 미리보기 (파일 안 씀)
#   .\vote_step1.ps1 -Apply     # 레벨에 쓰고 발행
#   .\vote_step1.ps1 -Remove -Apply   # 되돌리기
param(
    [string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm",
    [string] $LuaFile   = "$env:USERPROFILE\Desktop\onlyoneshot\Lua\MapService.lua",
    [switch] $Remove,
    [switch] $Apply
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"
. "$PSScriptRoot\ovdr_script.ps1"

$NODE = 'MapService'
$text = Read-OvdrText -Path $LevelPath

if ($Remove) {
    $span = Get-OvdrScriptSourceSpan -Text $text -Name $NODE
    if ($null -eq $span) { Write-Host "$NODE 노드가 없다. 할 일 없음." -ForegroundColor Yellow; return }
    $text = Remove-OvdrNodeByName -Text $text -Name $NODE
    $null = $text | ConvertFrom-Json
    Write-OvdrText -Text $text -Path $LevelPath
    Write-Host "$NODE 노드 제거됨" -ForegroundColor Yellow
    if ($Apply) { Publish-OvdrLevel }
    return
}

if (-not (Test-Path $LuaFile)) { throw "lua 파일이 없다: $LuaFile" }

# 이미 있으면 새로 만들지 않고 Source 만 갈아끼운다 (중복 노드 방지)
$span = Get-OvdrScriptSourceSpan -Text $text -Name $NODE
if ($null -ne $span) {
    Write-Host "$NODE 노드가 이미 있다 -> Source 만 갱신한다" -ForegroundColor Yellow
    if (-not $Apply) { Write-Host "미리보기만. 반영하려면 -Apply" -ForegroundColor Yellow; return }
    $null = Backup-OvdrLevel -Path $LevelPath -Tag 'mapservice_update'
    Set-OvdrScriptSource -Name $NODE -File $LuaFile -Path $LevelPath
    Publish-OvdrLevel
    return
}

$key = Get-OvdrKeyIndex -Text $text
$k = $key + 1

# ★ New-OvdrScriptNodeJson 은 끝에 쉼표를 붙여서 돌려준다.
#   Add-OvdrInstances 도 쉼표를 붙이므로 여기서 떼지 않으면 ",," 가 되어 JSON 이 깨진다.
$nodeJson = New-OvdrScriptNodeJson -Kind 'ModuleScript' -Name $NODE -ObjectKey $k -File $LuaFile
$nodeJson = $nodeJson.TrimEnd() -replace ',$', ''

$lua = [IO.File]::ReadAllText($LuaFile, [Text.UTF8Encoding]::new($false))
Write-Host ("MapService : lua {0} chars -> ObjectKey {1}" -f $lua.Length, $k)

$new = Add-OvdrInstances -Text $text -InstanceJson @($nodeJson) `
        -ParentType 'ReplicatedStorage' -NewKeyIndex $k

# JSON 이 안 깨졌는지 반드시 확인하고 나서 쓴다
$null = $new | ConvertFrom-Json

# 되읽어서 원본 lua 와 같은지 대조한다. 이스케이프가 틀리면 여기서 잡힌다.
$sp2 = Get-OvdrScriptSourceSpan -Text $new -Name $NODE
if ($null -eq $sp2) { throw "삽입 후에도 $NODE 노드를 못 찾는다" }
$back = ('"' + $new.Substring($sp2.Start, $sp2.End - $sp2.Start) + '"' | ConvertFrom-Json)
if (($back -replace "`r`n", "`n") -cne ($lua -replace "`r`n", "`n")) {
    throw "왕복 대조 실패 : 되읽은 소스가 원본과 다르다 ({0} vs {1} chars)" -f $back.Length, $lua.Length
}
Write-Host "왕복 대조 통과" -ForegroundColor Green

if (-not $Apply) {
    Write-Host "미리보기만 했다. 반영하려면 -Apply 를 붙여라." -ForegroundColor Yellow
    return
}

$null = Backup-OvdrLevel -Path $LevelPath -Tag 'mapservice_add'
Write-OvdrText -Text $new -Path $LevelPath
Write-Host "MapService 노드 삽입됨" -ForegroundColor Green
Publish-OvdrLevel
