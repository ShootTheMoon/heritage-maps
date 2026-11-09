param([string] $LevelPath = "$env:USERPROFILE\Desktop\onlyoneshot\onlyoneshot.ovdrjm")
$ErrorActionPreference='Stop'
. "$PSScriptRoot\ovdr_rpc.ps1"; . "$PSScriptRoot\ovdr_level.ps1"
$NUM='(-?[\d.]+(?:[eE][-+]?\d+)?)'
$text = Read-OvdrText -Path $LevelPath
$m=[regex]::Match($text,'"Name":\s*"Hwaseong Place"'); $i=$m.Index; $d=0
while($i -ge 0){$c=$text[$i]; if($c -eq '}'){$d++} elseif($c -eq '{'){if($d -eq 0){break}; $d--}; $i--}
$j=$i;$d=0;$s=$false
while($j -lt $text.Length){$c=$text[$j]
 if($s){if($c -eq '\'){$j+=2;continue}; if($c -eq '"'){$s=$false}}
 else{if($c -eq '"'){$s=$true}elseif($c -eq '{'){$d++}elseif($c -eq '}'){$d--;if($d -eq 0){break}}}
 $j++}
$blk=$text.Substring($i,$j-$i+1)
$pat='"InstanceType":\s*"MeshPart"[\s\S]{0,2500}?"Name":\s*"([^"]+)"[\s\S]{0,2500}?"UnitExtent":\s*\{[^{}]*?"X":\s*'+$NUM+'[^{}]*?"Y":\s*'+$NUM+'[^{}]*?"Z":\s*'+$NUM+'[\s\S]{0,900}?"Size":\s*\{[^{}]*?"X":\s*'+$NUM+'[^{}]*?"Y":\s*'+$NUM+'[^{}]*?"Z":\s*'+$NUM
$n=0
foreach($mm in [regex]::Matches($blk,$pat)){
  $n++
  if($n -le 8){
    "{0,-30} UE=({1,9:N0},{2,8:N0},{3,9:N0})  Size=({4,7:N1},{5,7:N1},{6,7:N1})" -f `
      $mm.Groups[1].Value,[double]$mm.Groups[2].Value,[double]$mm.Groups[3].Value,[double]$mm.Groups[4].Value,
      [double]$mm.Groups[5].Value,[double]$mm.Groups[6].Value,[double]$mm.Groups[7].Value
  }
}
"짝지은 MeshPart : $n"
