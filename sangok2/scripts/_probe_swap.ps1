param([string] $Mesh, [string] $Tex, [string] $Tag)
Set-Location "$HOME\Desktop\blender\gyeongbokgung"; . .\ovdr_rpc.ps1; . .\ovdr_level.ps1; . .\ovdr_script.ps1
$lv = "$HOME\Desktop\onlyonetap\onlyoneshot.ovdrjm"
$t = Read-OvdrText -Path $lv
$m = [regex]::Match($t, '"Name":\s*"SGK_Pine_0001"[\s\S]{0,5000}?"TextureId":\s*"[^"]*"')
if (-not $m.Success) { throw 'probe pine not found' }
$blk = $m.Value
if ($Mesh) { $blk = [regex]::Replace($blk, '"MeshId":\s*"[^"]*"', ('"MeshId": "ovdrassetid://' + $Mesh + '"')) }
if ($Tex)  { $blk = [regex]::Replace($blk, '"TextureId":\s*"[^"]*"', ('"TextureId": "ovdrassetid://' + $Tex + '"')) }
$t2 = $t.Substring(0, $m.Index) + $blk + $t.Substring($m.Index + $m.Length)
Write-OvdrText -Text $t2 -Path $lv
$null = Invoke-OvdrRpc 'level.apply' -TimeoutSec 240
Start-Sleep -Seconds 12
$null = Invoke-OvdrRpc 'viewport.camera.set' @{ position = @{ x = -42462; y = 3200; z = -8400 }; lookAt = @{ x = -42462; y = 2700; z = -10269 } }
$sh = Invoke-OvdrRpc 'game.screenshot' @{ includeGui = $false } -TimeoutSec 60
"$Tag : " + $sh.path
Write-OvdrText -Text $t -Path $lv
$null = Invoke-OvdrRpc 'level.apply' -TimeoutSec 240
