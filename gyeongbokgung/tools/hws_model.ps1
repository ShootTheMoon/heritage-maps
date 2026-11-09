param([string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm")
$ErrorActionPreference='Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"; . "$PSScriptRoot\ovdr_level.ps1"
$text = Read-OvdrText -Path $LevelPath
$m=[regex]::Match($text,'"Name":\s*"Hwaseong Place"'); $i=$m.Index; $d=0
while($i -ge 0){$c=$text[$i]; if($c -eq '}'){$d++} elseif($c -eq '{'){if($d -eq 0){break}; $d--}; $i--}
$j=$i;$d=0;$s=$false
while($j -lt $text.Length){$c=$text[$j]
 if($s){if($c -eq '\'){$j+=2;continue}; if($c -eq '"'){$s=$false}}
 else{if($c -eq '"'){$s=$true}elseif($c -eq '{'){$d++}elseif($c -eq '}'){$d--;if($d -eq 0){break}}}
 $j++}
$blk=$text.Substring($i,$j-$i+1)
# count instance types inside
[regex]::Matches($blk,'"InstanceType":\s*"([^"]+)"') | Group-Object { $_.Groups[1].Value } |
  ForEach-Object { "  {0,-16} {1}" -f $_.Name, $_.Count }
Write-Host "--- first 900 chars of container ---"
$blk.Substring(0,[Math]::Min(900,$blk.Length))
