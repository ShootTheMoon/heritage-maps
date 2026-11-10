param([double] $S = 100)
Set-Location "$HOME\Desktop\blender\gyeongbokgung"; . .\ovdr_rpc.ps1; . .\ovdr_level.ps1; . .\ovdr_script.ps1
$lv = "$HOME\Desktop\onlyonetap\onlyoneshot.ovdrjm"
$t = Read-OvdrText -Path $lv
$m = [regex]::Match($t, '"Name":\s*"STA_TER_11"[\s\S]{0,4000}?"Size":\s*\{[^}]*\}')
if (-not $m.Success) { throw 'STA_TER_11 Size not found' }
$blk = $m.Value
$new = [regex]::Replace($blk, '"Size":\s*\{[^}]*\}', ('"Size": ' + (New-OvdrVector3 $S $S $S)))
$t2 = $t.Substring(0, $m.Index) + $new + $t.Substring($m.Index + $m.Length)
Write-OvdrText -Text $t2 -Path $lv
$null = Invoke-OvdrRpc 'level.apply' -TimeoutSec 240
$null = Invoke-OvdrRpc 'viewport.camera.set' @{ position = @{ x = -30000; y = 26000; z = -1500 }; lookAt = @{ x = -30000; y = 0; z = 0 } }
$s = Invoke-OvdrRpc 'game.screenshot' @{ includeGui = $false } -TimeoutSec 60; "size=$S shot: " + $s.path
$r = Invoke-OvdrRpc 'instance.read' @{ ActorGuid = 'FE12200013CF469187A8571208DE71FF' }
"readback Size=" + ($r.instance.Size | ConvertTo-Json -Compress) + " UnitExtent=" + ($r.instance.UnitExtent | ConvertTo-Json -Compress)
