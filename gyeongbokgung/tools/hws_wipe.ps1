# 화성 임포트본을 레벨에서 지운다. 살릴 6개는 남긴다.
#
# ★ 2026-08-30. 지면을 OVERDARE 네이티브 Part 로 다시 만들기 위한 선행 작업이다.
#   건물·구조물은 나중에 Blender 에서 다시 임포트한다.
#
# 지우는 것 (전부 화성 전용 접두사임을 실측 확인했다 -- 다른 맵과 충돌 0):
#   Hwaseong Place   : CTB_ 111 · JAM_ 19 · SBK_ 8 · VEG_ 6 · CTP_ 2 · HPR_ 2 · CTR_ 1 · HGD_ 1
#                      = Model 150 + 그 안의 MeshPart 189 = 339 인스턴스
#   Hwaseong Collision : HWS_COL_ 992
#
# 살리는 것 (전부 Hwaseong Place 직속):
#   HWS_Bound_North/South/East/West  -- BoundaryServer 가 경기구역을 여기서 읽는다
#   HWS_Spawn_Red / HWS_Spawn_Blue   -- swapVerified 가 containers[1] 안에서 찾는다
#
# ★ 접두사 HWS_ 를 쓰면 살릴 것까지 지운다. 반드시 HWS_COL_ 로 정확히 짚는다.
#
# ★ 발행된 에셋 150파일은 계정에 그대로 남는다. 발행 취소는 없다.
#   되돌릴 수 있는 것은 인스턴스 삭제뿐이고, 백업이 그 수단이다.
#
#   .\hws_wipe.ps1           # 미리보기 + 살릴 6개 덤프
#   .\hws_wipe.ps1 -Apply
param(
    [string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm",
    [string] $DumpDir   = "$env:USERPROFILE\Desktop\blender\hwaseong_rebuild",
    [switch] $Apply
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"
. "$PSScriptRoot\ovdr_script.ps1"

$KILL = @('CTB_', 'JAM_', 'SBK_', 'VEG_', 'CTP_', 'HPR_', 'CTR_', 'HGD_', 'HWS_COL_')
$KEEP = @('HWS_Bound_North', 'HWS_Bound_South', 'HWS_Bound_East', 'HWS_Bound_West',
          'HWS_Spawn_Red', 'HWS_Spawn_Blue')

$text = Read-OvdrText -Path $LevelPath
$before = $text.Length

# --- 살릴 6개의 블록을 통째로 떠서 남긴다 (복원의 정본) ---
New-Item -ItemType Directory -Force -Path $DumpDir | Out-Null
$dump = @{}
foreach ($n in $KEEP) {
    $m = [regex]::Match($text, '"Name":\s*"' + [regex]::Escape($n) + '"')
    if (-not $m.Success) { throw "살려야 할 것을 못 찾았다: $n" }
    $s = $text.LastIndexOf('{', $m.Index)
    $d = 0; $e = -1
    for ($i = $s; $i -lt $text.Length; $i++) {
        if ($text[$i] -eq '{') { $d++ }
        elseif ($text[$i] -eq '}') { $d--; if ($d -eq 0) { $e = $i; break } }
    }
    if ($e -lt 0) { throw "블록 끝을 못 찾았다: $n" }
    $dump[$n] = $text.Substring($s, $e - $s + 1)
}
$dumpPath = Join-Path $DumpDir 'hws_survivors.json'
($dump.Keys | ForEach-Object { '"' + $_ + '": ' + $dump[$_] }) -join ",`n" |
    ForEach-Object { "{`n$_`n}" } |
    Set-Content -Path $dumpPath -Encoding utf8
Write-Host "살릴 6개 덤프: $dumpPath" -ForegroundColor Green

# --- 지울 것 개수 확인 ---
Write-Host "`n지울 대상:" -ForegroundColor Cyan
$total = 0
foreach ($p in $KILL) {
    $c = ([regex]::Matches($text, '"Name":\s*"' + [regex]::Escape($p) + '[^"]*"')).Count
    $total += $c
    Write-Host ("   {0,-12} {1,5} 매치" -f $p, $c)
}
Write-Host ("   합계 {0} 매치" -f $total)

$new = $text
foreach ($p in $KILL) {
    $new = Remove-OvdrInstancesByName -Text $new -NamePrefix $p
}

# --- 살릴 것이 살아있는지, 다른 맵이 안 다쳤는지 검증 ---
foreach ($n in $KEEP) {
    if ($new -notmatch ('"Name":\s*"' + [regex]::Escape($n) + '"')) { throw "삭제 후 사라졌다: $n" }
}
foreach ($guard in @('JSN_Sangok', 'Changdeokgung Place', 'KRM_Palace', 'Gyeongbokgung Place',
                     'Lobby', 'GND_Base', 'WarCitySpawn', 'Hwaseong Place', 'Hwaseong Collision')) {
    if ($new -notmatch ('"Name":\s*"' + [regex]::Escape($guard) + '"')) { throw "건드리면 안 되는 것이 사라졌다: $guard" }
}
$obj = $new | ConvertFrom-Json     # 구조 검증
Write-Host ("`n텍스트 {0:N0} -> {1:N0} 자  ({2:N0} 자 감소, {3:P1})" -f
    $before, $new.Length, ($before - $new.Length), (1 - $new.Length / $before)) -ForegroundColor Cyan
Write-Host "살릴 6개 전부 생존 확인 · 다른 맵 9개 생존 확인 · JSON 유효" -ForegroundColor Green

if (-not $Apply) { Write-Host "`n미리보기만 했다. 반영하려면 -Apply." -ForegroundColor Yellow; return }
$null = Backup-OvdrLevel -Path $LevelPath -Tag 'hws_wipe_before'
Write-OvdrText -Text $new -Path $LevelPath
$null = Invoke-OvdrRpc -Method 'game.stop' -TimeoutSec 30
Publish-OvdrLevel
