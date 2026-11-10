param([string] $Mat = 'Glass')
Set-Location "$HOME\Desktop\blender\gyeongbokgung"; . .\ovdr_rpc.ps1; . .\ovdr_level.ps1; . .\ovdr_script.ps1
$lv = "$HOME\Desktop\onlyonetap\onlyoneshot.ovdrjm"
$t = Read-OvdrText -Path $lv
$m = [regex]::Match($t, '"Name":\s*"SGK_Pine_0001"[\s\S]{0,6000}?"Material":\s*"[^"]*"')
if (-not $m.Success) { throw 'probe pine not found' }
$blk = [regex]::Replace($m.Value, '"Material":\s*"[^"]*"$', ('"Material": "' + $Mat + '"'))
$t2 = $t.Substring(0, $m.Index) + $blk + $t.Substring($m.Index + $m.Length)
Write-OvdrText -Text $t2 -Path $lv
$null = Invoke-OvdrRpc 'level.apply' -TimeoutSec 240
Start-Sleep -Seconds 5
$null = Invoke-OvdrRpc 'viewport.camera.set' @{ position = @{ x = -42462; y = 3200; z = -8400 }; lookAt = @{ x = -42462; y = 2700; z = -10269 } }
$sh = Invoke-OvdrRpc 'game.screenshot' @{ includeGui = $false } -TimeoutSec 60
"$Mat : " + $sh.path
Write-OvdrText -Text $t -Path $lv
$null = Invoke-OvdrRpc 'level.apply' -TimeoutSec 240
