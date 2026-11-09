param([string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm")
$ErrorActionPreference='Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"; . "$PSScriptRoot\ovdr_level.ps1"
$text = Read-OvdrText -Path $LevelPath
$m=[regex]::Match($text,'"Name":\s*"KRM_Palace"'); $i=$m.Index; $d=0
while($i -ge 0){$c=$text[$i]; if($c -eq '}'){$d++} elseif($c -eq '{'){if($d -eq 0){break}; $d--}; $i--}
$j=$i;$d=0;$s=$false
while($j -lt $text.Length){$c=$text[$j]
 if($s){if($c -eq '\'){$j+=2;continue}; if($c -eq '"'){$s=$false}}
 else{if($c -eq '"'){$s=$true}elseif($c -eq '{'){$d++}elseif($c -eq '}'){$d--;if($d -eq 0){break}}}
 $j++}
$blk=$text.Substring($i,$j-$i+1)
$lc=$blk.IndexOf('"LuaChildren"');$arr=$blk.IndexOf('[',$lc)
$k=$arr+1;$d=0;$s=$false;$start=-1;$rows=@()
while($k -lt $blk.Length){$c=$blk[$k]
 if($s){if($c -eq '\'){$k+=2;continue}; if($c -eq '"'){$s=$false}}
 else{
  if($c -eq '"'){$s=$true}
  elseif($c -eq '{'){if($d -eq 0){$start=$k};$d++}
  elseif($c -eq '}'){$d--
    if($d -eq 0 -and $start -ge 0){
      $ch=$blk.Substring($start,$k-$start+1)
      $nm=[regex]::Match($ch,'"InstanceType":\s*"([^"]+)"[\s\S]{0,400}?"Name":\s*"([^"]+)"')
      if($nm.Success){$rows+=[pscustomobject]@{N=$nm.Groups[2].Value;T=$nm.Groups[1].Value}}
      $start=-1}}
  elseif($c -eq ']' -and $d -eq 0){break}}
 $k++}
Write-Host ("자식 {0}" -f $rows.Count)
$rows | Group-Object { ($_.N -split '_')[0..1] -join '_' } | Sort-Object Count -Descending |
  ForEach-Object { "  {0,-24} {1}" -f $_.Name, $_.Count }
Write-Host "`nKRM_COL 이 아닌 Part:"
$rows | Where-Object { $_.T -eq 'Part' -and $_.N -notlike 'KRM_COL*' } | ForEach-Object { "   " + $_.N }
Write-Host "`n중복 이름:"
$rows | Group-Object N | Where-Object { $_.Count -gt 1 } | ForEach-Object { "   {0} x{1}" -f $_.Name, $_.Count }
