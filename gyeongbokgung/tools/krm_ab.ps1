# 셸이 안 보이는 원인 A/B : 같은 자리·같은 크기의 원시 Part 를 놓아 비교한다.
param([switch] $Remove, [switch] $Apply)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"; . "$PSScriptRoot\ovdr_level.ps1"; . "$PSScriptRoot\ovdr_script.ps1"
$t = Read-OvdrText
$t = Remove-OvdrInstancesByName -Text $t -NamePrefix 'KRMAB_'
$k = Get-OvdrKeyIndex -Text $t
if ($Remove) { $null = $t | ConvertFrom-Json; Write-OvdrText -Text $t; if ($Apply) { Publish-OvdrLevel }; return }
$items = @()
# GRA_Room 자리에 같은 크기 빨간 Part (반투명)
$k++
$items += New-OvdrPartJson -Name 'KRMAB_gra_box' -ObjectKey $k -PX 102972.5 -PY 485 -PZ 0 `
    -SX 2745 -SY 1130 -SZ 2745 -R 255 -G 40 -B 40 -Material 'Neon' -Transparency 0.55 -CanCollide $false
# 대홀 한가운데 작은 밝은 기둥 (위치 확인용)
$k++
$items += New-OvdrPartJson -Name 'KRMAB_marker' -ObjectKey $k -PX 102972.5 -PY 400 -PZ 0 `
    -SX 120 -SY 800 -SZ 120 -R 60 -G 255 -B 90 -Material 'Neon' -CanCollide $false
$t = Add-OvdrInstances -Text $t -InstanceJson $items -ParentType 'Workspace' -NewKeyIndex $k
$null = $t | ConvertFrom-Json
Write-OvdrText -Text $t
Write-Host ("KRMAB_ 삽입 {0}" -f $items.Count) -ForegroundColor Green
if ($Apply) { Publish-OvdrLevel }
