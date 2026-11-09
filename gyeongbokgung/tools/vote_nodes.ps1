# 레벨 안 Script / LocalScript / ModuleScript 노드 이름을 전부 뽑는다.
# (디스크 Lua 파일명과 노드 이름이 다른 경우가 있어서 대조가 필요하다)
param([string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm")
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"

$text = Read-OvdrText -Path $LevelPath

# "InstanceType": "Script" ... 뒤에 오는 "Name": "..." 를 짝지어 읽는다
$pat = '"InstanceType":\s*"(Script|LocalScript|ModuleScript)"[\s\S]{0,400}?"Name":\s*"([^"]+)"'
$rows = @()
foreach ($m in [regex]::Matches($text, $pat)) {
    $rows += [pscustomobject]@{ Kind = $m.Groups[1].Value; Name = $m.Groups[2].Value; At = $m.Index }
}
Write-Host ("script nodes: {0}" -f $rows.Count)
$rows | Sort-Object Kind, Name | ForEach-Object { "  {0,-14} {1}" -f $_.Kind, $_.Name }
