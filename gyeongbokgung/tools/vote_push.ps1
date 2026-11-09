# 디스크 Lua -> 레벨 스크립트 노드 Source 로 밀고 발행한다.
#
# ★ Studio 가 저장할 때 Lua\*.lua 를 레벨에서 되쓴다.
#   그래서 여러 파일을 고쳤으면 반드시 "전부 밀고 나서 한 번 발행" 해야 한다.
#   일부만 밀고 발행하면 안 민 파일이 옛 내용으로 되돌아간다.
#
#   .\vote_push.ps1 CaptureServer TeamServer SeamFiller
#   .\vote_push.ps1 -NoPublish CaptureServer      # 밀기만 (확인용)
param(
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)][string[]] $Names,
    [Parameter(DontShow)][string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm",
    [Parameter(DontShow)][string] $LuaDir    = "$env:USERPROFILE\Desktop\onlyoneshot\Lua",
    [string] $Tag       = 'vote_push',
    [switch] $NoPublish
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"
. "$PSScriptRoot\ovdr_script.ps1"

if (-not $Names -or $Names.Count -eq 0) { throw "밀 스크립트 이름을 하나 이상 줘라" }

# 레벨 노드 이름 -> 디스크 파일 이름. Studio 가 뽑을 때 _1 / _6 을 붙인 것들.
$fileOf = @{
    'BoundaryServer'      = 'BoundaryServer_1'
    'MovementSpeedServer' = 'MovementSpeedServer_6'
    'BoundaryFX'          = 'BoundaryFX_1'
    'FirstPersonLock'     = 'FirstPersonLock_1'
    'ViewmodelController' = 'ViewmodelController_2'
    'SoundClient'         = 'SoundClient_1'
    'MapService'          = 'MapService_1'
    'SoundServer'         = 'SoundServer_1'
    'SoundDB'             = 'SoundDB_1'
    'ViewmodelConfig'     = 'ViewmodelConfig_6'
    'ViewmodelAnimData'   = 'ViewmodelAnimData_1'
}

# 밀기 전에 전부 존재 확인. 하나라도 없으면 아무것도 안 민다.
$plan = @()
foreach ($n in $Names) {
    # ★ Windows PowerShell 5.1 에는 삼항 연산자가 없다. if/else 로 쓴다.
    $stem = if ($fileOf.ContainsKey($n)) { $fileOf[$n] } else { $n }
    $file = Join-Path $LuaDir ($stem + '.lua')
    if (-not (Test-Path $file)) { throw "lua 파일이 없다: $file" }
    $text = Read-OvdrText -Path $LevelPath
    if ($null -eq (Get-OvdrScriptSourceSpan -Text $text -Name $n)) { throw "레벨에 스크립트 노드가 없다: $n" }
    $plan += [pscustomobject]@{ Name = $n; File = $file }
}

$null = Backup-OvdrLevel -Path $LevelPath -Tag $Tag
foreach ($p in $plan) { Set-OvdrScriptSource -Name $p.Name -File $p.File -Path $LevelPath }

# 민 내용이 실제로 들어갔는지 되읽어 대조한다. 값 대조지만, 여기서는 "밀림 실패" 를 잡는 게 목적이다.
$bad = @()
foreach ($p in $plan) {
    $lvl = (Get-OvdrScriptSource -Name $p.Name -Path $LevelPath) -replace "`r`n", "`n"
    $dsk = ([IO.File]::ReadAllText($p.File, [Text.UTF8Encoding]::new($false))) -replace "`r`n", "`n"
    if ($lvl -ceq $dsk) { Write-Host ("  {0,-22} OK ({1} chars)" -f $p.Name, $dsk.Length) -ForegroundColor Green }
    else { Write-Host ("  {0,-22} MISMATCH level={1} disk={2}" -f $p.Name, $lvl.Length, $dsk.Length) -ForegroundColor Red; $bad += $p.Name }
}
if ($bad.Count) { throw ("밀기 실패: " + ($bad -join ', ')) }

if ($NoPublish) { Write-Host "레벨 파일에만 썼다. 반영하려면 Publish-OvdrLevel." -ForegroundColor Yellow; return }

$null = Invoke-OvdrRpc -Method 'game.stop' -TimeoutSec 30
Publish-OvdrLevel
