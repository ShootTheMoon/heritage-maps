# 경기구역 벽 4장과 스폰의 실좌표를 레벨에서 직접 읽는다.
#
# 계획서에 숫자를 박기 전에 반드시 여기서 확인한다.
# CaptureServer 의 하드코딩 상수(X -73053..-47053)는 "추첨 범위"이지 경기구역이 아니다.
# 실제 경기구역은 Arena_Bound_* 벽 4장의 위치가 정한다 -- 둘은 다른 값이다.
param([string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm")
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"
. "$PSScriptRoot\ovdr_level.ps1"

$text = Read-OvdrText -Path $LevelPath

function Get-NodeBlock {
    <# 이름으로 노드를 찾아 그 노드의 중괄호 블록만 잘라 낸다. #>
    param([string] $Text, [string] $Name)
    $m = [regex]::Match($Text, '"Name":\s*"' + [regex]::Escape($Name) + '"')
    if (-not $m.Success) { return $null }
    # 이 노드의 여는 중괄호까지 거슬러 올라간다
    $i = $m.Index; $depth = 0
    while ($i -ge 0) {
        $c = $Text[$i]
        if ($c -eq '}') { $depth++ }
        elseif ($c -eq '{') { if ($depth -eq 0) { break } ; $depth-- }
        $i--
    }
    if ($i -lt 0) { return $null }
    # 짝이 맞는 닫는 중괄호까지 (문자열 구간은 건너뛴다)
    $j = $i; $d = 0; $inStr = $false
    while ($j -lt $Text.Length) {
        $c = $Text[$j]
        if ($inStr) {
            if ($c -eq '\') { $j += 2; continue }
            if ($c -eq '"') { $inStr = $false }
        } else {
            if ($c -eq '"') { $inStr = $true }
            elseif ($c -eq '{') { $d++ }
            elseif ($c -eq '}') { $d--; if ($d -eq 0) { return $Text.Substring($i, $j - $i + 1) } }
        }
        $j++
    }
    return $null
}

function Get-Vec {
    param([string] $Block, [string] $Key)
    # "Key": { ... "X": n, "Y": n, "Z": n }
    $m = [regex]::Match($Block, '"' + $Key + '":\s*\{[^{}]*?"X":\s*(-?[\d.eE+]+)[^{}]*?"Y":\s*(-?[\d.eE+]+)[^{}]*?"Z":\s*(-?[\d.eE+]+)')
    if (-not $m.Success) { return $null }
    return [pscustomobject]@{ X = [double]$m.Groups[1].Value; Y = [double]$m.Groups[2].Value; Z = [double]$m.Groups[3].Value }
}

function Show-Part {
    param([string] $Name)
    $b = Get-NodeBlock -Text $text -Name $Name
    if (-not $b) { Write-Host ("  {0,-22} NOT FOUND" -f $Name) -ForegroundColor Red; return }
    # CFrame 안의 Position 을 잡는다
    $cf = [regex]::Match($b, '"CFrame":\s*\{[\s\S]{0,400}?"Position":\s*\{[^{}]*?"X":\s*(-?[\d.eE+]+)[^{}]*?"Y":\s*(-?[\d.eE+]+)[^{}]*?"Z":\s*(-?[\d.eE+]+)')
    $sz = Get-Vec -Block $b -Key 'Size'
    $ue = Get-Vec -Block $b -Key 'UnitExtent'
    if ($cf.Success) {
        $p = [pscustomobject]@{ X = [double]$cf.Groups[1].Value; Y = [double]$cf.Groups[2].Value; Z = [double]$cf.Groups[3].Value }
        $szs = if ($sz) { "{0} x {1} x {2}" -f $sz.X, $sz.Y, $sz.Z } else { '-' }
        $ues = if ($ue) { "{0} x {1} x {2}" -f $ue.X, $ue.Y, $ue.Z } else { '-' }
        Write-Host ("  {0,-22} P=({1}, {2}, {3})  Size={4}  UnitExtent={5}" -f $Name, $p.X, $p.Y, $p.Z, $szs, $ues)
    } else {
        Write-Host ("  {0,-22} (CFrame 못 읽음)" -f $Name) -ForegroundColor Yellow
    }
}

Write-Host "`n== Arena_Bound (경기구역 벽) ==" -ForegroundColor Cyan
foreach ($n in 'JSN_Bound_North','JSN_Bound_South','JSN_Bound_East','JSN_Bound_West','KRM_Bound_North','HWS_Bound_North') { Show-Part $n }

Write-Host "`n== SpawnLocation ==" -ForegroundColor Cyan
foreach ($n in 'JSN_Spawn_Red','JSN_Spawn_Blue','KRM_Spawn_Red','KRM_Spawn_Blue') { Show-Part $n }

Write-Host "`n== Model 존재 확인 ==" -ForegroundColor Cyan
foreach ($n in 'JSN_Sangok','KRM_Palace','Hwaseong Place','Hwaseong Collision','Gyeongbokgung Place') {
    $b = Get-NodeBlock -Text $text -Name $n
    Write-Host ("  {0,-22} {1}" -f $n, $(if ($b) { "있음 ({0} chars)" -f $b.Length } else { 'NOT FOUND' }))
}
