# 1단계 사전 점검 : 레벨 Source 와 디스크 Lua 가 같은지 대조한다.
#
# 계획서 7절의 경고 — "둘이 갈라진 채로 밀면 남의 수정을 덮어쓴다".
# 여기서 다르다고 나오면 밀기 전에 어느 쪽이 정본인지 먼저 정해야 한다.
param(
    [string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm",
    [string] $LuaDir    = "$env:USERPROFILE\Desktop\onlyoneshot\Lua"
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"
. "$PSScriptRoot\ovdr_script.ps1"

# 이번 작업에서 손대는 스크립트. 레벨 노드 이름 = 디스크 파일 이름(.lua) 이다.
# 레벨 노드 이름 = 키, 디스크 파일 이름 = 값.
# Studio 가 뽑을 때 _1 / _6 접미어를 붙이므로 둘이 다르다. 대조할 땐 짝을 지어야 한다.
$targets = [ordered]@{
    'BoundaryServer'      = 'BoundaryServer_1'
    'CaptureServer'       = 'CaptureServer'
    'TeamServer'          = 'TeamServer'
    'SeamFiller'          = 'SeamFiller'
    'LobbyServer'         = 'LobbyServer'
    'LobbyUI'             = 'LobbyUI'
    'MovementSpeedServer' = 'MovementSpeedServer_6'
    'BoundaryFX'          = 'BoundaryFX_1'
}

$text = Read-OvdrText -Path $LevelPath
Write-Host ("level: {0} chars" -f $text.Length)

$bad = @()
foreach ($n in $targets.Keys) {
    $file = Join-Path $LuaDir ($targets[$n] + '.lua')
    if (-not (Test-Path $file)) { Write-Host ("  {0,-24} FILE MISSING" -f $n) -ForegroundColor Red; $bad += $n; continue }

    $span = Get-OvdrScriptSourceSpan -Text $text -Name $n
    if ($null -eq $span) { Write-Host ("  {0,-24} NODE MISSING" -f $n) -ForegroundColor Red; $bad += $n; continue }

    $raw = $text.Substring($span.Start, $span.End - $span.Start)
    $lvl = ('"' + $raw + '"' | ConvertFrom-Json)
    $dsk = [IO.File]::ReadAllText($file, [Text.UTF8Encoding]::new($false))

    # 줄끝만 다른 건 같은 것으로 본다 (Studio 가 뽑을 때 바꾼다)
    $a = $lvl -replace "`r`n", "`n"
    $b = $dsk -replace "`r`n", "`n"
    if ($a -ceq $b) {
        Write-Host ("  {0,-24} SAME  ({1} chars)" -f $n, $dsk.Length) -ForegroundColor Green
    } else {
        Write-Host ("  {0,-24} DIFF  level={1} disk={2}" -f $n, $a.Length, $b.Length) -ForegroundColor Red
        $bad += $n
    }
}

# MapService 노드가 이미 있는지 (없어야 정상 - 새로 만든다)
$ms = Get-OvdrScriptSourceSpan -Text $text -Name 'MapService'
Write-Host ("  {0,-24} {1}" -f 'MapService', $(if ($ms) { 'ALREADY EXISTS' } else { 'not present (will create)' }))

if ($bad.Count) {
    Write-Host ("`nMISMATCH: {0}" -f ($bad -join ', ')) -ForegroundColor Red
    Write-Host "밀기 전에 어느 쪽이 정본인지 정해라." -ForegroundColor Yellow
} else {
    Write-Host "`nall in sync" -ForegroundColor Green
}
