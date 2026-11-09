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
$NUM='(-?[\d.]+(?:[eE][-+]?\d+)?)'
$sc=[regex]::Matches($blk,'"Scale":\s*\{[^{}]*?"X":\s*'+$NUM)
$sc | Group-Object { $_.Groups[1].Value } | ForEach-Object { "  WorldTransform.Scale.X = {0,-8} x{1}" -f $_.Name, $_.Count }
$one=[regex]::Match($blk,'"Name":\s*"B_CastleWall[^"]*"[\s\S]{0,2500}?"Size":\s*\{[^{}]*?"X":\s*'+$NUM+'[^{}]*?"Y":\s*'+$NUM)
if($one.Success){ "  B_CastleWall Size = ({0}, {1})" -f $one.Groups[1].Value, $one.Groups[2].Value }
