Set-Location "$HOME\Desktop\blender\gyeongbokgung"; . .\ovdr_rpc.ps1
$g = 'FE12200013CF469187A8571208DE71FF'
try { $r = Invoke-OvdrRpc 'instance.upsert' @{ ActorGuid = $g; Transparency = 1 } -Raw; "upsert: " + $r.Substring(0, [Math]::Min(200, $r.Length)) } catch { "upsert ERR $($_.Exception.Message)" }
$null = Invoke-OvdrRpc 'viewport.camera.set' @{ position = @{ x = -32000; y = 9500; z = -9000 }; lookAt = @{ x = -32000; y = 300; z = 0 } }
$s = Invoke-OvdrRpc 'game.screenshot' @{ includeGui = $false } -TimeoutSec 60; "hidden: " + $s.path
try { $r = Invoke-OvdrRpc 'instance.upsert' @{ ActorGuid = $g; Transparency = 0 } -Raw } catch {}
