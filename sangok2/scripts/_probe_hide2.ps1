Set-Location "$HOME\Desktop\blender\gyeongbokgung"; . .\ovdr_rpc.ps1; . .\ovdr_level.ps1; . .\ovdr_script.ps1
$lv = "$HOME\Desktop\onlyonetap\onlyoneshot.ovdrjm"
$t = Read-OvdrText -Path $lv
$m = [regex]::Match($t, '"Name":\s*"STA_TER_11"[\s\S]{0,3000}?"Transparency":\s*0')
if (-not $m.Success) { throw 'STA_TER_11 block not found' }
$t2 = $t.Substring(0, $m.Index) + $m.Value.Substring(0, $m.Value.Length - 1) + '1' + $t.Substring($m.Index + $m.Length)
Write-OvdrText -Text $t2 -Path $lv
$null = Invoke-OvdrRpc 'level.apply' -TimeoutSec 240
$null = Invoke-OvdrRpc 'viewport.camera.set' @{ position = @{ x = -32000; y = 9500; z = -9000 }; lookAt = @{ x = -32000; y = 300; z = 0 } }
$s = Invoke-OvdrRpc 'game.screenshot' @{ includeGui = $false } -TimeoutSec 60; "hidden: " + $s.path
Write-OvdrText -Text $t -Path $lv
$null = Invoke-OvdrRpc 'level.apply' -TimeoutSec 240
"restored"
