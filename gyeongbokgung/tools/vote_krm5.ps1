param([string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm")
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"; . "$PSScriptRoot\ovdr_level.ps1"
$text = Read-OvdrText -Path $LevelPath
$m = [regex]::Match($text, '"Name":\s*"KRM_Palace"')
$i = $m.Index; $d = 0
while ($i -ge 0) { $c=$text[$i]; if ($c -eq '}'){$d++} elseif ($c -eq '{'){ if($d -eq 0){break}; $d-- }; $i-- }
$j=$i; $d=0; $s=$false
while ($j -lt $text.Length) { $c=$text[$j]
  if ($s) { if ($c -eq '\'){$j+=2;continue}; if ($c -eq '"'){$s=$false} }
  else { if ($c -eq '"'){$s=$true} elseif ($c -eq '{'){$d++} elseif ($c -eq '}'){$d--; if($d -eq 0){break}} }
  $j++ }
$blk = $text.Substring($i, $j-$i+1)
$lc=$blk.IndexOf('"LuaChildren"'); $arr=$blk.IndexOf('[',$lc)
$k=$arr+1; $d=0; $s=$false; $start=-1; $rows=@()
while ($k -lt $blk.Length) { $c=$blk[$k]
  if ($s) { if ($c -eq '\'){$k+=2;continue}; if ($c -eq '"'){$s=$false} }
  else {
    if ($c -eq '"'){$s=$true}
    elseif ($c -eq '{'){ if($d -eq 0){$start=$k}; $d++ }
    elseif ($c -eq '}'){ $d--
      if ($d -eq 0 -and $start -ge 0) {
        $ch=$blk.Substring($start,$k-$start+1)
        $nm=[regex]::Match($ch,'"InstanceType":\s*"(MeshPart)"[\s\S]{0,400}?"Name":\s*"([^"]+)"')
        $ue=[regex]::Match($ch,'"UnitExtent":\s*\{[^{}]*?"X":\s*(-?[\d.eE+]+)[^{}]*?"Y":\s*(-?[\d.eE+]+)[^{}]*?"Z":\s*(-?[\d.eE+]+)')
        if ($nm.Success -and $ue.Success) {
          $rows += [pscustomobject]@{ Name=$nm.Groups[2].Value
            UX=[double]$ue.Groups[1].Value; UY=[double]$ue.Groups[2].Value; UZ=[double]$ue.Groups[3].Value }
        }
        $start=-1 } }
    elseif ($c -eq ']' -and $d -eq 0){break} }
  $k++ }
$shell = @($rows | Where-Object { $_.Name -notlike 'KRMM_KRM_PROP*' })
$prop  = @($rows | Where-Object { $_.Name -like 'KRMM_KRM_PROP*' })
$isDefault = { param($r) ($r.UX -eq 50 -and $r.UY -eq 50 -and $r.UZ -eq -50) }
Write-Host ("MeshPart {0} (셸 {1} / 소품 {2})" -f $rows.Count, $shell.Count, $prop.Count) -ForegroundColor Cyan
Write-Host ("  기본값(50,50,-50) 그대로인 것 : 셸 {0}/{1}   소품 {2}/{3}" -f `
  @($shell | Where-Object { &$isDefault $_ }).Count, $shell.Count,
  @($prop  | Where-Object { &$isDefault $_ }).Count, $prop.Count)
Write-Host "`n== 셸 UnitExtent ==" -ForegroundColor Cyan
$shell | Sort-Object Name | ForEach-Object { "  {0,-34} ({1,9:N1}, {2,8:N1}, {3,9:N1})" -f $_.Name,$_.UX,$_.UY,$_.UZ }
Write-Host "`n== 소품 표본 6 ==" -ForegroundColor Cyan
$prop | Select-Object -First 6 | ForEach-Object { "  {0,-34} ({1,9:N1}, {2,8:N1}, {3,9:N1})" -f $_.Name,$_.UX,$_.UY,$_.UZ }
